from studyapp.core.database import get_connection
from .models import WordEntry


def get_all_vocab():
    rows = get_connection().execute(
        "SELECT * FROM vocabulary ORDER BY created_at DESC"
    ).fetchall()
    return [WordEntry(
        word=r['word'],
        phonetic=r['phonetic'],
        translation=r['translation'],
        definition=r['definition'],
        example=r['example'],
        example_cn=r['example_cn'],
        audio_url=r['audio_url'],
    ) for r in rows]


def get_vocab(word: str) -> WordEntry | None:
    r = get_connection().execute(
        "SELECT * FROM vocabulary WHERE word = ?", (word,)
    ).fetchone()
    if not r:
        return None
    return WordEntry(
        word=r['word'],
        phonetic=r['phonetic'],
        translation=r['translation'],
        definition=r['definition'],
        example=r['example'],
        example_cn=r['example_cn'],
        audio_url=r['audio_url'],
    )


def delete_vocab(word: str):
    """从生词本中删除指定单词"""
    conn = get_connection()
    conn.execute("DELETE FROM vocabulary WHERE word = ?", (word,))
    conn.commit()


def delete_vocab_by_card_id(card_id: int):
    """通过关联的卡片ID删除生词本记录"""
    conn = get_connection()
    conn.execute("DELETE FROM vocabulary WHERE card_id = ?", (card_id,))
    conn.commit()


def save_or_update_vocab(entry: WordEntry, card_id: int | None = None):
    conn = get_connection()
    existing = conn.execute(
        "SELECT id, lookup_count FROM vocabulary WHERE word = ?", (entry.word,)
    ).fetchone()

    if existing:
        conn.execute(
            """UPDATE vocabulary SET phonetic=?, translation=?, definition=?,
               example=?, example_cn=?, audio_url=?, lookup_count=?
               WHERE word=?""",
            (entry.phonetic, entry.translation, entry.definition,
             entry.example, entry.example_cn, entry.audio_url,
             existing['lookup_count'] + 1, entry.word),
        )
    else:
        conn.execute(
            """INSERT INTO vocabulary (word, phonetic, translation, definition,
               example, example_cn, audio_url, card_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (entry.word, entry.phonetic, entry.translation, entry.definition,
             entry.example, entry.example_cn, entry.audio_url, card_id),
        )
    conn.commit()
