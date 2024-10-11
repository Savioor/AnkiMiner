import re

from config import MAIN_CFG
from writer.ankiwriter import AnkiWriter


class KanjiReader:

    def __init__(self):
        self.info_source = AnkiWriter(MAIN_CFG.collection,
                                      r"Maintain::Kanji and Radicals Sorted")  # TODO add to config

    def get_meaning_of_kanji(self, kanji: str):
        kanji_card = self.info_source.get_notes_by_value("Kanji", kanji)
        if len(kanji_card) != 1:
            return None
        return kanji_card[0]['Kanji_Meaning']

    def extract_kanjis(self, word: str):
        rt = []
        for c in word:
            if re.match('[\u3400-\u4DB5\u4E00-\u9FCB\uF900-\uFA6A]$', c):
                rt.append(c)
        return rt

    def extract_kanji_meaning_pairs(self, word: str):
        kanjis = self.extract_kanjis(word)
        rt = []
        for kanji in kanjis:
            meaning = self.get_meaning_of_kanji(kanji)
            if meaning is not None:
                rt.append((kanji, meaning))
        return rt
