import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER_DATA_DIR = "/data"
LOCAL_DATA_DIR = os.path.join(PROJECT_ROOT, "local_data")

STORAGE_DIR = RENDER_DATA_DIR if os.path.exists(RENDER_DATA_DIR) else LOCAL_DATA_DIR
os.makedirs(STORAGE_DIR, exist_ok=True)


def storage_path(filename: str) -> str:
    return os.path.join(STORAGE_DIR, filename)
