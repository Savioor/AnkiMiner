import hashlib
import pathlib
import random
from typing import Union, Dict, List, Any

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
