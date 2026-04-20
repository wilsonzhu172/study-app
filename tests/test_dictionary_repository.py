import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from studyapp.core.database import init_db, get_connection, close_connection
from studyapp.features.dictionary.repository import save_or_update_vocab, get_vocab, get_all_vocab
from studyapp.features.dictionary.models import WordEntry


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(
        'studyapp.core.paths.get_data_dir', lambda: str(tmp_path)
    )
    close_connection()
    init_db()
    yield
    close_connection()


def test_save_and_get_vocab():
    entry = WordEntry(
        word='apple', phonetic='/ˈæpl/', translation='n. 苹果',
        definition='a fruit', example='I eat an apple.',
    )
    save_or_update_vocab(entry)
    result = get_vocab('apple')
    assert result is not None
    assert result.word == 'apple'
    assert result.phonetic == '/ˈæpl/'
    assert result.translation == 'n. 苹果'


def test_update_increments_lookup_count():
    entry = WordEntry(word='apple', translation='n. 苹果')
    save_or_update_vocab(entry)
    save_or_update_vocab(entry)
    r = get_connection().execute(
        "SELECT lookup_count FROM vocabulary WHERE word = 'apple'"
    ).fetchone()
    assert r['lookup_count'] == 2


def test_get_all_vocab():
    save_or_update_vocab(WordEntry(word='apple', translation='苹果'))
    save_or_update_vocab(WordEntry(word='banana', translation='香蕉'))
    words = get_all_vocab()
    assert len(words) == 2
    assert {w.word for w in words} == {'apple', 'banana'}


def test_get_nonexistent():
    assert get_vocab('xyz123') is None
