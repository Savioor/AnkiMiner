import json
import os
import traceback
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from typing import Optional, Union

import config
from config import MAIN_CFG
from reader.KanjiInfoReader import KanjiReader
from reader.ichi_reader import IchiReader
from reader.ichiran_reader import IchiranReader
from reader.subtitle_reader import GenericReader, SubtitleEvent, align, MasterReader
from reader.video_reader import VideoReader
from utils import parse_timestamp
from writer.ankiwriter import AnkiWriter

Tk().withdraw()


def read_timestamp(stamp: str) -> float:
    return parse_timestamp(stamp, "%m:%s.%C")


def sub_chooser(sub_reader: GenericReader, timestamp: Union[SubtitleEvent, float], max_to_print: int = 10,
                auto_choice: bool = True) -> Optional[SubtitleEvent]:
    all_events = sub_reader.get_all_lines_and_time_ranges(timestamp)

    if len(all_events) == 1 and auto_choice:
        print("Only one event at timestamp, choosing it:")
        print(str(all_events[0]))
        return all_events[0]
    if len(all_events) == 0:
        print("No subtitles found")
        return None

    start_ind = 0
    while start_ind < len(all_events):
        for i in range(max_to_print):
            if i + start_ind >= len(all_events):
                break
            curr_e = all_events[start_ind + i]
            print(align(f"{start_ind + i})", 4) + str(curr_e))

        decision = input("\nPick a subtitle from above or type [n]ext/[q]uit >>> ")
        if "next".startswith(decision.lower()) and len(decision) != 0:
            start_ind = start_ind + max_to_print
            continue
        if "quit".startswith(decision.lower()) and len(decision) != 0:
            start_ind = len(all_events)
            continue
        if not decision.isnumeric():
            print("got non numeric value")
            continue
        decision = int(decision)
        if decision >= (start_ind + max_to_print) or decision < start_ind:
            print("decision not within shown values")
            continue
        return all_events[decision]

    print("Invalid choice!")
    return None


"""
IDEA OF UI DESIGN:
base on a web client (e.g. flask)
Somewhat like this:
_____________________________________________
|  timestamp: [ mm:ss.ss ]                   |
|--------------------------------------------|
| Japanese subs:    |  Word: [ jp word ]     | 
|   * example sub   |  is_common             |
|  [*] chosen sub   |       * example trans  |
|   * example sub   |      [*] chosen trans  |
|-------------------|------------------------|
| English subs:     |      CARD PREVIEW      |
|   * example sub   |    (editable fields)   |
|   * example sub   |       __________       |
|___________________|______/[-create-]\______|

MAYBE:
First jisho result in a panel (yoink the html - edit for choosing)
"""


def verify_exists(path):
    def verify_exists_dec(func):
        def wrapper(*args, **kwargs):
            if not os.path.isdir(path):
                if os.path.exists(path):
                    raise RuntimeError("data path wasn't a directory but exists!")
                os.makedirs(path)
            return func(*args, **kwargs)

        return wrapper

    return verify_exists_dec


@verify_exists(config.MAIN_CFG.data_path)
def load_memory():
    cmd_miner_mem = os.path.join(config.MAIN_CFG.data_path, "cmd_miner.json")
    if not os.path.exists(cmd_miner_mem):
        return dict()
    with open(cmd_miner_mem, "r") as f:
        return json.load(f)


@verify_exists(config.MAIN_CFG.data_path)
def dump_mem(js):
    with open(os.path.join(config.MAIN_CFG.data_path, "cmd_miner.json"), "w") as f:
        json.dump(js, f)


if __name__ == "__main__":
    memory = load_memory()

    print("Welcome to cmd miner!")
    print("Please pick a video file ... ")
    vid_file = askopenfilename()
    sub_file_jp = None
    sub_file_eng = None
    if vid_file in memory:
        print("load existing subtitles? (y/n) ")
        while True:
            cmd = input(" >>> ").strip().lower()
            if len(cmd) == 0:
                continue
            if "yes".startswith(cmd):
                sub_file_eng = memory[vid_file]["eng"]
                sub_file_jp = memory[vid_file]["jp"]
                break
            if "no".startswith(cmd):
                break

    if sub_file_jp is None or sub_file_eng is None:
        print("Please pick an English sub file (only .ass/.srt supported) ... ")
        sub_file_eng = askopenfilename()
        print("Please pick an Japanese sub file (only .ass/.srt supported) ... ")
        sub_file_jp = askopenfilename()

    memory[vid_file] = {"eng": sub_file_eng, "jp": sub_file_jp}
    print("Updated memory for chose video file!")
    dump_mem(memory)

    vid_reader = VideoReader(vid_file)
    sub_reader_eng = MasterReader(sub_file_eng)
    sub_reader_jp = MasterReader(sub_file_jp)
    ichi_reader = IchiranReader()
    kanji_reader = KanjiReader()
    writer = AnkiWriter(MAIN_CFG["collection"],
                        MAIN_CFG["main_deck"])
    print("All ready!")

    mined_this_session = 0

    while True:
        try:
            cmd = input("Enter timestamp (mm:ss.ss) or any command >>> ")
            if len(cmd) == 0:
                continue
            if 'quit'.startswith(cmd.lower()):
                confirmation = input("To confirm exiting type '[e]xit >>> ")
                if 'exit'.startswith(confirmation.lower()) and len(confirmation) != 0:
                    print("Thank you for using the cmd miner :)")
                    print(f"Mined {mined_this_session} cards this session!")
                    vid_reader.clear_everything()
                    exit(0)
                else:
                    continue
            elif 'help'.startswith(cmd.lower()):
                print("[q]uit - exit the program")
                print("[h]elp - show this text")
                continue
            timestamp = read_timestamp(cmd)

            jp_sub = sub_chooser(sub_reader_jp, timestamp, auto_choice=True)
            if jp_sub is None:
                raise RuntimeError("No japanese sub chosen")

            print(ichi_reader.to_deconstruction(jp_sub.text))

            eng_sub = sub_chooser(sub_reader_eng, jp_sub, auto_choice=False)
            if eng_sub is None:
                print("No english sub chosen. Enter manually")
                eng_sub = input(" >>> ")
            else:
                eng_sub = eng_sub.text
            if len(eng_sub) == 0:
                raise RuntimeError("No translation chosen")

            jp_word = input("Choose target word or [s]entence to mine a sentence >>> ")
            if len(jp_word) == 0:
                raise RuntimeError("No word chosen")

            image = vid_reader.extract_image(timestamp)
            audio = vid_reader.extract_audio(jp_sub.t0, jp_sub.t1)
            furigana = ichi_reader.to_furigana(jp_sub.text)

            if 'sentence'.startswith(jp_word.lower()):

                print("Ready to create card!")
                print(f"furigana - {furigana}")
                print(f"english sentence - {eng_sub}")

                confirmation = input("[c]onfirm? >>> ")

                if "confirm".startswith(confirmation.lower()) and len(confirmation) != 0:
                    writer.json_to_note(
                        {
                            "model": MAIN_CFG["sentence_model"],
                            "Line": jp_sub.text,
                            "Screenshot": str(image),
                            "Line-English": eng_sub,
                            "Audio": str(audio),
                            "Line-Furigana": furigana
                        }, marked_as_file=["Audio", "Screenshot"])
                    print("note written!")
                    mined_this_session += 1
                else:
                    print("operation cancelled")

            else:
                try:
                    jp_spelling = ichi_reader.to_spelling(jp_word)
                except (RuntimeError, KeyboardInterrupt) as e:
                    jp_spelling = input("auto spelling failed! input manually >>> ")
                if len(jp_spelling) == 0:
                    raise RuntimeError("No spelling provided")

                try:
                    eng_translation = ichi_reader.interactive_translation_picker(jp_word)
                except (RuntimeError, KeyboardInterrupt) as e:
                    eng_translation = input("Enter translation manually >>> ")
                if len(eng_translation) == 0:
                    raise RuntimeError("No translation given")

                print("Ready to create card!")
                print(f"target - {jp_word}")
                print(f"pronunciation - {jp_spelling}")
                print(f"target English - {eng_translation}")
                print(f"furigana - {furigana}")
                print(f"english sentence - {eng_sub}")

                kanjis = kanji_reader.extract_kanji_meaning_pairs(jp_word)
                print(f"Kanji pairs - {kanjis}")

                confirmation = input("[c]onfirm? >>> ")

                if len(kanjis) < 4:
                    for i in range(4 - len(kanjis)):
                        kanjis.append(("", ""))

                if "confirm".startswith(confirmation.lower()) and len(confirmation) != 0:
                    writer.json_to_note(
                        {
                            "model": MAIN_CFG["main_model"],
                            "Target": jp_word,
                            "Screenshot": str(image),
                            "Target-Eng": eng_translation,
                            "Line-English": eng_sub,
                            "Target-Spelling": jp_spelling,
                            "Audio": str(audio),
                            "Line-Furigana": furigana,
                            "Kanji1": kanjis[0][0],
                            "Kanji1-meaning": kanjis[0][1],
                            "Kanji2": kanjis[1][0],
                            "Kanji2-meaning": kanjis[1][1],
                            "Kanji3": kanjis[2][0],
                            "Kanji3-meaning": kanjis[2][1],
                            "Kanji4": kanjis[3][0],
                            "Kanji4-meaning": kanjis[3][1],
                        }, marked_as_file=["Audio", "Screenshot"])
                    print("note written!")
                    mined_this_session += 1
                else:
                    print("operation cancelled")

            vid_reader.clear_everything()

        except Exception as e:
            print("ERROR:", e)
            traceback.format_exc()
