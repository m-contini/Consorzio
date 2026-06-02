import os
from pathlib import Path

# Verifica se siamo in ambiente cloud
IS_CLOUD = os.getenv("HEADLESS") == "true"
BUCKET_NAME = "consorzio-data"
REMOTE_DB_BLOB = "menu.duckdb"

# URL del menu online
URL = "https://consorziobirre.com/menu-consorzio-pub/"

# Cartella base per i dati (può essere sovrascritta da ENV)
DATA_DIR = Path(os.getenv("DATA_PATH", Path(__file__).parent.parent))

# File contenente menù aggiornato (JSON)
MENU_JSON = DATA_DIR / "menu_updated.json"

# DB contenente cronologia del menù
DB_PATH = DATA_DIR / "menu.duckdb"
