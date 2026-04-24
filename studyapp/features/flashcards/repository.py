from studyapp.core.database import get_connection
from .models import Deck, Card, StudyRecord


# --- Decks ---

def get_decks():
    rows = get_connection().execute(
        "SELECT * FROM decks ORDER BY is_system DESC, created_at"
    ).fetchall()
    return [Deck(**dict(r)) for r in rows]


def get_deck(deck_id: int) -> Deck | None:
    r = get_connection().execute(
        "SELECT * FROM decks WHERE id = ?", (deck_id,)
    ).fetchone()
    return Deck(**dict(r)) if r else None


def get_vocab_deck_id() -> int | None:
    r = get_connection().execute(
        "SELECT id FROM decks WHERE is_system = 1"
    ).fetchone()
    return r['id'] if r else None


def get_daily_deck_id() -> int | None:
    r = get_connection().execute(
        "SELECT id FROM decks WHERE is_system = 2"
    ).fetchone()
    return r['id'] if r else None


def add_to_daily_deck(deck_id: int, word: str, back: str):
    """在当日生词本中添加卡片（按 source_ref 去重）"""
    existing = get_card_by_source_ref(deck_id, word)
    if existing:
        return
    create_card(deck_id, word, back, source='dictionary', source_ref=word)


def create_deck(name: str, description: str = "", color: str = "#4CAF50", daily_new_limit: int = 20) -> int:
    cur = get_connection().execute(
        "INSERT INTO decks (name, description, color, daily_new_limit) VALUES (?, ?, ?, ?)",
        (name, description, color, daily_new_limit),
    )
    get_connection().commit()
    return cur.lastrowid


def update_deck(deck_id: int, name: str = None, description: str = None, color: str = None):
    parts, vals = [], []
    if name is not None:
        parts.append("name = ?"); vals.append(name)
    if description is not None:
        parts.append("description = ?"); vals.append(description)
    if color is not None:
        parts.append("color = ?"); vals.append(color)
    if not parts:
        return
    vals.append(deck_id)
    get_connection().execute(
        f"UPDATE decks SET {', '.join(parts)} WHERE id = ?", vals
    )
    get_connection().commit()


def delete_deck(deck_id: int):
    get_connection().execute("DELETE FROM decks WHERE id = ? AND is_system = 0", (deck_id,))
    get_connection().commit()


def update_deck_daily_limit(deck_id: int, limit: int):
    get_connection().execute(
        "UPDATE decks SET daily_new_limit = ? WHERE id = ?", (limit, deck_id)
    )
    get_connection().commit()


def checkin_deck(deck_id: int):
    """标记牌组今日已打卡"""
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    get_connection().execute(
        "UPDATE decks SET last_checkin = ? WHERE id = ?", (today, deck_id)
    )
    get_connection().commit()


def is_deck_checked_in(deck_id: int) -> bool:
    """检查牌组今日是否已打卡（当日生词本不参与打卡）"""
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    r = get_connection().execute(
        "SELECT last_checkin, is_system FROM decks WHERE id = ?", (deck_id,)
    ).fetchone()
    if r is None or r['is_system'] == 2:
        return False
    return r['last_checkin'] == today


# --- Cards ---

def get_cards_by_deck(deck_id: int):
    rows = get_connection().execute(
        "SELECT * FROM cards WHERE deck_id = ? ORDER BY created_at", (deck_id,)
    ).fetchall()
    return [Card(**dict(r)) for r in rows]


def get_card(card_id: int) -> Card | None:
    r = get_connection().execute(
        "SELECT * FROM cards WHERE id = ?", (card_id,)
    ).fetchone()
    return Card(**dict(r)) if r else None


def get_card_by_source_ref(deck_id: int, source_ref: str) -> Card | None:
    r = get_connection().execute(
        "SELECT * FROM cards WHERE deck_id = ? AND source_ref = ?",
        (deck_id, source_ref),
    ).fetchone()
    return Card(**dict(r)) if r else None


def create_card(deck_id: int, front: str, back: str, source: str = "manual", source_ref: str = "") -> int:
    cur = get_connection().execute(
        "INSERT INTO cards (deck_id, front, back, source, source_ref) VALUES (?, ?, ?, ?, ?)",
        (deck_id, front, back, source, source_ref),
    )
    get_connection().commit()
    return cur.lastrowid


def update_card(card_id: int, front: str = None, back: str = None):
    parts, vals = [], []
    if front is not None:
        parts.append("front = ?"); vals.append(front)
    if back is not None:
        parts.append("back = ?"); vals.append(back)
    if not parts:
        return
    vals.append(card_id)
    get_connection().execute(
        f"UPDATE cards SET {', '.join(parts)} WHERE id = ?", vals
    )
    get_connection().commit()


def delete_card(card_id: int):
    get_connection().execute("DELETE FROM cards WHERE id = ?", (card_id,))
    get_connection().commit()


def get_card_count(deck_id: int) -> int:
    r = get_connection().execute(
        "SELECT COUNT(*) as cnt FROM cards WHERE deck_id = ?", (deck_id,)
    ).fetchone()
    return r['cnt']


def get_learned_count(deck_id: int) -> int:
    """统计已掌握卡片数 (level >= 5)"""
    r = get_connection().execute(
        """SELECT COUNT(*) as cnt FROM cards c
           JOIN card_progress cp ON cp.card_id = c.id
           WHERE c.deck_id = ? AND cp.level >= 5""",
        (deck_id,),
    ).fetchone()
    return r['cnt']


# --- Card Progress ---

def get_card_progress(card_id: int) -> dict | None:
    """获取卡片学习进度"""
    r = get_connection().execute(
        "SELECT * FROM card_progress WHERE card_id = ?", (card_id,)
    ).fetchone()
    return dict(r) if r else None


def upsert_card_progress(card_id: int, level: int, next_review: str):
    """插入或更新卡片进度"""
    conn = get_connection()
    existing = conn.execute(
        "SELECT card_id FROM card_progress WHERE card_id = ?", (card_id,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE card_progress SET level=?, next_review=?, review_count=review_count+1 WHERE card_id=?",
            (level, next_review, card_id),
        )
    else:
        conn.execute(
            "INSERT INTO card_progress (card_id, level, next_review, review_count) VALUES (?, ?, ?, 1)",
            (card_id, level, next_review),
        )
    conn.commit()


def get_due_cards(deck_id: int):
    """获取到期需复习的卡片 (next_review <= now, level < 5)"""
    rows = get_connection().execute(
        """SELECT c.* FROM cards c
           JOIN card_progress cp ON cp.card_id = c.id
           WHERE c.deck_id = ? AND cp.next_review <= datetime('now','localtime') AND cp.level < 5
           ORDER BY cp.level ASC, cp.next_review ASC""",
        (deck_id,),
    ).fetchall()
    return [Card(**dict(r)) for r in rows]


def get_new_cards(deck_id: int):
    """获取新卡片 (无进度记录)"""
    rows = get_connection().execute(
        """SELECT c.* FROM cards c
           LEFT JOIN card_progress cp ON cp.card_id = c.id
           WHERE c.deck_id = ? AND cp.card_id IS NULL
           ORDER BY c.created_at ASC""",
        (deck_id,),
    ).fetchall()
    return [Card(**dict(r)) for r in rows]


# --- Study Records ---

def add_study_record(card_id: int, grade: int):
    get_connection().execute(
        "INSERT INTO study_records (card_id, grade) VALUES (?, ?)",
        (card_id, grade),
    )
    get_connection().commit()


# --- Preset Decks ---

def get_preset_decks() -> list[dict]:
    """获取所有预设牌组（含卡片数和是否已导入）"""
    conn = get_connection()
    rows = conn.execute(
        """SELECT pd.*, COUNT(pc.id) as card_count
           FROM preset_decks pd
           LEFT JOIN preset_cards pc ON pc.preset_deck_id = pd.id
           GROUP BY pd.id ORDER BY pd.id"""
    ).fetchall()

    result = []
    for r in rows:
        imported = conn.execute(
            "SELECT id FROM decks WHERE preset_id = ?", (r['id'],)
        ).fetchone()
        result.append({
            'id': r['id'],
            'name': r['name'],
            'description': r['description'],
            'color': r['color'],
            'card_count': r['card_count'],
            'imported': imported is not None,
        })
    return result


def import_preset_deck(preset_deck_id: int) -> int:
    """导入预设牌组为新的用户牌组，返回新牌组ID"""
    conn = get_connection()
    preset = conn.execute(
        "SELECT * FROM preset_decks WHERE id = ?", (preset_deck_id,)
    ).fetchone()
    if not preset:
        return 0

    cur = conn.execute(
        "INSERT INTO decks (name, description, color, preset_id) VALUES (?, ?, ?, ?)",
        (preset['name'], preset['description'], preset['color'], preset_deck_id),
    )
    deck_id = cur.lastrowid

    cards = conn.execute(
        "SELECT front, back FROM preset_cards WHERE preset_deck_id = ?",
        (preset_deck_id,),
    ).fetchall()
    for card in cards:
        conn.execute(
            "INSERT INTO cards (deck_id, front, back) VALUES (?, ?, ?)",
            (deck_id, card['front'], card['back']),
        )
    conn.commit()
    return deck_id
