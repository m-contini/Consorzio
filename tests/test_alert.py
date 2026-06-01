from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from core.alert import Notification


@pytest.fixture
def sample_dfs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Crea due DataFrame per simulare allegati alla notifica:
    - uno con dati;
    - uno vuoto.

    Serve per testare la logica di skip (se vuoto) in `_build_msg`
    """
    df_deactivated_rows = pd.DataFrame(
        {"Articolo": ["BIANCONIGLIO"], "Size": ["piccola"], "Prezzo": [5.5]}
    )
    df_inserted_rows = pd.DataFrame()

    return df_deactivated_rows, df_inserted_rows


"""
In Python, con i decoratori in pila, gli argomenti che vengono passati alla funzione
di test seguono un ordine dal basso verso l'alto.
Es. in `test_send_email_success`, `mock_smtp_class` è il primo argomento
perché è il decoratore più vicino alla firma della funzione.
"""


# Credenziali mancanti
@patch("core.alert.load_dotenv")
@patch("core.alert.os.getenv", return_value="")
def test_missing_credentials(
    mock_getenv: MagicMock,
    mock_dotenv: MagicMock,
    sample_dfs: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Verifica che sia sollevato ValueError se mancano credenziali in .env"""

    with pytest.raises(ValueError, match="Missing credentials."):
        _ = Notification(timestamp="2026-06-01T06-32-19")


# Costruzione del messaggio e allegati
@patch("core.alert.load_dotenv")
@patch("core.alert.os.getenv", return_value="dummy")
def test_build_msg(
    mock_getenv: MagicMock,
    mock_dotenv: MagicMock,
    sample_dfs: tuple[pd.DataFrame, pd.DataFrame],
) -> None:

    # Inizializza oggetto
    alert = Notification(timestamp="2026-06-01T06-38-16")

    msg = alert.build_msg(deactivated_rows=sample_dfs[0], inserted_rows=sample_dfs[1])

    # Verifica headers
    assert msg["Subject"] == f"{alert.timestamp} | Aggiornamento Menu Consorzio"
    assert msg["From"] == "dummy"
    assert msg["To"] == "dummy"

    # Verifica gestione allegati (dev'essere uno solo, non vuoto)
    attachments = list(msg.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == f"{alert.timestamp}_deactivated_rows.csv"

    content = attachments[0].get_payload(decode=True)
    assert isinstance(content, bytes)
    assert b"BIANCONIGLIO" in content


# Costruzione del messaggio e allegati
@patch("core.alert.load_dotenv")
@patch("core.alert.os.getenv", return_value="dummy")
def test_build_fatal_alert(
    mock_getenv: MagicMock,
    mock_dotenv: MagicMock,
    sample_dfs: tuple[pd.DataFrame, pd.DataFrame],
) -> None:

    # Inizializza oggetto
    alert = Notification(timestamp="2026-06-01T06-38-16")

    with patch(
        "core.alert.traceback.format_exc", return_value="errore"
    ) as mock_traceback:
        msg = alert.build_fatal_alert(mock_traceback)

    # Verifica headers
    assert msg["Subject"] == f"{alert.timestamp} | Errore Menu Consorzio"
    assert msg["From"] == "dummy"
    assert msg["To"] == "dummy"

    # Verifica gestione allegati (dev'essere uno solo, non vuoto)
    attachments = next(msg.iter_attachments(), None)
    assert attachments is None

    msg_body = msg.get_body(preferencelist=("plain",))
    assert msg_body is not None
    assert "errore" in msg_body.get_content()


# Invio email
@patch("core.alert.load_dotenv")
@patch("core.alert.os.getenv", return_value="dummy")
@patch("core.alert.smtplib.SMTP")
def test_send_email_success(
    mock_smtp_class: MagicMock,
    mock_getenv: MagicMock,
    mock_dotenv: MagicMock,
    sample_dfs: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """
    Verifica che la logica di invio tocchi il server SMTP corretto
    e chiami i metodi giusti (starttls, login, send_message, quit)
    senza inviare email reale
    """

    alert = Notification(timestamp="2026-06-01T06-48-11")

    # Server finto
    mock_server = MagicMock()
    mock_smtp_class.return_value = mock_server

    # Invio
    alert.send_email(
        alert.build_msg(deactivated_rows=sample_dfs[0], inserted_rows=sample_dfs[1])
    )

    # Verifica che SMTP sia stato inizializzato con i parametri giusti
    mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587)

    # Verifica ciclo connessione
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("dummy", "dummy")
    mock_server.send_message.assert_called_once()
    mock_server.quit.assert_called_once()
