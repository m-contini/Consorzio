import pytest
from unittest.mock import MagicMock, patch

import pandas as pd
from core.cleaner import Cleaner


# fixture per creazione dell'oggetto Cleaner pronto all'uso
@pytest.fixture
def cleaner_obj():
    # Si usa `patch.object` per catturare il metodo `load_json` della classe Cleaner
    # ogni volta che viene chiamata, ritorna un dizionario vuoto {}.
    # Così `__init__` non tenterà mai di leggere un file reale.
    with patch.object(Cleaner, "load_json", return_value={}):
        mock = MagicMock()
        c = Cleaner(input_file=mock)

        # Qui si forza l'inizializzazione del dataframe in modo che sia pronto per i test
        c.df = pd.DataFrame(
            columns=["Macro-categoria", "Categoria", "Articolo", "Prezzo"]
        )

    return c


# Gli argomenti devono sempre chiamarsi `cleaner_obj` come la funzione definita sopra
def test_price_normalization(cleaner_obj: Cleaner) -> None:
    """
    Testa che il metodo `_price_to_float` gestisca formati diversi
    """

    cleaner_obj.df = pd.DataFrame(
        {"Prezzo": ["€ 10,50 ", "€20,00", "30", "€ 40.99", "50.12 €"]}
    )
    expected_prices: list[float] = [10.50, 20.00, 30.00, 40.99, 50.12]

    # Applicazione del metodo
    cleaner_obj._price_to_float()  # pyright: ignore[reportPrivateUsage]

    # Verifica risultati
    assert cleaner_obj.df["Prezzo"].tolist() == expected_prices
    assert cleaner_obj.df["Prezzo"].dtype == "float64"
    pd.testing.assert_series_equal(
        cleaner_obj.df["Prezzo"], pd.Series(expected_prices, name="Prezzo")
    )


def test_invalid_price_handling(cleaner_obj: Cleaner) -> None:
    """
    Testa che un valore non numerico causi un errore o un NaN
    """

    cleaner_obj.df = pd.DataFrame({"Prezzo": ["Prezzo indeterminato"]})

    # Applicazione del metodo
    cleaner_obj._price_to_float()  # pyright: ignore[reportPrivateUsage]

    # Verifica risultati
    # Internamente `pd.to_numeric` metta NaN per valori non pulibili
    assert pd.isna(cleaner_obj.df["Prezzo"].iloc[0])
    assert cleaner_obj.df["Prezzo"].dtype == "float64"
