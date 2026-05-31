from typing import Any

import pytest

import pandas as pd
import duckdb
from pathlib import Path

from core.database import Database, hashed_df


@pytest.fixture
def db(tmp_path: Path) -> Database:
    # Percorso temporaneo che viene rimosso automaticamente da pytest
    temp_db_path = tmp_path / "menu_test.duckdb"

    # Inizializza in RAM un'istanza di Database
    # così da non creare file sul disco
    _db = Database(temp_db_path)
    _db.create_menu()
    return _db


def test_hashed_df() -> None:
    # Verifica che hashed_df generi id univoci basati sulle colonne chiave
    # e che generi lo stesso id per righe identiche

    # Record di test
    raw_data: dict[str, Any] = {
        "Macro-categoria": ["BEVI BENE", "BEVI BENE"],
        "Categoria": ["BIRRE", "BIRRE"],
        "Articolo": ["Pilsner", "Pilsner"],
        "Dettagli": ["Chiara 5%", "Versione Speciale"],
        "Size": ["0.40 cl", "0.40 cl"],
        "Prezzo": [6.00, 7.50],
    }
    df = pd.DataFrame(raw_data).set_index(["Macro-categoria", "Categoria", "Articolo"])
    processed_df = hashed_df(df)

    # 1) L'id deve essere identico per i due articoli poiché hanno le colonne chiave in comune
    # Dettagli e prezzo non devono influenzare item_id
    assert processed_df["item_id"].iloc[0] == processed_df["item_id"].iloc[1]

    # 2) Ordine corretto delle colonne di output
    assert list(processed_df.columns) == [
        "item_id",
        "Macro-categoria",
        "Categoria",
        "Articolo",
        "Dettagli",
        "Size",
        "Prezzo",
    ]

    # 3) item_id dev'essere intero a 64 bit non firmato (UBIGINT su DuckDB)
    assert pd.api.types.is_integer_dtype(processed_df["item_id"])


def test_scd_type_2_pipeline(db: Database) -> None:
    """
    Testa il comportamento della pipeline del database simulandone un ciclo di vita SCD Type 2:
    """

    # 1. Popolamento iniziale
    first_data = pd.DataFrame(
        {
            "item_id": [1234, 5678],
            "Macro-categoria": ["BEVI BENE", "MANGIA BENE"],
            "Categoria": ["GIN TONIC MORBIDI 7,5CL", "NACHOS"],
            "Articolo": ["ETSU GIN ORIGINAL GIAPPONE", "Nachos TIPICOS"],
            "Dettagli": [
                "Gin fresco e rotondo",
                "con Formaggella artigianale fusa (allergeni: 7)",
            ],
            "Size": ["N/A", "N/A"],
            "Prezzo": [13.00, 11.50],
        }
    )

    db.to_sql(first_data)

    # Verifica che il database si sia popolato
    with duckdb.connect(db.db_path) as conn:
        res = conn.sql("""
            SELECT
                isActive,
                startDate,
                endDate,
                Prezzo
            FROM menu
            ORDER BY item_id;
        """).df()
        assert not res.empty
        assert len(res) == 2

        assert bool(res["isActive"][0]) is True
        assert res["Prezzo"][0] == 13.0
        assert pd.isna(res["endDate"].iloc[0])

        assert bool(res["isActive"][1]) is True
        assert res["Prezzo"][1] == 11.5
        assert pd.isna(res["endDate"].iloc[1])

    # 2. Nessuna variazione nel menù
    db.df = db.read_sql()
    db.to_sql(first_data)
    assert db.is_updated is False

    # 3. Aumento del prezzo del gin
    updated_data = first_data.copy()
    updated_data.loc[0, "Prezzo"] = 14.0

    # 4. Rimozione dei nachos
    updated_data = updated_data.drop(index=1)

    """
    1 Gin Vecchio: 13.00 € (Disattivato)
    2 Nachos Vecchi: 11.50 € (Disattivato perché rimosso)
    3 Gin Nuovo: 14.00 € (Attivo)
    """
    db.df = db.read_sql()
    db.to_sql(updated_data)

    # Verifica che l'aggiornamento sia stato inviato
    assert db.is_updated is True
    assert len(db.deactivated_rows) == 2
    assert len(db.inserted_rows) == 1

    # Verifica che l'aggiornamento sia stato recepito
    with duckdb.connect(db.db_path) as conn:
        # Filtro esplicito per item_id del Gin, ordinando per Prezzo.
        # db_df conterrà solo i due record del gin:
        # riga 0 -> 13.0€ (vecchio), riga 1 -> 14.0€ (nuovo).
        db_df = conn.execute("""
            SELECT
                item_id,
                isActive,
                Prezzo,
                endDate
            FROM menu
            WHERE item_id = 1234
            ORDER BY Prezzo;
        """).df()

        # Per lo stesso gin devono esistere 2 records
        assert len(db_df) == 2

        # Il vecchio record deve risultare disattivato
        assert bool(db_df.iloc[0]["isActive"]) is False
        assert db_df.iloc[0]["Prezzo"] == 13.0
        assert pd.notna(db_df.iloc[0]["endDate"])

        # Il nuovo record deve essere attivato
        assert bool(db_df.iloc[1]["isActive"]) is True
        assert db_df.iloc[1]["Prezzo"] == 14.00
        assert pd.isna(db_df.iloc[1]["endDate"])

    # Verifica che anche i nachos (item_id=5678) siano stati spenti
    with duckdb.connect(db.db_path) as conn:
        nachos_df = conn.execute("""
            SELECT
                isActive,
                endDate
            FROM menu
            WHERE item_id = 5678;
        """).df()
        assert len(nachos_df) == 1
        assert bool(nachos_df.iloc[0]["isActive"]) is False
        assert pd.notna(nachos_df.iloc[0]["endDate"])
