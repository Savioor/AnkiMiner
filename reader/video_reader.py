import os
import pathlib

import moviepy.editor as movp

from utils import generate_random_file_name


class VideoReader:
    ALLOWED_VIDEO_FILES = [".mkv", ".mp4"]
    AUDIO_OUT = ".wav"
    IMAGE_OUT = ".png"

    def __init__(self, video_loc: str, save_loc=""):
        if not os.path.isfile(video_loc):
            raise ValueError(f"no file at path {video_loc}")
        if os.path.splitext(video_loc)[1] not in self.ALLOWED_VIDEO_FILES:
            raise ValueError(f"file type is {os.path.splitext(video_loc)[1]} and not allowed video type")

        self.vid = movp.VideoFileClip(video_loc)
        if len(save_loc) == "":
            self.path_to_use = pathlib.Path(os.getcwd()).parent
        else:
            self.path_to_use = pathlib.Path(save_loc)
        self.my_files = []

    def extract_audio(self, sec_start: float, sec_end: float) -> pathlib.Path:
        if sec_start < 0 or sec_start >= sec_end or sec_end > self.vid.duration:
            raise ValueError(f"Invalid timestamp {sec_end}-{sec_end}")
        file_name = generate_random_file_name(self.path_to_use, self.AUDIO_OUT)
        self.vid.audio.subclip(sec_start, sec_end).write_audiofile(file_name)
        self.my_files.append(file_name)
        return file_name

    def extract_image(self, image_timestamp: float) -> pathlib.Path:
        if image_timestamp < 0 or image_timestamp > self.vid.duration:
            raise ValueError(f"Invalid timestamp {image_timestamp}")
        file_name = generate_random_file_name(self.path_to_use, self.IMAGE_OUT)
        self.vid.save_frame(file_name, t=image_timestamp)
        self.my_files.append(file_name)
        return file_name

    def clear_everything(self):
        for file in self.my_files:
            file.unlink()
        self.my_files = []


if __name__ == "__main__":
    t0 = 8 * 60 + 44.95
    t1 = 8 * 60 + 47.34
    vid_reader = VideoReader(
        r"C:\Users\Alexey\Downloads\[Orphan] Shirokuma Cafe (BD 720p)\[Orphan] Shirokuma Cafe - 01v2 (BD 720p) [35A192D6].mkv")
    vid_reader.extract_image((t0 + t1) / 2)
    vid_reader.extract_audio(t0, t1)
    vid_reader.clear_everything()
