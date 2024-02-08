import os
import re
from typing import List, Optional, Tuple

from utils import parse_timestamp


def timestamp_to_str(stamp: float) -> str:
    minute = int(stamp / 60)
    seconds = round(stamp - 60 * int(stamp / 60), 2)
    return str(minute) + ":" + str(seconds)


def align(value: str, size: int) -> str:
    if len(value) > size:
        raise RuntimeError("Can't pad")
    return value + " " * (size - len(value))


class SubtitleEvent:

    def __init__(self, t0: float, t1: float, text: str):
        if min(t0, t1) < 0 or t1 < t0:
            raise ValueError(f"{t0}-{t1} is invalid as a timestamp")
        self.t0 = t0
        self.t1 = t1
        self.text = text

    def is_within(self, t: float) -> bool:
        return self.t0 <= t <= self.t1

    def __str__(self):
        return align(f"{timestamp_to_str(self.t0)} - {timestamp_to_str(self.t1)}", 32) + self.text

    def __repr__(self):
        return self.__str__()


class GenericReader:

    def __init__(self, sub_file: str):
        if not os.path.isfile(sub_file):
            raise ValueError(f"no file at path {sub_file}")
        if os.path.splitext(sub_file)[1] not in self.get_allowed_extensions():
            raise ValueError(f"file type is {os.path.splitext(sub_file)[1]} and not allowed type")

    @staticmethod
    def get_allowed_extensions() -> List[str]:
        raise RuntimeError("Not Implemented")

    def get_all_lines_and_time_ranges(self, timestamp: float) -> List[SubtitleEvent]:
        raise RuntimeError("Not Implemented")


class SrtReader(GenericReader):

    def __init__(self, sub_file: str):
        super().__init__(sub_file)

        self.events: List[SubtitleEvent] = []

        with open(sub_file, "r", encoding='utf-8') as f:
            lines = f.read().splitlines()

        while len(lines) != 0:
            lines, to_add = self.parse_sub(lines, len(self.events))
            self.events.append(to_add)

    @staticmethod
    def parse_sub(lines: List[str], prev_index: int) -> Tuple[List[str], SubtitleEvent]:
        if len(lines) < 3:
            raise RuntimeError("Not enough lines for subtitle line")

        # ind = lines[0].strip()
        # print(ind[0], len(ind))
        # assert ind.isnumeric(), "Index wasn't numeric"
        # ind = int(ind)
        # assert ind == prev_index + 1, "Missed an index"

        start, arrow, end = lines[1].partition("-->")
        assert arrow == "-->", "Time range has no end time"
        start_t = SrtReader.parse_srt_timestamp(start.strip())
        end_t = SrtReader.parse_srt_timestamp(end.strip())
        assert end_t >= start_t, "end time was before start time"

        line_count = 0
        total_sub = ""
        for line in lines[2:]:
            line = line.strip()
            if len(line) == 0:
                break
            line_count += 1
            if len(total_sub) != 0:
                total_sub += "\n"
            total_sub += line

        return lines[3 + line_count:], SubtitleEvent(start_t, end_t, total_sub)

    @staticmethod
    def parse_srt_timestamp(stamp: str):
        return parse_timestamp(stamp, "%h:%m:%s,%M")

    @staticmethod
    def get_allowed_extensions() -> List[str]:
        return [".srt"]

    def get_all_lines_and_time_ranges(self, timestamp: float) -> List[SubtitleEvent]:
        return list(filter(lambda e: e.is_within(timestamp), self.events))


class AssReader(GenericReader):
    ASS_HEADER_OPENER = "["
    ASS_HEADER_CLOSER = "]"
    ASS_EVENTS_HEADER = "Events"
    ASS_HEADER_RE = re.compile(r"^\s*\[.*]\s*$")
    ASS_COMMENT_LINE = "Comment"
    ALLOWED_SUBTITLE_TYPES = ["Dialogue", "Comment"]
    ASS_FORMAT = "Format"
    ASS_START = "Start"
    ASS_END = "End"
    ASS_TEXT = "Text"

    def __init__(self, sub_file: str, strict: bool = True):
        super().__init__(sub_file)
        with open(sub_file, "r", encoding='utf-8') as f:
            file_data = f.read()
        self.as_lines = file_data.splitlines()
        self.strict = strict

        self.event_starts = self.get_all_section_starts(self.ASS_EVENTS_HEADER)
        self.event_ends = list(map(lambda i: self.get_section_end_by_start(i), self.event_starts))

    def get_all_lines_and_time_ranges(self, timestamp: float) -> List[SubtitleEvent]:
        rt_list = []
        for start, end in zip(self.event_starts, self.event_ends):
            if end <= start + 1:
                raise RuntimeError("No format line available")
            format_line = self.as_lines[start + 1]
            tp, colon, data = format_line.partition(": ")
            if tp != self.ASS_FORMAT or colon != ": ":
                raise RuntimeError("No format line found")
            splat = data.split(", ")
            t0 = splat.index(self.ASS_START)
            t1 = splat.index(self.ASS_END)
            txt = splat.index(self.ASS_TEXT)

            if txt != len(splat) - 1:
                raise ValueError("Text must be last in format file")

            for i in range(start + 2, end):
                event = self.ass_line_to_sub_event(self.as_lines[i],
                                                   t0,
                                                   t1,
                                                   len(splat))
                if event is not None and event.is_within(timestamp):
                    rt_list.append(event)

        return rt_list

    def get_all_section_starts(self, header: str) -> List[int]:
        rt = []
        for line, i in zip(self.as_lines, range(len(self.as_lines))):
            if self.get_header_value(line) == header:
                rt.append(i)
        if self.strict and len(rt) != 1:
            raise RuntimeError("Invalid header requested")
        return rt

    def get_section_end_by_start(self, index: int) -> int:
        if index < 0 or index >= len(self.as_lines):
            raise ValueError("Bad index given")
        if not self.is_header(self.as_lines[index]):
            raise ValueError("Line given isn't header")

        for j in range(index + 1, len(self.as_lines)):
            if self.is_header(self.as_lines[j]):
                return j

        return len(self.as_lines)

    def ass_line_to_sub_event(self, line: str, start_ind: int, end_ind: int,
                              amount_of_fields: int) -> Optional[SubtitleEvent]:
        tp, colon, line = line.partition(": ")
        if colon != ": " or tp not in self.ALLOWED_SUBTITLE_TYPES:
            raise ValueError(f"{tp} is invalid file or no line given")
        if tp == self.ASS_COMMENT_LINE:
            return None
        splat = line.split(",")
        if amount_of_fields <= min(start_ind, end_ind):
            raise ValueError("Parameters make no sense")
        if len(splat) <= max(start_ind, end_ind, amount_of_fields - 1):
            raise RuntimeError(f"Line {line} isn't in proper format")
        return SubtitleEvent(self.parse_ass_timestamp(splat[start_ind]),
                             self.parse_ass_timestamp(splat[end_ind]),
                             ",".join(splat[amount_of_fields - 1:]))

    @staticmethod
    def parse_ass_timestamp(stamp: str):
        return parse_timestamp(stamp, "%h:%m:%s.%C")

    @staticmethod
    def get_header_value(line: str) -> Optional[str]:
        if AssReader.ASS_HEADER_RE.match(line) is None:
            return None
        return line[line.index(AssReader.ASS_HEADER_OPENER) + 1:
                    line.index(AssReader.ASS_HEADER_CLOSER)]

    @staticmethod
    def is_header(line: str):
        return AssReader.get_header_value(line) is not None

    @staticmethod
    def get_allowed_extensions() -> List[str]:
        return [".ass"]


class MasterReader(GenericReader):
    _all_readers = (SrtReader, AssReader)

    def __init__(self, sub_file: str):
        super().__init__(sub_file)
        ext = os.path.splitext(sub_file)[1]
        self.worker = None
        for reader in self._all_readers:
            if ext in reader.get_allowed_extensions():
                self.worker = reader(sub_file)
                break
        if self.worker is None:
            raise RuntimeError("This is not supposed to happen....")

    @staticmethod
    def get_allowed_extensions() -> List[str]:
        rt = []
        for r in MasterReader._all_readers:
            rt += r.get_allowed_extensions()
        return rt

    def get_all_lines_and_time_ranges(self, timestamp: float) -> List[SubtitleEvent]:
        return self.worker.get_all_lines_and_time_ranges(timestamp)


if __name__ == "__main__":
    sub_file = r"C:\Users\Alexey\Downloads\My_Neighbor_Totoro_(1988)_[1080p,BluRay,x264,flac]_-_THORA v2 - JP.srt"
    reader = MasterReader(sub_file)
    print(reader.worker.events)
    print(reader.get_all_lines_and_time_ranges(11.5))
