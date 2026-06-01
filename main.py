"""
Punto di ingresso principale dell'applicazione.
Gestisce il flusso di scraping, pulizia, aggiornamento del database,
invio notifiche e avvio dell'interfaccia utente testuale (TUI).
"""

import os
from datetime import datetime
import sys
from zoneinfo import ZoneInfo

import core.alert as alert
import core.ingestion as ingestion
import core.tui as tui
from core.colors import *
from core.const import DB_PATH, MENU_JSON

now = datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%dT%H-%M-%S")

# Percorso per salvare lo storico del file JSON grezzo con timestamp
history_dir = MENU_JSON.parent / "history"
menu_json = history_dir / (now + "_" + MENU_JSON.name)
db_path = DB_PATH


def main() -> None:
    """
    Funzione principale che orchestra le fasi di data ingestion e l'interfaccia utente.
    """

    # Istanzia alert per poter mandare notifica se necessario
    _alert = alert.Notification(timestamp=now, reciprocal=True)

    try:
        # Assicura che le cartelle esistano (necessario per i volumi montati)
        menu_json.parent.mkdir(parents=True, exist_ok=True)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # SCRAPING + SAVE + INIT + CLEANING + UPDATE
        print(cyan("\nScraping menu..."))
        cln, db = ingestion.data_ingestion(json_path=menu_json, db_path=db_path)

        # PREVIEW
        print(cyan("\nPreview:"))
        print(cln.preview(["Dettagli", "Size", "Prezzo"], 5))

        # ALERT
        if db.is_updated:
            print(f"{yellow('[EMAIL]')} 📩 Sending notification via e-mail...")
            msg = _alert.build_msg(db.deactivated_rows, db.inserted_rows)
            _alert.send_email(msg)

        # TEXTUAL USER INTERFACE (Solo se non in modalità headless)
        if os.getenv("HEADLESS") != "true":
            print(cyan("\nLookup:"))
            _tui = tui.InteractiveMenu(cln.df)
            _tui.run()
    except Exception as e:
        print(f"🚨 FATAL ERROR riscontrato nella pipeline: {e}", file=sys.stderr)
        _alert.send_email(_alert.build_fatal_alert(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
