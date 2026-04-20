from dataclasses import dataclass
from typing import Optional


@dataclass
class WordEntry:
    word: str = ""
    phonetic: str = ""
    translation: str = ""
    definition: str = ""
    example: str = ""
    example_cn: str = ""
    audio_url: str = ""
