import json
import subprocess
from typing import Tuple, List, Dict

import config


class IchiranReader:

    def __init__(self):
        self.cli_tool = config.MAIN_CFG["ichiran_cli"]

    def modify_for_cli(self, text: str) -> str:
        # to_escape = '"\\'
        # rt = ""
        # for t in text:
        #     if t in to_escape:
        #         rt += '\\'
        #     rt += t
        return " ".join(text.splitlines())

    def run_ichiran_cmd(self, flags: str, text: str) -> str:
        if not all([(len(flg) == 2 and flg[0] == '-') or len(flg) == 1 for flg in flags.split()]):
            raise RuntimeError(f"flags: \"{flags}\" not legal format (-a -b -c ...)")
        result = subprocess.Popen([self.cli_tool, flags, f"{self.modify_for_cli(text)}"],
                                  shell=True, stdout=subprocess.PIPE)
        return result.stdout.read().decode('utf-8')

    def to_furigana(self, text: str) -> str:
        result = json.loads(self.run_ichiran_cmd(flags='-f', text=text))
        # output is list of sentence sections, each a str or a set of fragmentations
        # each fragmentation is a list of fragments, and the score
        # each fragment is a list, of the romanization, the details dict and some unknown third list
        # the details dict has the following intresting fields:
        #   * text -> jp origina text
        #   * kana -> jp kana of original text
        #   * IF ONE COMPONENT: gloss -> a list of meanings
        #   (each meaning has a position at 'pos' and meaning at 'gloss')
        #   * IF MANY COMPONENTS: 'components' -> list of components (same structure as the details dict)
        #   * IF CONJUGATED: 'conj' -> details about the conjugation with definition at 'gloss'
        res = ""
        for section in result:
            if isinstance(section, str):
                res += section
            else:
                fragments = section[0][0]  # get first (only) fragmentation, from it the fragments (not score)
                for romanization, details, _ in fragments:
                    orig = details['text']
                    kana = details['kana']
                    if orig == kana:
                        res += orig
                    else:
                        res += f' {orig}[{kana}]'
        return res

    def to_deconstruction(self, text: str) -> str:
        return self.run_ichiran_cmd(flags='-i', text=text)

    def to_definitions(self, text: str) -> List[Dict[str, str]]:
        result = json.loads(self.run_ichiran_cmd(flags='-f', text=text))
        if len(result) != 1:
            raise RuntimeError(f"got more than one section! {result}")
        frags = result[0][0][0]
        if len(frags) != 1:
            raise RuntimeError(f"got more than one fragment in section! {frags}")
        details = frags[0][1]
        if 'components' in details:
            raise RuntimeError(f"got result with components! {details}")
        if 'conj' in details and len(details['conj']) > 0 and 'gloss' in details['conj'][0]:
            details = details['conj'][0]
        if 'gloss' not in details:
            raise RuntimeError(f"definition not found! {details}")
        return details['gloss']


if __name__ == "__main__":
    reader = IchiranReader()
    print(reader.to_furigana("ユーカリ？　かわいく 食べてますけど　もう　あれ 限界です"))
    print(reader.to_definitions("限界"))
