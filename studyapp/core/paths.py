import os


def get_data_dir() -> str:
    try:
        from android.storage import app_storage_path
        return app_storage_path()
    except ImportError:
        return os.path.join(os.path.dirname(__file__), '..', '..', 'data')


def get_db_path() -> str:
    d = get_data_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'studyapp.db')


def get_dict_db_path() -> str:
    base = os.path.dirname(__file__)
    return os.path.join(base, '..', 'assets', 'dict', 'stardict.db')
