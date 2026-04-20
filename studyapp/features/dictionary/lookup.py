import sqlite3
import os
import threading
import requests as http_requests

from .models import WordEntry
from ..flashcards.repository import create_card, get_vocab_deck_id

_DICT_DB = None
_DICT_LOCK = threading.Lock()


def _get_dict_conn():
    global _DICT_DB
    if _DICT_DB is not None:
        return _DICT_DB
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'dict', 'stardict.db')
    db_path = os.path.normpath(db_path)
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _DICT_DB = conn
    return conn


def lookup_offline(word: str) -> WordEntry | None:
    """Look up word in local ECDICT database."""
    conn = _get_dict_conn()
    if conn is None:
        return None
    r = conn.execute(
        "SELECT word, phonetic, translation, definition FROM stardict WHERE word = ? COLLATE NOCASE",
        (word,),
    ).fetchone()
    if not r:
        return None
    return WordEntry(
        word=r['word'],
        phonetic=r['phonetic'] or '',
        translation=_clean_translation(r['translation']),
        definition=r['definition'] or '',
    )


def lookup_online(word: str) -> WordEntry | None:
    """Look up word via Free Dictionary API for examples and audio."""
    try:
        resp = http_requests.get(
            f'https://api.dictionaryapi.dev/api/v2/entries/en/{word}',
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()[0]

        # Get phonetic
        phonetic = data.get('phonetic', '')
        if not phonetic:
            for p in data.get('phonetics', []):
                if p.get('text'):
                    phonetic = p['text']
                    break

        # Get audio URL
        audio_url = ''
        for p in data.get('phonetics', []):
            if p.get('audio'):
                audio_url = p['audio']
                if audio_url.startswith('//'):
                    audio_url = 'https:' + audio_url
                break

        # Get first example sentence
        example = ''
        for meaning in data.get('meanings', []):
            for defn in meaning.get('definitions', []):
                if defn.get('example'):
                    example = defn['example']
                    break
            if example:
                break

        # Build translation from meanings (English definitions)
        parts = []
        for meaning in data.get('meanings', []):
            pos = meaning.get('partOfSpeech', '')
            for defn in meaning.get('definitions', [])[:2]:
                parts.append(f'{pos}: {defn["definition"]}')
        definition = '\n'.join(parts)

        return WordEntry(
            word=data['word'],
            phonetic=phonetic,
            definition=definition,
            example=example,
            audio_url=audio_url,
        )
    except Exception:
        return None


def lookup_word(word: str) -> WordEntry:
    """Combined lookup: offline first, then online for enrichment."""
    word = word.strip().lower()
    if not word:
        return WordEntry(word=word)

    entry = lookup_offline(word)

    # Enrich with online data
    online = lookup_online(word)
    if online:
        if entry is None:
            entry = online
        else:
            # Merge: keep offline translation, add online extras
            if online.phonetic and not entry.phonetic:
                entry.phonetic = online.phonetic
            if online.example and not entry.example:
                entry.example = online.example
            if online.audio_url and not entry.audio_url:
                entry.audio_url = online.audio_url

    if entry is None:
        entry = WordEntry(word=word)

    return entry


def _clean_translation(text):
    if not text:
        return ''
    # ECDICT translations are separated by \n
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return '; '.join(lines[:3])
