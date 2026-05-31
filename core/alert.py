from datetime import datetime
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import pandas as pd

from .colors import *


class Notification:
    """
    Gestisce l'invio di notifiche via email contenenti i cambiamenti rilevati nel database.
    I dati vengono inviati come allegati CSV generati in memoria.
    """

    def __init__(
        self, *rows: pd.DataFrame, timestamp: datetime, reciprocal: bool = True
    ) -> None:

        # Il parametro `reciprocal`, se True, imposta
        # il mittente come destinatario.
        if not self._set_credentials(reciprocal):
            print(
                f"{red('[EMAIL]')} ❌ Credentials not set. Unable to send email: check .env file."
            )
            return

        self.deactivated_rows, self.inserted_rows = rows
        self.timestamp: datetime = timestamp

    def _set_credentials(self, reciprocal: bool) -> bool:
        """Carica le variabili d'ambiente e imposta le credenziali email."""
        load_dotenv()
        self._api_key = os.getenv("API_KEY", "")
        self._sender = os.getenv("SENDER", "")
        self._recipient = self._sender if reciprocal else os.getenv("RECIPIENT", "")
        if not all([self._api_key, self._sender, self._recipient]):
            return False
        return True

    def _build_msg(self) -> EmailMessage:
        """Costruisce il messaggio email con gli allegati."""
        msg = EmailMessage()
        msg["From"] = self._sender
        msg["To"] = self._recipient
        msg["Subject"] = f"{self.timestamp} | Aggiornamento Menu Consorzio"
        msg.set_content("Ciao,\n\nIn allegato le variazioni del menu.\n\nSaluti.\n")

        # ---------------------------------------------------------
        # GESTIONE ALLEGATI IN MEMORIA (Nessun file sul disco)
        # ---------------------------------------------------------
        changed_rows = {
            f"{self.timestamp}_deactivated_rows.csv": self.deactivated_rows,
            f"{self.timestamp}_inserted_rows.csv": self.inserted_rows,
        }
        for fname, df in changed_rows.items():
            # Il DataFrame
            # viene convertito in stringa CSV e poi codificato in byte per l'invio
            df_as_str = df.to_csv(index=False, sep=";")
            msg.add_attachment(
                df_as_str.encode("utf-8"),
                maintype="text",
                subtype="csv",
                filename=fname,
            )

        return msg

    def send_email(
        self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587
    ) -> None:

        msg = self._build_msg()

        # ---------------------------------------------------------
        # INVIO EMAIL
        # ---------------------------------------------------------
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(self._sender, self._api_key)
            server.send_message(msg)
            server.quit()
            print(
                f"{green('[EMAIL]')} 📧 Notification sent successfully to {self._recipient}."
            )
        except Exception as e:
            print(f"{red('[EMAIL]')} ❌ Error during email sending: {e}")
