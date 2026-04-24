"""Buildozer entry point - imports and runs the StudyApp."""
import os

if os.environ.get('ANDROID_ROOT'):
    os.environ["KIVY_NO_FILELOG"] = "1"

from studyapp.main import StudyApp

StudyApp().run()
