from dataclasses import dataclass
from typing import Optional


@dataclass
class Deck:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    color: str = "#4CAF50"
    is_system: int = 0
    daily_new_limit: int = 20
    last_checkin: Optional[str] = None
    preset_id: Optional[int] = None
    created_at: str = ""


@dataclass
class Card:
    id: Optional[int] = None
    deck_id: int = 0
    front: str = ""
    back: str = ""
    source: str = "manual"
    source_ref: str = ""
    created_at: str = ""


@dataclass
class StudyRecord:
    id: Optional[int] = None
    card_id: int = 0
    grade: int = 0
    studied_at: str = ""
