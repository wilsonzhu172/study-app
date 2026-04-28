from datetime import datetime

from studyapp.core.database import get_connection
from .models import BookRecord


def get_today_record() -> BookRecord | None:
    today = datetime.now().strftime('%Y-%m-%d')
    r = get_connection().execute(
        "SELECT * FROM picture_book_records WHERE date = ?", (today,)
    ).fetchone()
    return BookRecord(**dict(r)) if r else None


def get_record_by_date(date: str) -> BookRecord | None:
    r = get_connection().execute(
        "SELECT * FROM picture_book_records WHERE date = ?", (date,)
    ).fetchone()
    return BookRecord(**dict(r)) if r else None


def upsert_record(book_count: int, accuracy: int, date: str = None):
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM picture_book_records WHERE date = ?", (date,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE picture_book_records SET book_count=?, accuracy=? WHERE date=?",
            (book_count, accuracy, date),
        )
    else:
        conn.execute(
            "INSERT INTO picture_book_records (date, book_count, accuracy) VALUES (?, ?, ?)",
            (date, book_count, accuracy),
        )
    conn.commit()


def get_recent_records(days: int = 7) -> list[BookRecord]:
    rows = get_connection().execute(
        """SELECT * FROM picture_book_records
           WHERE date >= date('now','localtime', ?)
           ORDER BY date""",
        (f'-{days} days',),
    ).fetchall()
    return [BookRecord(**dict(r)) for r in rows]


def get_stats(days: int) -> dict:
    """获取指定天数范围内的统计: 总本数, 平均正确率"""
    r = get_connection().execute(
        """SELECT COALESCE(SUM(book_count), 0) as total_books,
                  COALESCE(AVG(accuracy), 0) as avg_acc
           FROM picture_book_records
           WHERE date >= date('now','localtime', ?)""",
        (f'-{days} days',),
    ).fetchone()
    return {'total_books': r['total_books'], 'avg_accuracy': round(r['avg_acc'])}
