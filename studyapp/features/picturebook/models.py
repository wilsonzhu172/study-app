from dataclasses import dataclass


@dataclass
class BookRecord:
    id: int | None = None
    date: str = ""
    book_count: int = 0
    accuracy: float = 0.0
    created_at: str = ""
