from tkinter import Tk
from tkinter.filedialog import askopenfilename
from typing import Optional

from config import MAIN_CFG
from reader.ichi_reader import IchiReader
from reader.subtitle_reader import AssReader, GenericReader, SubtitleEvent, align, MasterReader
from reader.video_reader import VideoReader
from utils import parse_timestamp
from writer.ankiwriter import AnkiWriter

Tk().withdraw()


def read_timestamp(stamp: str) -> float:
    return parse_timestamp(stamp, "%m:%s.%C")


def sub_chooser(sub_reader: GenericReader, timestamp: float, max_to_print: int = 10,
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

if __name__ == "__main__":
    print("Welcome to cmd miner!")
    print("Please pick a video file ... ")
    vid_file = askopenfilename()
    vid_reader = VideoReader(vid_file)
    print("Please pick an English sub file (only .ass/.srt supported) ... ")
    sub_file = askopenfilename()
    sub_reader_eng = MasterReader(sub_file)
    print("Please pick an Japanese sub file (only .ass/.srt supported) ... ")
    sub_file = askopenfilename()
    sub_reader_jp = MasterReader(sub_file)
    ichi_reader = IchiReader()
    writer = AnkiWriter(MAIN_CFG["collection"],
                        MAIN_CFG["main_deck"])
    print("All ready!")

    mined_this_session = 0

    while True:
        try:
            cmd = input("Enter timestamp (mm:ss.ss) or '[q]uit' >>> ")
            if 'quit'.startswith(cmd.lower()) and len(cmd) != 0:
                print("Thank you for using the cmd miner :)")
                print(f"Mined {mined_this_session} cards this session!")
                vid_reader.clear_everything()
                exit(0)
            timestamp = read_timestamp(cmd)

            jp_sub = sub_chooser(sub_reader_jp, timestamp)
            if jp_sub is None:
                raise RuntimeError("No japanese sub chosen")

            eng_sub = sub_chooser(sub_reader_eng, timestamp, auto_choice=False)
            if eng_sub is None:
                print("No english sub chosen. Enter manually")
                eng_sub = input(" >>> ")
            else:
                eng_sub = eng_sub.text
            if len(eng_sub) == 0:
                raise RuntimeError("No translation chosen")

            jp_word = input("Choose target word >>> ")
            if len(jp_word) == 0:
                raise RuntimeError("No word chosen")

            jp_spelling = input("Enter target word spelling >>> ")
            if len(jp_spelling) == 0:
                raise RuntimeError("No spelling provided")

            eng_translation = input("Enter translation of target >>> ")
            if len(eng_translation) == 0:
                raise RuntimeError("No translation given")

            furigana = ichi_reader.to_furigana(jp_sub.text)
            image = vid_reader.extract_image(timestamp)
            audio = vid_reader.extract_audio(jp_sub.t0, jp_sub.t1)

            print("Ready to create card!")
            print(f"target - {jp_word}")
            print(f"pronunciation - {jp_spelling}")
            print(f"target English - {eng_translation}")
            print(f"furigana - {furigana}")
            print(f"english sentence - {eng_sub}")

            confirmation = input("[c]onfirm? >>> ")

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
                        "Line-Furigana": furigana
                    }, marked_as_file=["Audio", "Screenshot"])
                print("note written!")
                mined_this_session += 1
            else:
                print("operation cancelled")

            vid_reader.clear_everything()

        except Exception as e:
            print("ERROR:", e)
