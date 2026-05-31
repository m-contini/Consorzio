from pathlib import Path
import duckdb
import pandas as pd

from .colors import *


def hashed_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera un hash dalle colonne chiave (Macro-categoria, Categoria, Articolo, Size)
    e riordina il DataFrame posizionando 'item_id' in testa e 'Prezzo' in coda.
    """
    df = df.reset_index()

    cols_to_hash = ["Macro-categoria", "Categoria", "Articolo", "Size"]
    df["item_id"] = pd.util.hash_pandas_object(df[cols_to_hash], index=False)

    remaining_cols = df.columns.drop(["item_id", "Prezzo"])
    return df[["item_id", *remaining_cols, "Prezzo"]]


class Database:
    """Gestisce la connessione e le operazioni sul database DuckDB."""

    def __init__(self, db_path: Path) -> None:
        # Percorso al file .duckdb
        self.db_path: Path = db_path
        # Legge menu, se esistente, altrimenti DataFrame vuoto
        self.df: pd.DataFrame = self.read_sql()
        # Flag che segnala se ci sono state variazioni nel menu
        self._is_updated: bool = False

    @property
    def empty(self) -> bool:
        return self.df.empty

    @property
    def is_updated(self) -> bool:
        return self._is_updated

    def read_sql(self) -> pd.DataFrame:
        """Legge il DataFrame 'menu' dal database DuckDB."""
        try:
            with duckdb.connect(self.db_path) as conn:
                df = conn.execute("SELECT * FROM menu").df()
                return df
        except duckdb.CatalogException:
            print(
                f"\n⚠️ {magenta('[DB]')} Database locale non trovato in '{yellow(self.db_path)}'"
            )
            return pd.DataFrame()

    def create_menu(self) -> None:
        """Crea la tabella 'menu' nel database se non esiste."""
        if self.empty:
            print(f"\n🎊 {yellow('[DB]')} Creating table 'menu'.")
        with duckdb.connect(self.db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS menu (
                    item_id           UBIGINT,
                    "Macro-categoria" TEXT,
                    Categoria         TEXT,
                    Articolo          TEXT,
                    Dettagli          TEXT,
                    Size              TEXT,
                    Prezzo            FLOAT,

                    isActive          BOOLEAN DEFAULT TRUE,
                    startDate         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    endDate           TIMESTAMP DEFAULT NULL,

                    PRIMARY KEY (item_id, startDate)
                )"""
            )

    def to_sql(self, new_df: pd.DataFrame) -> None:
        """Applica le modifiche al database usando la logica SCD Type 2."""
        with duckdb.connect(self.db_path) as conn:
            # Registra in memoria `menu_new` (t1) in arrivo dallo scraping
            # mentre `menu` (t2) è presente nel DB
            conn.register("menu_new", new_df)

            # Se è il primissimo inserimento (DB nuovo)
            if self.empty:
                print("Populating empty database...")
                conn.execute("""
                    INSERT INTO menu
                        SELECT
                            *,
                            TRUE,              -- isActive
                            CURRENT_TIMESTAMP, -- startDate
                            NULL               -- endDate
                        FROM menu_new
                    ON CONFLICT DO NOTHING""")
                return

            # --------------------
            # SCD Type 2
            # --------------------
            print(f"\n🔃 {yellow('[DB]')} Updating database (SCD Type 2)...")
            conn.execute("BEGIN TRANSACTION")
            try:
                # ---------------------------------------- #
                # 1. Disattivazione record obsoleti o con prezzo cambiato
                # ---------------------------------------- #
                cursor_update = conn.execute("""
                    UPDATE menu
                    SET isActive = FALSE, endDate = CURRENT_TIMESTAMP
                    WHERE isActive = TRUE
                    AND (
                        -- CASO A: Il prodotto è stato rimosso dal menu
                        NOT EXISTS (
                            SELECT 1
                            FROM menu_new t1
                            WHERE t1.item_id = menu.item_id
                        )
                        OR
                        -- CASO B: Il prodotto esiste ancora, ma il prezzo è cambiato
                        EXISTS (
                            SELECT 1
                            FROM menu_new t1
                            WHERE t1.item_id = menu.item_id
                                AND t1.Prezzo != menu.Prezzo
                        )
                    )
                    RETURNING *;
                """)
                # Salva le righe rimosse/modificate in un attributo
                # per restituirle e inviarle via `Notification`
                self.deactivated_rows = cursor_update.df()
                deactivated_rows = len(self.deactivated_rows)

                # ---------------------------------------- #
                # 2. Inserimento nuovi record o record con prezzo aggiornato
                # ---------------------------------------- #
                cursor_insert = conn.execute("""
                    INSERT INTO menu (
                        item_id, "Macro-categoria", Categoria, Articolo,
                        Dettagli, Size, Prezzo, isActive, startDate, endDate
                    )
                    SELECT
                        t1.item_id, t1."Macro-categoria", t1.Categoria, t1.Articolo,
                        t1.Dettagli, t1.Size, t1.Prezzo,
                        TRUE,              -- isActive
                        CURRENT_TIMESTAMP, -- startDate
                        NULL               -- endDate
                        FROM menu_new t1
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM menu t2
                        WHERE t2.item_id = t1.item_id
                            AND t2.Prezzo = t1.Prezzo
                            AND t2.isActive = TRUE
                    )
                    ON CONFLICT DO NOTHING
                    RETURNING *;
                """)
                # Salva le righe nuove in un attributo
                # per restituirle e inviarle via `Notification`
                self.inserted_rows = cursor_insert.df()
                inserted_rows = len(self.inserted_rows)

                conn.execute("COMMIT")

                # -------------------- #
                # Report modifiche
                # -------------------- #
                if deactivated_rows > 0 or inserted_rows > 0:
                    print(f"\n🔄 {yellow('[DB]')} Update completed:")
                    self._is_updated = True
                    if inserted_rows > 0:
                        print(f"  ➕ {inserted_rows} new articles or updated prices.")
                    if deactivated_rows > 0:
                        print(f"  🍂 {deactivated_rows} old records archived.")
                else:
                    print(f"\n✨ {green('[DB]')} No changes detected.")
                    self._is_updated = False

            except Exception as e:
                conn.execute("ROLLBACK")
                raise e
