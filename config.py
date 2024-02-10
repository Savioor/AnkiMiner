import toml


class __Config:

    def __init__(self, path: str):
        with open(path, "r") as f:
            self.config = toml.load(f)

    def __getitem__(self, item):
        return self.config[item]

    def __setitem__(self, key, value):
        self.config[key] = value


MAIN_CFG = __Config(__file__[:-3] + ".toml")


if __name__ == "__main__":

    example = {
        "collection": r"C:\Users\Alexey\AppData\Roaming\Anki2\Main\collection.anki2",
        "main_deck": r"My Mined Cards",
        "main_model": r"Mined From Anime"
    }

    with open("example.toml", "w") as f:
        toml.dump(example, f)
