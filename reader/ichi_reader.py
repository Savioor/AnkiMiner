import re
from time import sleep, time

import requests


class IchiReader:
    ICHI_BASE = "https://ichi.moe/cl/qr/?q=+{}"
    JP_TEXT_RE = re.compile(  # "<div class=\"jspContainer\" style=\"[^<>]*?\">\s*"
        # "<div class=\"jspPane\" style=\"[^<>]*?\">\s*"
        r"<dl class=\"alternatives\">\s*"
        r"<dt>\s*([^【】\s<>\\\/]+?)\s*(【(.+?)】)?\s*<\/dt>")

    def __init__(self, network_wait: float = 5.0):
        self.last_network_call = 0
        self.network_wait = network_wait

    def to_furigana(self, text: str):
        t_passed = time() - self.last_network_call
        if t_passed < self.network_wait:
            sleep(self.network_wait - t_passed)
        answer = requests.get(self.ICHI_BASE.format(text))
        self.last_network_call = time()
        results = self.JP_TEXT_RE.findall(answer.text)
        # index 0 = matched word
        # index 1 = furigana (with brackets)
        # index 2 = furigana (no brackets)

        rt = ""
        curr_ind = 0
        len_increase = 0
        for result in results:
            curr = result[0]

            chars_moved = 0
            matches = 0
            for i in range(curr_ind, len(text)):
                if matches == len(curr):
                    break
                if text[i] != curr[matches]:
                    for j in range(i - matches, i + 1):
                        rt += text[j]
                    matches = 0
                else:
                    matches += 1
                chars_moved += 1
            if matches != len(curr):
                raise RuntimeError(f"Can't find {curr} in {text}")
            curr_ind += chars_moved

            if len(result[1]) == 0:
                rt += curr
            else:
                rt += f" {curr}[{result[2]}]"
                len_increase += 3 + len(result[2])

        rt += text[curr_ind:]

        if len(rt) != len(text) + len_increase:
            raise RuntimeError(f"Length of output {rt} doesn't match input {text}")

        return rt


if __name__ == "__main__":
    reader = IchiReader()
    print(reader.to_furigana("なんで起こしてくれないんですか、常勤パンダさん、え！"))
