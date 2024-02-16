import abc
import functools
import glob
import os
import time
from typing import Dict, Any, List

from tqdm import tqdm


class StatsReader(abc.ABC):

    def __init__(self, minimum_viable_instances: int = 0,
                 minimum_viable_unique_instances: int = 0):
        self.minimum_viable_instances = minimum_viable_instances
        self.minimum_viable_unique_instances = minimum_viable_unique_instances

    @staticmethod
    def count_to_total(stats: Dict[Any, int]) -> int:
        total = 0
        for value in stats.values():
            total += value
        return total

    def count_to_percent(self, stats: Dict[Any, int]) -> Dict[Any, float]:
        if len(stats) < self.minimum_viable_unique_instances:
            raise RuntimeError("Didn't have enough viable unique instances to create stats")
        total = self.count_to_total(stats)
        if total < self.minimum_viable_instances:
            raise RuntimeError("Didn't have enough viable instances to create stats")
        rt = dict()
        for key, value in stats.items():
            rt[key] = value / total
        return rt

    @staticmethod
    def join_stats_same_source(first: Dict[Any, int], second: Dict[Any, int]) -> Dict[Any, int]:
        rt = {}
        rt.update(first)
        for key, value in second.items():
            if key in rt:
                rt[key] += value
            else:
                rt[key] = value
        return rt

    def join_stats_diff_sources(self, all_stats: List[Dict[Any, int]]):
        """
        idea - sources have MORE common instances, but not LESS common instances (rather all words instances less common
        to make place for the common ones).
        i.e. for an instance w the real probability of it appearing P(w) is either close to the measured probability
        P_mes(w) or much lower than it.
        :param all_stats:
        :return:
        """
        as_percent = map(self.count_to_percent, all_stats)
        total_count = sum(map(self.count_to_total, all_stats))

        rt: Dict[Any, List[float]] = {}
        for elem in as_percent:
            for key, value in elem.items():
                if key not in rt:
                    rt[key] = [value]
                else:
                    rt[key].append(value)

        rt_medians: Dict[Any, float] = {}
        for key, value in rt.items():
            to_use = value + [0] * (len(all_stats) - len(value))
            to_use = sorted(to_use)
            if len(to_use) % 2 == 1:
                rt_medians[key] = to_use[len(to_use) // 2]
            else:
                rt_medians[key] = (to_use[len(to_use) // 2] + to_use[(len(to_use) // 2) - 1]) * 0.5

        total_percent = 0
        for value in rt_medians.values():
            total_percent += value

        real_rt: Dict[Any, int] = {}
        # Normalize and convert back to count
        for key in rt.keys():
            real_rt[key] = int((rt_medians[key] / total_percent) * total_count + 0.5)
        return real_rt

    @abc.abstractmethod
    def process_file(self, file_data: str) -> Dict[Any, int]:
        pass

    def process_folder(self, target_folder: str) -> Dict[Any, int]:
        if not os.path.isdir(target_folder):
            raise ValueError(f"{target_folder} is not a directory")
        all_stats = []
        for element in glob.glob(target_folder + "/*"):
            if os.path.isdir(element):
                print(f"Processing {element}")
                time.sleep(0.05)
                sub_stats = []
                for fl in tqdm(glob.glob(element + "/*")):
                    if os.path.isfile(fl):
                        with open(fl, "r", encoding='utf-8') as f:
                            sub_stats.append(self.process_file(f.read()))
                all_stats.append(functools.reduce(self.join_stats_same_source, sub_stats, {}))

        final_stats = self.join_stats_diff_sources(all_stats)

        return final_stats


if __name__ == "__main__":
    # char_reader = KanjiStatsReader()
    # res = char_reader.process_folder(r"C:\Users\Alexey\Documents\subs")
    # print(len(res))
    # data = sorted(res.items(), key=lambda key_val: key_val[1], reverse=True)
    # print(data)

    from jamdict import Jamdict

    jam = Jamdict()

    # print(data[0], jam.krad[data[0][0]])
