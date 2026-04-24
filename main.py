"""Buildozer entry point - imports and runs the StudyApp."""
import os
import sys
import traceback

if os.environ.get('ANDROID_ROOT'):
    os.environ["KIVY_NO_FILELOG"] = "1"

CRASH_LOG = '/sdcard/Download/studyapp_crash.log'

try:
    from studyapp.main import StudyApp
    StudyApp().run()
except Exception as e:
    tb = traceback.format_exc()
    try:
        with open(CRASH_LOG, 'w', encoding='utf-8') as f:
            f.write(tb)
    except Exception:
        pass
    print(f"CRASH: {e}\n{tb}", file=sys.stderr)
    raise
