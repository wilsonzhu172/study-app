import os
import tempfile
import threading
import logging

import requests as http_requests
from kivy.core.audio import SoundLoader
from kivy.clock import Clock

logger = logging.getLogger(__name__)


def play_audio(url: str, on_stop=None):
    if not url:
        return
    threading.Thread(target=_download_and_play, args=(url, on_stop), daemon=True).start()


def _download_and_play(url: str, on_stop):
    try:
        resp = http_requests.get(url, timeout=10)
        if resp.status_code != 200:
            logger.warning('Audio download failed: status %d for %s', resp.status_code, url)
            if on_stop:
                Clock.schedule_once(lambda dt: on_stop())
            return
        ext = '.mp3'
        if url.endswith('.ogg'):
            ext = '.ogg'
        tmp = os.path.join(tempfile.gettempdir(), f'_dict_audio{ext}')
        with open(tmp, 'wb') as f:
            f.write(resp.content)
        sound = SoundLoader.load(tmp)
        if sound:
            if on_stop:
                sound.bind(on_stop=lambda s: Clock.schedule_once(lambda dt: on_stop()))
            sound.play()
        else:
            logger.warning('SoundLoader could not load %s', tmp)
            if on_stop:
                Clock.schedule_once(lambda dt: on_stop())
    except Exception as e:
        logger.error('Audio playback error: %s', e)
        if on_stop:
            Clock.schedule_once(lambda dt: on_stop())
