"""
Punto di ingresso principale dell'applicazione.
Gestisce il flusso di scraping, pulizia, aggiornamento del database,
invio notifiche e avvio dell'interfaccia utente testuale (TUI).
"""

import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

import core.alert as alert
import core.cloud as cloud
import core.ingestion as ingestion
import core.tui as tui
from core.colors import *
from core.const import DB_PATH, IS_CLOUD, MENU_JSON

now = datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%dT%H-%M-%S")

# Percorso per salvare lo storico del file JSON grezzo con timestamp
history_dir = MENU_JSON.parent / "history"
db_path = DB_PATH


def test_env(required_vars: list[str] | tuple[str, ...] | None = None) -> bool:
    # Serve solo in locale, su cloud fallisce in silenzio
    load_dotenv()
    if required_vars is None:
        return True
    return all(os.getenv(v) is not None for v in required_vars)


# Esce immediatamente se non riesce a caricare tutte le variabili d'ambiente
required_vars = ("API_KEY", "SENDER", "RECIPIENT", "HEADLESS")
if not test_env(required_vars):
    print(
        f"🚨 {red('[FATAL]')}: Configurazione incompleta, variabili non trovate in '.env' "
        f"({', '.join([v for v in required_vars if os.getenv(v) is None])})"
    )
    sys.exit(1)


def run_pipeline() -> None:
    """
    Funzione principale che orchestra le fasi di data ingestion e l'interfaccia utente.
    """

    # Se siamo in locale, scarichiamo il DB aggiornato
    # prima di qualsiasi operazione.
    # Se siamo in cloud, ritorna None
    cloud.download_cloud_db(DB_PATH)

    # Percorso del JSON
    if IS_CLOUD:
        menu_json = history_dir / (now + "_" + MENU_JSON.name)
    else:
        menu_json = MENU_JSON

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

        # Se siamo in locale, carichiamo le modifiche sul bucket
        # Se siamo in cloud, ritorna None senza fare nulla
        cloud.upload_cloud_db(DB_PATH)

        # TEXTUAL USER INTERFACE (solo in locale)
        if not IS_CLOUD:
            print(cyan("\nLookup:"))
            _tui = tui.InteractiveMenu(cln.df)
            _tui.run()
    except Exception as e:
        print(f"🚨 {red('[FATAL]')}: {e}", file=sys.stderr)
        _alert.send_email(_alert.build_fatal_alert(e))
        sys.exit(1)


def main() -> None:
    start_time = time.perf_counter()
    print("✈️ [START] Avvio pipeline ETL")
    run_pipeline()
    end_time = time.perf_counter()
    print(
        f"🕰️ [END] Pipeline completata con successo in {end_time - start_time:.2f} secondi."
    )


if __name__ == "__main__":
    main()
