import os
import re
from typing import List, Optional


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

    def get_allowed_extensions(self) -> List[str]:
        raise RuntimeError("Not Implemented")

    def get_all_lines_and_time_ranges(self, timestamp: float) -> List[SubtitleEvent]:
        raise RuntimeError("Not Implemented")


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
        splat = stamp.split(":")
        if len(splat) != 3:
            raise RuntimeError(f"String {stamp} given wasn't ass timestamp")

        seconds, dot, hundrenths = splat[-1].partition(".")

        if (len(splat[0]) != 1 or len(splat[1]) != 2
                or len(seconds) != 2 or len(hundrenths) != 2):
            raise RuntimeError(f"String {stamp} given wasn't ass timestamp")

        for elem in splat[:-1]:
            if not elem.isnumeric():
                raise ValueError(f"{elem} isn't numeric")

        if not (seconds.isnumeric() and hundrenths.isnumeric()):
            raise ValueError(f"{splat[-1]} isn't numeric")

        hours = int(splat[0])
        minutes = int(splat[1])

        return 60 * 60 * hours + 60 * minutes + int(seconds) + int(hundrenths) / 100

    @staticmethod
    def get_header_value(line: str) -> Optional[str]:
        if AssReader.ASS_HEADER_RE.match(line) is None:
            return None
        return line[line.index(AssReader.ASS_HEADER_OPENER) + 1:
                    line.index(AssReader.ASS_HEADER_CLOSER)]

    @staticmethod
    def is_header(line: str):
        return AssReader.get_header_value(line) is not None

    def get_allowed_extensions(self) -> List[str]:
        return [".ass"]


if __name__ == "__main__":
    sub_file = r"C:\Users\Alexey\Downloads\[Kamigami - Fixed Timing] Shirokuma Cafe 1-50 subs(1)\[Kamigami - Fixed Timing] Shirokuma Cafe - 01 [1280x720 x264 AAC Sub(GB,BIG5,JP)_track5_und.ass"
    reader = AssReader(sub_file)
    print(reader.get_all_lines_and_time_ranges(7 * 60 + 54))
