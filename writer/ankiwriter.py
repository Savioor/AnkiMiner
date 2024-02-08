import os
import pathlib
import re
import shutil
from typing import Optional, Union, List

import anki.collection
import anki.decks
import anki.notes
from anki.models import NotetypeDict

from utils import generate_random_file_name, compute_file_hash, get_all_from_dict_list_by_value, json_t

_global_collections_loaded = {}


class AnkiWriter:
    ANKI_EXTENSION = '.anki2'
    MODEL_FIELDS_KEY = 'flds'
    DECK_ID = 'id'
    MODEL = 'model'
    FIELD_NAME_KEY = 'name'
    DECK_NAME = 'name'
    MODEL_NAME = 'name'
    DECK_PATH_TO_MEDIA_PATH = "collection.media"

    SOUND_FILES = [".wav", ".mp3"]
    IMAGE_FILES = [".jpg", ".png", ".jpeg"]
    ALLOWED_FILES = SOUND_FILES + IMAGE_FILES

    def __init__(self, deck_path: str,
                 deck: Union[int, str]):
        """

        :param deck_path: A path to the `collection.anki2` file for the collection which will be edited.
        :param deck: A name of a deck (as a string) or the id of a deck (as an int) whose cards will be edited.
            The cards of this deck and more relevant information will be loaded into the object for simpler editing.
        """
        global _global_collections_loaded

        if not os.path.isfile(deck_path):
            raise ValueError(f"no file at path {deck_path}")
        if os.path.splitext(deck_path)[1] != self.ANKI_EXTENSION:
            raise ValueError(f"file type is {os.path.splitext(deck_path)[1]} and not {self.ANKI_EXTENSION}")

        self.__deck_path = pathlib.Path(deck_path)

        # Can't open the same collection twice, make sure we won't
        if deck_path in _global_collections_loaded:
            self._collection = _global_collections_loaded[deck_path]
        else:
            self._collection: anki.collection.Collection = anki.collection.Collection(deck_path)
            _global_collections_loaded[deck_path] = self._collection

        # Load deck information
        self.deck_name = deck
        self._deck: Optional[anki.decks.DeckDict] = None
        if type(deck) is int:
            self._deck = self._collection.decks.get(deck)
        elif type(deck) is str:
            all_matches = get_all_from_dict_list_by_value(self._collection.decks.all(), AnkiWriter.DECK_NAME, deck)
            if len(all_matches) != 1:
                raise RuntimeError(f"Invalid matches amount {len(all_matches)}")
            self._deck = self._collection.decks.get(all_matches[0]['id'])
        if self._deck is None:
            raise RuntimeError("Deck initialization failed")

        self._notes: List[anki.notes.Note] = list(
            map(self._collection.get_note, self._collection.find_notes(f"\"deck:{self._deck['name']}\"")))

    def get_model(self, name_or_id: Union[str, int]) -> NotetypeDict:
        """

        :param name_or_id: The name (str) or the id (int) of the desired model to get.
        :return: The model as a `NotetypeDict`, as returned by the Anki python library. This is just a python dictionary
            that has information about the model. Note that this object can't edited (or rather, changes will not be
            reflected in the model).
        """
        if type(name_or_id) not in [str, int]:
            raise TypeError(f"name_or_id was {type(name_or_id)} expected int or str")
        if type(name_or_id) is int:
            options = get_all_from_dict_list_by_value(self._collection.models.all(), "id", name_or_id)
        else:
            options = get_all_from_dict_list_by_value(self._collection.models.all(), "name", name_or_id)

        if len(options) != 1:
            raise RuntimeError(f"Invalid matches amount {len(options)}")
        return options[0]

    @staticmethod
    def model_to_flds_list(model: NotetypeDict) -> List[str]:
        """
        This is a helper function, to extract data from a dict representing a model
        :param model: A dictionary representing an Anki model
        :return: A list of all the field names for the given model
        """
        if AnkiWriter.MODEL_FIELDS_KEY not in model or type(model[AnkiWriter.MODEL_FIELDS_KEY]) is not list:
            raise RuntimeError(f"model didn't include {AnkiWriter.MODEL_FIELDS_KEY} field or type wasn't list")

        fields = model[AnkiWriter.MODEL_FIELDS_KEY]
        ret = []
        for field in fields:
            if type(field) is not dict or AnkiWriter.FIELD_NAME_KEY not in field or type(
                    field[AnkiWriter.FIELD_NAME_KEY]) is not str:
                raise RuntimeError(f"Invalid field {field} encountered")
            ret.append(field[AnkiWriter.FIELD_NAME_KEY])
        if len(set(ret)) != len(ret):
            raise RuntimeError("Fields with the same name found")

        return ret

    def add_media_file(self, file_name: str, collection_data_path: Optional[str] = None) -> pathlib.Path:
        """
        Adds the file at the given path into the media folder of the collection. If the file is already in the
        collection it is not added again.
        :param file_name: The location of the file to add
        :param collection_data_path: The location of the data files for the collection. When None is passed, the
            path of the data folder is interpolated from the path of the collection.
        :return: A Path object pointing to the new/existing file.
        """
        if collection_data_path is None:
            collection_data_path = self.__deck_path.parent.joinpath(AnkiWriter.DECK_PATH_TO_MEDIA_PATH)
        else:
            collection_data_path = pathlib.Path(collection_data_path)

        if not collection_data_path.is_dir():
            raise ValueError(f"{collection_data_path} is not a directory")
        if not os.path.isfile(file_name):
            raise ValueError(f"{file_name} isn't valid file")
        if os.path.splitext(file_name)[1] not in self.ALLOWED_FILES:
            print(f"file type of {file_name} not allowed.")

        given_sha = compute_file_hash(file_name)

        for inner in collection_data_path.iterdir():
            # We check if the size is the same to skip most sha256 calculations
            if inner.is_file() and os.path.getsize(file_name) == inner.stat().st_size:
                if given_sha == compute_file_hash(inner.absolute().__str__()):
                    print(f"Sha of {file_name} already in collection")
                    return inner

        new_name = generate_random_file_name(collection_data_path, os.path.splitext(file_name)[1])
        shutil.copyfile(file_name, new_name)
        return new_name

    def handle_file_field(self, note: anki.notes.Note, key: str, field: str):
        if not os.path.isfile(field) or os.path.islink(field):
            raise ValueError(f"{field} is not a file.")

        extension = os.path.splitext(field)[-1]
        actual_file_path = self.add_media_file(field).name
        actual_field_val = None
        if extension in self.SOUND_FILES:
            actual_field_val = f"[sound:{actual_file_path}]"
        elif extension in self.IMAGE_FILES:
            actual_field_val = f'<img src="{actual_file_path}">'
        if actual_field_val is None:
            raise RuntimeError("Couldn't build actual field value for file")

        note[key] = actual_field_val

    def json_to_note(self, input_json: json_t, auto_handle_files: bool = True,
                     marked_as_file: List[str] = None) -> anki.notes.Note:
        if AnkiWriter.MODEL not in input_json or type(input_json[AnkiWriter.MODEL]) not in [int, str]:
            raise ValueError(f"json didn't include valid {AnkiWriter.MODEL} key")
        if marked_as_file is None:
            marked_as_file = []

        model = self.get_model(input_json[AnkiWriter.MODEL])
        input_json.pop(AnkiWriter.MODEL)

        fields = self.model_to_flds_list(model)
        for field in fields:
            if field not in input_json:
                raise RuntimeError(f"{field} not in input json")
        for key in input_json.keys():
            if key not in fields:
                raise RuntimeError(f"{key} from json not a valid field")
        note = anki.notes.Note(self._collection, model)

        for key in input_json.keys():
            val = input_json[key]
            if (auto_handle_files or (key in marked_as_file)) and os.path.isfile(val):
                self.handle_file_field(note, key, val)
            else:
                if key in marked_as_file:
                    raise RuntimeError(f"{key} should be file but wasn't")
                note[key] = val

        self._collection.add_note(note, self._deck.get(self.DECK_ID))

        cards = note.cards()
        for card in cards:
            card.did = self._deck.get(self.DECK_ID)
        for card in cards:
            self._collection.update_card(card)

        self._collection.update_note(note)

        return note

    def get_notes_by_value(self, field: str, value: str) -> List[anki.notes.Note]:
        return list(filter(lambda a: field in a.keys() and a[field] == value, self._notes))

    def handle_file_fields_export(self, value: str) -> Optional[pathlib.Path]:
        """

        :param value:
        :return: Full path to the file in the field, or None if no file in field.
        """
        pattern = re.compile(r"([a-zA-Z0-9 ._\-]+\.[a-zA-Z0-9]{2,5})")

        results = pattern.findall(value)
        if len(results) == 0:
            return None
        if len(results) > 1:
            raise RuntimeError(f"More than one valid filename found at {value}")

        fp = results[0]

        full_fp = self.__deck_path.parent.joinpath(AnkiWriter.DECK_PATH_TO_MEDIA_PATH).joinpath(fp)
        if not full_fp.is_file():
            raise RuntimeError(f"File {full_fp} was found but wasn't a file")

        return full_fp

    def export_note_into_json(self, note: anki.notes.Note,
                              marked_as_file: List[str] = None,
                              marked_as_not_files: List[str] = None) -> json_t:
        rt_json = {self.MODEL: note.note_type()[self.MODEL_NAME]}

        if marked_as_file is None:
            marked_as_file = []
        if marked_as_not_files is None:
            marked_as_not_files = []

        for field in marked_as_file:
            if field in marked_as_not_files:
                raise RuntimeError(f"{field} was marked as both file and not file")

        for field in note.keys():
            value = note[field]
            if field in marked_as_not_files:
                rt_json[field] = value
                continue
            as_path = self.handle_file_fields_export(value)
            if as_path is None and field in marked_as_file:
                raise RuntimeError(f"{field} should be a file but wasn't")
            if as_path is not None and field not in marked_as_file:
                raise RuntimeError(f"{field} was file but wasn't marked")
            if as_path is None:
                rt_json[field] = value
            else:
                rt_json[field] = str(as_path)

        return rt_json


if __name__ == "__main__":
    writer = AnkiWriter(r"C:\Users\Alexey\AppData\Roaming\Anki2\Main\collection.anki2",
                        r"Tae Kim's Grammar Guide Exercises and Flashcards")

    for d in writer._notes:
        print(d.values())

    print(writer.export_note_into_json(writer._notes[-1],
                                       marked_as_file=["Screenshot", "Audio"]))

    # writer._notes[0].note_type()
    # print(writer._notes[0][writer._notes[0].keys()[0]])
    # json_to_load = {
    #     "model": "Mined From Anime",
    #     "Target": "両立",
    #     "Screenshot": r"C:\Users\Alexey\Pictures\Screenshots\shirokuma-1-0822.png",
    #     "Target-Eng": "compatibility",
    #     "Line-English": "Who, me? I wonder if I could handle being both a customer and a part-timer",
    #     "Target-Spelling": "りょうりつ",
    #     "Audio": r"C:\Users\Alexey\Documents\Audacity\shirokuma-1-0831.wav",
    #     "Line-Furigana": "え？ぼく  お 客[きゃく]とバイトの 両立[りょうりつ]  できるかな"
    # }
    # writer.json_to_note(json_to_load, marked_as_file=["Audio", "Screenshot"])
