import sqlite3
import csv
import os
import shutil
from .paths import get_db_path, get_backup_db_path

_connection = None


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        db_path = get_db_path()
        _connection = sqlite3.connect(db_path)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA foreign_keys = ON")
    return _connection


def close_connection():
    global _connection
    if _connection:
        _connection.close()
        _connection = None


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS decks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            color       TEXT DEFAULT '#4CAF50',
            is_system   INTEGER DEFAULT 0,
            daily_new_limit INTEGER DEFAULT 20,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS cards (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id     INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
            front       TEXT NOT NULL,
            back        TEXT NOT NULL,
            source      TEXT DEFAULT 'manual',
            source_ref  TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS study_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id     INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            grade       INTEGER NOT NULL,
            studied_at  TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS vocabulary (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            word         TEXT NOT NULL UNIQUE,
            phonetic     TEXT DEFAULT '',
            translation  TEXT DEFAULT '',
            definition   TEXT DEFAULT '',
            example      TEXT DEFAULT '',
            example_cn   TEXT DEFAULT '',
            audio_url    TEXT DEFAULT '',
            lookup_count INTEGER DEFAULT 1,
            card_id      INTEGER DEFAULT NULL,
            created_at   TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS card_progress (
            card_id       INTEGER PRIMARY KEY REFERENCES cards(id) ON DELETE CASCADE,
            level         INTEGER DEFAULT 0,
            next_review   TEXT DEFAULT (datetime('now','localtime')),
            review_count  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS preset_decks (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            color       TEXT DEFAULT '#4CAF50'
        );

        CREATE TABLE IF NOT EXISTS preset_cards (
            id              INTEGER PRIMARY KEY,
            preset_deck_id  INTEGER NOT NULL REFERENCES preset_decks(id),
            front           TEXT NOT NULL,
            back            TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS picture_book_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL UNIQUE,
            book_count  INTEGER DEFAULT 0,
            accuracy    REAL DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        );
    """)

    # Add last_checkin column to decks if not exists (must be before usage below)
    try:
        conn.execute("ALTER TABLE decks ADD COLUMN last_checkin TEXT DEFAULT NULL")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # Create default "vocabulary book" deck if not exists
    cur = conn.execute("SELECT id FROM decks WHERE is_system = 1")
    if cur.fetchone() is None:
        conn.execute(
            "INSERT INTO decks (name, description, color, is_system) VALUES (?, ?, ?, 1)",
            ('生词本', '查词自动收集的单词', '#FF9800'),
        )
    conn.commit()

    # Create "daily vocabulary" deck if not exists (is_system = 2)
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    cur = conn.execute("SELECT id, last_checkin FROM decks WHERE is_system = 2")
    daily_row = cur.fetchone()
    if daily_row is None:
        conn.execute(
            "INSERT INTO decks (name, description, color, is_system, last_checkin) VALUES (?, ?, ?, 2, ?)",
            ('当日生词本', '今日查词集中复习', '#E91E63', today),
        )
    elif daily_row['last_checkin'] != today:
        # 新的一天: 清空当日生词本所有卡片
        conn.execute("DELETE FROM cards WHERE deck_id = ?", (daily_row['id'],))
        conn.execute("UPDATE decks SET last_checkin = ? WHERE id = ?", (today, daily_row['id']))
    conn.commit()

    # Add preset_id column to decks if not exists
    try:
        conn.execute("ALTER TABLE decks ADD COLUMN preset_id INTEGER DEFAULT NULL")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # Add daily_new_limit column to decks if not exists
    try:
        conn.execute("ALTER TABLE decks ADD COLUMN daily_new_limit INTEGER DEFAULT 20")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # Load preset data from CSV files (only if preset_decks is empty)
    _load_presets(conn)


def backup_db():
    """备份数据库到公共目录"""
    global _connection
    try:
        if _connection:
            _connection.commit()
            _connection.close()
            _connection = None
        db_path = get_db_path()
        backup_path = get_backup_db_path()
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
    except (PermissionError, OSError):
        # 没有存储权限，跳过备份
        if _connection is None:
            _connection = sqlite3.connect(get_db_path())
            _connection.row_factory = sqlite3.Row
            _connection.execute("PRAGMA foreign_keys = ON")


def do_restore_backup():
    """手动恢复备份，返回 (成功?, 消息)"""
    global _connection
    try:
        backup_path = get_backup_db_path()
        if not os.path.exists(backup_path):
            return False, '没有找到备份数据'
        db_path = get_db_path()
        if _connection:
            _connection.commit()
            _connection.close()
            _connection = None
        shutil.copy2(backup_path, db_path)
        _connection = sqlite3.connect(db_path)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA foreign_keys = ON")
        return True, '恢复成功!\n请点击"退出"重新打开应用'
    except (PermissionError, OSError):
        if _connection is None:
            _connection = sqlite3.connect(get_db_path())
            _connection.row_factory = sqlite3.Row
            _connection.execute("PRAGMA foreign_keys = ON")
        return False, '恢复失败\n请在弹出的设置页中授予权限后再次点击恢复'


def _load_presets(conn):
    """从CSV文件加载预设牌组数据（每次启动刷新preset表）"""
    conn.execute("DELETE FROM preset_cards")
    conn.execute("DELETE FROM preset_decks")

    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    if not os.path.isdir(data_dir):
        return

    # 预设牌组元信息: (filename, name, description, color)
    presets = [
        ('primary_poems.csv', '小学生必背古诗', '小学课标必背75+80首古诗词', '#E91E63'),
        ('toefl_junior.csv', '小托福词汇', 'TOEFL Junior 核心词汇', '#3F51B5'),
        ('shanghai_zhongkao.csv', '上海中考词汇', '上海中考英语核心词汇', '#009688'),
        ('shanghai_gaokao.csv', '上海高考词汇', '上海高考英语核心词汇', '#FF5722'),
        ('ielts.csv', '雅思词汇', 'IELTS雅思核心词汇', '#673AB7'),
        ('middle_poems.csv', '初中必备古诗', '初中课标必背古诗词', '#F44336'),
    ]

    for idx, (filename, name, desc, color) in enumerate(presets, 1):
        csv_path = os.path.join(data_dir, filename)
        if not os.path.exists(csv_path):
            continue

        conn.execute(
            "INSERT INTO preset_decks (id, name, description, color) VALUES (?, ?, ?, ?)",
            (idx, name, desc, color),
        )

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            card_id = (idx - 1) * 10000 + 1
            for row in reader:
                front = row.get('front', '').strip()
                back = row.get('back', '').strip()
                if front and back:
                    conn.execute(
                        "INSERT INTO preset_cards (id, preset_deck_id, front, back) VALUES (?, ?, ?, ?)",
                        (card_id, idx, front, back),
                    )
                    card_id += 1

    conn.commit()
