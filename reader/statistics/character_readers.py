import re
from typing import Dict, Any

from reader.statistics.generic_statistic_reader import StatsReader


class KanjiStatsReader(StatsReader):

    def __init__(self):
        super().__init__(10000, 200)

    def process_file(self, file_data: str) -> Dict[Any, int]:
        rt = {}
        for c in file_data:
            if re.match('[\u3400-\u4DB5\u4E00-\u9FCB\uF900-\uFA6A]$', c):
                if c not in rt:
                    rt[c] = 0
                rt[c] += 1
        return rt
