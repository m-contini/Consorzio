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

import duckdb
from dotenv import load_dotenv

from core import (
    DB_PATH,
    HEADLESS,
    MENU_JSON,
    alert,
    cyan,
    ingestion,
    red,
    tui,
    yellow,
)

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

    # Percorso del JSON
    if HEADLESS:
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
        else:
            print(
                f"{yellow('[EMAIL]')} ✨  Sospensione: nessuna variazione rilevata nel menu."
            )

        # TEXTUAL USER INTERFACE (solo in locale)
        if not HEADLESS:
            print(cyan("\nLookup:"))
            _tui = tui.InteractiveMenu(cln.df)
            _tui.run()
    except (
        PermissionError,
        KeyError,
        ValueError,
        TypeError,
        duckdb.IOException,
        duckdb.Error,
    ) as e:
        print(f"🚨 {red('[FATAL]')}: {e}", file=sys.stderr)
        _alert.send_email(_alert.build_fatal_alert(e))
        sys.exit(1)


def main() -> None:

    print("Data esecuzione: ", now)

    start_time = time.perf_counter()
    print("✈️ [START] Avvio pipeline ETL")
    run_pipeline()
    end_time = time.perf_counter()
    print(
        f"🕰️ [END] Pipeline completata con successo in {end_time - start_time:.2f} secondi."
    )


if __name__ == "__main__":
    main()
