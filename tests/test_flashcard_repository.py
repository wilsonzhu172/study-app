import os
import sys
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from studyapp.core.database import init_db, get_connection, close_connection
from studyapp.features.flashcards.repository import (
    create_deck, get_decks, get_deck, update_deck, delete_deck,
    create_card, get_cards_by_deck, get_card, update_card, delete_card,
    get_card_count, get_learned_count, add_study_record, get_vocab_deck_id,
)
from studyapp.features.flashcards.models import Deck, Card


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(
        'studyapp.core.paths.get_data_dir', lambda: str(tmp_path)
    )
    close_connection()
    init_db()
    yield
    close_connection()


def test_default_vocab_deck():
    deck_id = get_vocab_deck_id()
    assert deck_id is not None
    deck = get_deck(deck_id)
    assert deck.is_system == 1
    assert deck.name == '生词本'


def test_create_and_get_deck():
    did = create_deck('Math', 'Math cards', '#2196F3')
    deck = get_deck(did)
    assert deck.name == 'Math'
    assert deck.description == 'Math cards'
    assert deck.color == '#2196F3'
    assert deck.is_system == 0


def test_update_deck():
    did = create_deck('Old')
    update_deck(did, name='New', color='#F00')
    deck = get_deck(did)
    assert deck.name == 'New'
    assert deck.color == '#F00'


def test_delete_deck():
    did = create_deck('Tmp')
    delete_deck(did)
    assert get_deck(did) is None


def test_cannot_delete_system_deck():
    did = get_vocab_deck_id()
    delete_deck(did)
    assert get_deck(did) is not None


def test_get_decks():
    create_deck('A')
    create_deck('B')
    decks = get_decks()
    names = [d.name for d in decks]
    assert '生词本' in names
    assert 'A' in names
    assert 'B' in names


def test_create_and_get_cards():
    did = create_deck('Test')
    cid = create_card(did, 'front text', 'back text')
    card = get_card(cid)
    assert card.front == 'front text'
    assert card.back == 'back text'
    assert card.deck_id == did


def test_update_card():
    did = create_deck('Test')
    cid = create_card(did, 'old front', 'old back')
    update_card(cid, front='new front', back='new back')
    card = get_card(cid)
    assert card.front == 'new front'


def test_delete_card():
    did = create_deck('Test')
    cid = create_card(did, 'f', 'b')
    delete_card(cid)
    assert get_card(cid) is None


def test_card_count():
    did = create_deck('Test')
    create_card(did, 'f1', 'b1')
    create_card(did, 'f2', 'b2')
    assert get_card_count(did) == 2


def test_study_records():
    did = create_deck('Test')
    cid = create_card(did, 'f', 'b')
    add_study_record(cid, 2)
    add_study_record(cid, 3)
    assert get_learned_count(did) == 1


def test_learned_count_filters_grade():
    did = create_deck('Test')
    c1 = create_card(did, 'f1', 'b1')
    c2 = create_card(did, 'f2', 'b2')
    add_study_record(c1, 0)
    add_study_record(c2, 2)
    assert get_learned_count(did) == 1
