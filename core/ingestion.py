from .colors import *
from .const import URL, MENU_JSON
import core.scraper as scraper
import core.cleaner as cleaner
import core.database as database


def data_ingestion(
    json_path: Path, db_path: Path
) -> tuple[cleaner.Cleaner, database.Database]:
    """
    Esegue l'intero processo di acquisizione dati: scraping dal sito web,
    salvataggio in JSON, pulizia dei dati, esportazione in Excel e
    aggiornamento del database DuckDB con logica SCD Type 2.

    Args:
        json_path (Path): Percorso dove salvare il file JSON grezzo (storico).
        db_path (Path): Percorso del database DuckDB.

    Returns:
        tuple[cleaner.Cleaner, database.Database]: Oggetti Cleaner (con DataFrame aggiornato) e Database.
    """

    # Inizializzazione moduli
    _scraper = scraper.Scraper(output_file=json_path)
    _cleaner = cleaner.Cleaner(input_file=json_path)
    _database = database.Database(db_path=db_path)

    # SCRAPING
    print(f"📖 {yellow('[JSON]')} Reading menu from '{cyan(URL)}'...")
    _cleaner.menu = _scraper.parse_menu(URL)

    # SAVE
    _scraper.save_json(_cleaner.menu)
    print(f"\n{green('[JSON]')} Output written to '{yellow(_scraper.output_file)}'")
    print(f"{green('[JSON]')} Output written to '{yellow(MENU_JSON)}'")

    # INIT
    _database.create_menu()

    # CLEANING
    _cleaner.clean()
    _cleaner.to_xlsx()
    print(
        f"\n{green('[XLSX]')} Output written to '{yellow(_cleaner.input_file.with_suffix('.xlsx'))}'"
    )

    # UPDATE
    _database.to_sql(database.hashed_df(_cleaner.df))
    print(
        f"\n{green('[DB]')} Output written in local database '{yellow(_database.db_path)}'"
    )

    print(cyan("\nReading menu from database..."))

    _cleaner.df = _database.read_sql()
    _cleaner.df = _cleaner.df.drop(
        columns=["item_id", "isActive", "startDate", "endDate"]
    ).set_index(["Macro-categoria", "Categoria", "Articolo"])

    return _cleaner, _database
