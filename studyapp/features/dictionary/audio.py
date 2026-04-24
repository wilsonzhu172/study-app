import os
import tempfile
import threading
import logging

import requests as http_requests

logger = logging.getLogger(__name__)

try:
    import pygame
    pygame.mixer.init()
    _HAS_PYGAME = True
except Exception:
    _HAS_PYGAME = False


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
                on_stop()
            return

        ext = '.mp3'
        if url.endswith('.ogg'):
            ext = '.ogg'
        tmp = os.path.join(tempfile.gettempdir(), f'_dict_audio{ext}')
        with open(tmp, 'wb') as f:
            f.write(resp.content)

        if _HAS_PYGAME:
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            if on_stop:
                on_stop()
        else:
            logger.warning('No audio playback available (pygame not installed)')
            if on_stop:
                on_stop()
    except Exception as e:
        logger.error('Audio playback error: %s', e)
        if on_stop:
            on_stop()
