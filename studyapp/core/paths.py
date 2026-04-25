import os


def get_data_dir() -> str:
    try:
        from android.storage import app_storage_path
        return app_storage_path()
    except (ImportError, Exception):
        base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, '..', '..', 'data')


def get_db_path() -> str:
    d = get_data_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'studyapp.db')


def get_backup_dir() -> str:
    """返回公共备份目录 (/sdcard/Download/studyapp/)"""
    try:
        from android.storage import primary_external_storage_path
        ext = primary_external_storage_path()
    except (ImportError, Exception):
        ext = os.path.expanduser('~')
    d = os.path.join(ext, 'Download', 'studyapp')
    os.makedirs(d, exist_ok=True)
    return d


def get_backup_db_path() -> str:
    return os.path.join(get_backup_dir(), 'studyapp.db')


def get_dict_db_path() -> str:
    base = os.path.dirname(__file__)
    return os.path.join(base, '..', 'assets', 'dict', 'stardict.db')
