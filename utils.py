import hashlib
import pathlib
import random
from typing import Union, Dict, List, Any, Tuple

number = Union[float, int]
json_value = Union[number, str, bool, List, Dict, None]
json_key = str
json_t = Dict[json_key, json_value]


def get_all_from_dict_list_by_value(dictio: List[Dict], key: Any, value: Any) -> List[Dict]:
    return list(filter(lambda a: key in a and a[key] == value, dictio))


def compute_file_hash(file_name: str) -> str:
    hash_sha256 = hashlib.sha256()
    with open(file_name, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def generate_random_file_name(location: pathlib.Path,
                              extension: str,
                              char_amount: int = 12,
                              max_tries: int = 1000):
    char_options = "abcdefghijklmnopqrstuvwxyz"
    char_options += str.upper(char_options)
    char_options += "0123456789"
    for _ in range(max_tries):
        curr_try = ""
        for __ in range(char_amount):
            curr_try += random.choice(char_options)
        if location.joinpath(curr_try + extension).is_file():
            continue
        return location.joinpath(curr_try + extension)
    raise RuntimeError(f"Tried {max_tries} names of length {char_options} and couldn't find any non taken names")


class _Marker:

    def __init__(self,
                 char_amount: int,
                 base_value: float,
                 strict: bool = True):
        assert char_amount > 0
        assert base_value > 0
        self.length = char_amount
        self.base = base_value
        self.strict = strict

    def parse(self, source: str) -> Tuple[str, float]:
        substr = ""
        for c in source:
            if len(substr) == self.length:
                break
            if not c.isnumeric():
                break
            substr += c

        if len(substr) != self.length and self.strict:
            raise ValueError(f"{source} is an invalid stamp")

        return source[len(substr):], int(substr) * self.base


_formats = {
    "M": _Marker(3, 0.001, True),
    "C": _Marker(2, 0.01, True),
    "s": _Marker(2, 1.0, True),
    "m": _Marker(2, 60.0, False),
    "h": _Marker(2, 60.0 * 60.0, False)
}


def parse_timestamp(stamp: str, fmt: str) -> float:
    curr = stamp
    curr_f = fmt
    total = 0
    while len(curr) != 0:
        if len(curr_f) == 0:
            raise RuntimeError(f"Can't parse {stamp} for format {fmt}")

        if curr_f[0] == '%':

            if len(curr_f) <= 1:
                raise RuntimeError(f"Can't parse {stamp} for format {fmt}")
            curr, to_add = _formats[curr_f[1]].parse(curr)
            total += to_add
            curr_f = curr_f[2:]

        else:
            if curr[0] != curr_f[0]:
                raise RuntimeError(f"Can't parse {stamp} for format {fmt}")

            curr = curr[1:]
            curr_f = curr_f[1:]

    if len(curr_f) != 0:
        raise RuntimeError(f"Can't parse {stamp} for format {fmt}")

    return total


if __name__ == "__main__":
    print(parse_timestamp("12:42.11", "%m:%s.%Msdfsdf"))
