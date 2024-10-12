import json
import os
from tkinter.filedialog import askopenfilename
from typing import Optional

from flask import Flask, render_template, request, jsonify, redirect

import config
from miners.cmd_miner import load_memory, dump_mem, read_timestamp
from reader.KanjiInfoReader import KanjiReader
from reader.ichiran_reader import IchiranReader
from reader.subtitle_reader import MasterReader
from reader.video_reader import VideoReader
from writer.ankiwriter import AnkiWriter

app = Flask(__name__)

# Variables to store file paths and readers
vid_reader: Optional[VideoReader] = None
sub_reader_jp: Optional[MasterReader] = None
sub_reader_eng: Optional[MasterReader] = None
ichi_reader: Optional[IchiranReader] = None
kanji_reader: Optional[KanjiReader] = None
anki_writer: Optional[AnkiWriter] = None


# Initialize the necessary objects using the selected files
def initialize(video_file, jp_sub_file, eng_sub_file):
    global vid_reader, sub_reader_jp, sub_reader_eng, ichi_reader, kanji_reader, anki_writer
    vid_reader = VideoReader(video_file, save_loc=os.path.join(os.path.dirname(__file__), 'static', 'mined'))
    sub_reader_jp = MasterReader(jp_sub_file)
    sub_reader_eng = MasterReader(eng_sub_file)
    ichi_reader = IchiranReader()
    kanji_reader = KanjiReader()
    anki_writer = AnkiWriter(config.MAIN_CFG["collection"], config.MAIN_CFG["main_deck"])


@app.route('/')
def index():
    vid_reader.clear_everything()
    return render_template('index.html')


@app.errorhandler(405)
def method_not_allowed(e):
    return redirect('/')


@app.route('/select', methods=['POST'])
def select_timestamp():
    timestamp = request.form.get('timestamp')

    jp_sub = sub_reader_jp.get_all_lines_and_time_ranges(read_timestamp(timestamp))
    eng_sub = []
    added_eng_text = []
    for sub in jp_sub:
        new_subs = sub_reader_eng.get_all_lines_and_time_ranges(sub)
        for new_sub in new_subs:
            if new_sub.text not in added_eng_text:
                eng_sub.append(new_sub)
                added_eng_text.append(new_sub.text)

    return render_template('select_subs.html', jp_subs=jp_sub, eng_subs=eng_sub,
                           timestamp=timestamp)


@app.route('/get_decomposition', methods=['GET'])
def get_decomposition():
    jp_sub = request.args.get('jp_sub', '')
    try:
        return jsonify(decomposition=ichi_reader.to_deconstruction(jp_sub))
    except RuntimeError as e:
        return jsonify(decomposition=f'got error {e} while getting decomposition for {jp_sub}!')


def deconstruction_json_to_wordlist(decon):
    if isinstance(decon, list):
        rt = []
        for elem in decon:
            rt += deconstruction_json_to_wordlist(elem)
        return rt
    if isinstance(decon, str):
        return []
    if isinstance(decon, int):
        return []
    if 'components' in decon:
        return deconstruction_json_to_wordlist(decon['components'])
    if 'alternative' in decon:
        return deconstruction_json_to_wordlist(decon['alternative'])
    rt = []
    if 'conj' in decon and len(decon['conj']) != 0:
        rt += deconstruction_json_to_wordlist(decon['conj'])
    if 'via' in decon:
        rt += deconstruction_json_to_wordlist(decon['via'])
    if 'reading' in decon and 'gloss' in decon:
        reading = decon['reading']
        if '【' in reading:
            text = reading[:reading.index('【')].strip()
            kana = reading[reading.index('【') + 1:reading.index('】')].strip()
        else:
            text = reading
            kana = text
        rt += [{'reading': reading, 'text': text, 'gloss': decon['gloss'], 'kana': kana}]
    return rt


@app.route('/get_wordlist', methods=['GET'])
def get_wordlist():
    jp_sub = request.args.get('jp_sub', '')
    try:
        js_deconstruction = json.loads(ichi_reader.run_ichiran_cmd(flags='-f', text=jp_sub))
        # print(json.dumps(js_deconstruction, indent=1))
        return jsonify(deconstruction_json_to_wordlist(js_deconstruction))
    except RuntimeError as e:
        return jsonify([])


@app.route('/mine', methods=['POST'])
def mine_card():
    jp_sub = json.loads(request.form.get('jp_sub'))
    eng_sub = request.form.get('eng_sub_custom')
    if len(eng_sub) == 0:
        eng_sub = request.form.get('eng_sub')
    word = json.loads(request.form.get('jp_word'))
    definition = request.form.get('definition')
    timestamp = read_timestamp(request.form.get('timestamp'))

    image = vid_reader.extract_image(timestamp)
    audio = vid_reader.extract_audio(jp_sub['t0'], jp_sub['t1'])
    furigana = ichi_reader.to_furigana(jp_sub['text'])

    kanji_pairs = kanji_reader.extract_kanji_meaning_pairs(word['text'])
    if len(kanji_pairs) < 4:
        for i in range(4 - len(kanji_pairs)):
            kanji_pairs.append(("", ""))

    kanji_kwargs = dict()
    for i in range(min(4, len(kanji_pairs))):
        kanji_kwargs[f'Kanji{i + 1}'] = kanji_pairs[i][0]
        kanji_kwargs[f'Kanji{i + 1}_meaning'] = kanji_pairs[i][1]

    card_as_js = {
        "model": config.MAIN_CFG["main_model"],
        "Target": word['text'],
        "Screenshot": str(image),
        "Target-Eng": definition,
        "Line-English": eng_sub,
        "Target-Spelling": word['kana'],
        "Audio": str(audio),
        "Line-Furigana": furigana,
        "Kanji1": kanji_pairs[0][0],
        "Kanji1-meaning": kanji_pairs[0][1],
        "Kanji2": kanji_pairs[1][0],
        "Kanji2-meaning": kanji_pairs[1][1],
        "Kanji3": kanji_pairs[2][0],
        "Kanji3-meaning": kanji_pairs[2][1],
        "Kanji4": kanji_pairs[3][0],
        "Kanji4-meaning": kanji_pairs[3][1],
    }

    return render_template('card_preview.html',
                           target=word['text'],
                           screenshot=os.path.relpath(image),
                           furigana=furigana,
                           english=eng_sub,
                           translation=definition,
                           spelling=word['kana'],
                           audio=os.path.relpath(audio),
                           card_as_js=json.dumps(card_as_js),
                           **kanji_kwargs)


@app.route('/finalize_mine', methods=['POST'])
def finalize_mine():
    card_js = json.loads(request.form.get('card_as_js'))
    anki_writer.json_to_note(card_js, marked_as_file=["Audio", "Screenshot"])
    return redirect('/', code=302)


def get_files():
    memory = load_memory()

    print("Welcome to flask miner!")
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

    return vid_file, sub_file_jp, sub_file_eng


if __name__ == "__main__":
    video_file, jp_sub_file, eng_sub_file = get_files()
    initialize(video_file, jp_sub_file, eng_sub_file)
    app.run(debug=False)
