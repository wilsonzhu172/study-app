import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from studyapp.features.dictionary.lookup import lookup_offline, lookup_online, _clean_translation
from studyapp.features.dictionary.models import WordEntry


def test_clean_translation():
    assert _clean_translation('') == ''
    assert _clean_translation('n. apple') == 'n. apple'
    assert _clean_translation('n. apple\nv. apply') == 'n. apple; v. apply'


def test_lookup_offline_no_db():
    """When ECDICT db doesn't exist, returns None."""
    result = lookup_offline('apple')
    assert result is None


def test_lookup_online_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{
        'word': 'hello',
        'phonetic': '/həˈloʊ/',
        'phonetics': [
            {'text': '/həˈloʊ/', 'audio': '//example.com/hello.mp3'}
        ],
        'meanings': [{
            'partOfSpeech': 'exclamation',
            'definitions': [
                {'definition': 'used as a greeting', 'example': 'hello there!'}
            ]
        }]
    }]

    with patch('studyapp.features.dictionary.lookup.http_requests.get', return_value=mock_response):
        result = lookup_online('hello')
        assert result is not None
        assert result.word == 'hello'
        assert result.phonetic == '/həˈloʊ/'
        assert 'greeting' in result.definition
        assert result.example == 'hello there!'
        assert 'example.com' in result.audio_url


def test_lookup_online_not_found():
    mock_response = MagicMock()
    mock_response.status_code = 404
    with patch('studyapp.features.dictionary.lookup.http_requests.get', return_value=mock_response):
        result = lookup_online('xyz123')
        assert result is None


def test_lookup_online_timeout():
    import requests
    with patch('studyapp.features.dictionary.lookup.http_requests.get', side_effect=requests.Timeout):
        result = lookup_online('hello')
        assert result is None
