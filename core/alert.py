import os
import smtplib
import traceback
from email.message import EmailMessage

import pandas as pd
from dotenv import load_dotenv

from .colors import *


class Notification:
    """
    Gestisce l'invio di notifiche via email contenenti i cambiamenti rilevati nel database.
    I dati vengono inviati come allegati CSV generati in memoria.
    """

    def __init__(self, timestamp: str, reciprocal: bool = True) -> None:

        # Il parametro `reciprocal`, se True, imposta
        # il mittente come destinatario.
        if not self._set_credentials(reciprocal):
            print(
                f"{red('[EMAIL]')} ❌ Credentials not set. Unable to send email: check .env file."
            )
            raise ValueError("Missing credentials.")

        self.timestamp: str = timestamp

    def _set_credentials(self, reciprocal: bool) -> bool:
        """Carica le variabili d'ambiente e imposta le credenziali email."""
        load_dotenv()
        self._api_key = os.getenv("API_KEY", "")
        self._sender = os.getenv("SENDER", "")
        self._recipient = self._sender if reciprocal else os.getenv("RECIPIENT", "")
        if not all([self._api_key, self._sender, self._recipient]):
            return False
        return True

    def build_msg(
        self, deactivated_rows: pd.DataFrame, inserted_rows: pd.DataFrame
    ) -> EmailMessage:
        """Costruisce il messaggio email con gli allegati."""
        msg = EmailMessage()
        msg["From"] = self._sender
        msg["To"] = self._recipient
        msg["Subject"] = f"{self.timestamp} | Aggiornamento Menu Consorzio"
        msg.set_content("Ciao,\n\nIn allegato le variazioni del menu.\n\nSaluti.\n")

        # -----------------------------------
        # Tabelle HTML nel body del messaggio
        # -----------------------------------
        cols = [
            "Macro-categoria",
            "Categoria",
            "Articolo",
            "Dettagli",
            "Size",
            "Prezzo",
        ]

        deactivated_html = (
            "<i> Nessuna riga disattivata.</i><br>"
            if deactivated_rows.empty
            else '<p><strong><span style="color: #d32f2f;">🔴 Righe disattivate:</span></strong></p>'
            + deactivated_rows[cols].fillna("N/A").to_html(index=False)
        )
        inserted_html = (
            "<i> Nessuna riga inserita.</i><br>"
            if inserted_rows.empty
            else '<p><strong><span style="color: #388e3c;">🟢 Righe inserite:</span></strong></p>'
            + inserted_rows[cols].fillna("N/A").to_html(index=False)
        )

        html_body = (
            "<p>Ciao,</p>"
            "<p>In allegato le variazioni al menù.</p>"
            "<p>Di seguito il riepilogo delle modifiche:</p>"
            f"{deactivated_html}"
            f"{inserted_html}"
            "<p>Saluti,</p>"
            "<p><strong>m-contini</strong></p>"
        )
        msg.add_alternative(html_body, subtype="html")

        # -------------------------------------------------------
        # GESTIONE ALLEGATI IN MEMORIA (Nessun file sul disco)
        # -------------------------------------------------------
        changed_rows = {
            f"{self.timestamp}_deactivated_rows.csv": deactivated_rows,
            f"{self.timestamp}_inserted_rows.csv": inserted_rows,
        }
        for fname, df in changed_rows.items():
            if df.empty:
                continue
            # Il DataFrame # viene convertito in stringa CSV
            # e poi codificato in byte per l'invio
            df_as_str = df.to_csv(index=False, sep=";")
            msg.add_attachment(
                df_as_str.encode("utf-8"),
                maintype="text",
                subtype="csv",
                filename=fname,
            )

        return msg

    def build_fatal_alert(self, error: Exception) -> EmailMessage:
        """Costruisce il messaggio email con gli allegati."""
        msg = EmailMessage()
        msg["From"] = self._sender
        msg["To"] = self._recipient
        msg["Subject"] = f"{self.timestamp} | Errore Menu Consorzio"

        stack_trace = traceback.format_exc()
        msg.set_content(
            "Ciao,\n\n"
            "Sfortunatamente si è verificato un errore "
            "durante l'esecuzione dello script:\n\n"
            f"{stack_trace}"
        )

        return msg

    def send_email(
        self,
        msg: EmailMessage,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
    ) -> None:

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
            raise e
