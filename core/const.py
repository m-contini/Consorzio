from pathlib import Path

# URL del menu online
URL = 'https://consorziobirre.com/menu-consorzio-pub/'

# File contenente menù aggiornato (JSON)
MENU_JSON = Path(__file__).parent.parent / 'menu_updated.json'

# DB contenente cronologia del menù
DB_PATH = Path(__file__).parent.parent / 'menu.duckdb'
