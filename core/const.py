import os
import sys
from pathlib import Path

DUCKDB_FNAME = "menu.duckdb"

# Verifica se siamo in modalità headless
HEADLESS = "--headless" in sys.argv
os.environ["HEADLESS"] = str(HEADLESS).lower()

# URL del menu online
URL = "https://consorziobirre.com/menu-consorzio-pub/"

# Cartella base per i dati (può essere sovrascritta da ENV)
DATA_DIR = Path(__file__).parent.parent

# File contenente menù aggiornato (JSON)
MENU_JSON = DATA_DIR / "menu_updated.json"

# DB contenente cronologia del menù
DB_PATH = DATA_DIR / "menu.duckdb"
