from pathlib import Path

import google.cloud.storage as gcs

from .colors import *
from .const import BUCKET_NAME, IS_CLOUD, REMOTE_DB_BLOB

_client = None
_bucket = None

if not IS_CLOUD:
    try:
        _client = gcs.Client()
        _bucket = _client.bucket(BUCKET_NAME)
    except Exception:
        pass


def download_cloud_db(local_path: Path) -> None:
    """Scarica il database aggiornato del bucket GCS prima dell'esecuzione locale."""
    if IS_CLOUD or _bucket is None:
        return

    print(
        f"📥 {magenta('[CLOUD]')} "
        f"Download di '{REMOTE_DB_BLOB}' "
        f"dal bucket '{BUCKET_NAME}'"
    )
    try:
        blob = _bucket.blob(REMOTE_DB_BLOB)
        if blob.exists():
            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_path))
            print(
                f"✅ {magenta('[CLOUD]')} Database locale sincronizzato con il Cloud."
            )
        else:
            print(
                f"⚠️ {magenta('[CLOUD]')} Nessun database trovato nel bucket. Verrà creato uno nuovo."
            )
    except Exception as e:
        print(
            f"❌ {magenta('[CLOUD]')} Impossibile scaricare il DB dal Cloud: {e}. Uso il file locale."
        )


def upload_cloud_db(local_path: Path) -> None:
    """Carica il database locale aggiornato sul bucket GCS al termine dell'esecuzione"""
    if IS_CLOUD or _bucket is None:
        return

    print(
        f"📤 {magenta('[CLOUD]')} Caricamento del database aggiornato su '{BUCKET_NAME}'..."
    )
    try:
        blob = _bucket.blob(REMOTE_DB_BLOB)
        blob.upload_from_filename(str(local_path))
        print(
            f"✅ {magenta('[CLOUD]')} Sincronizzazione Cloud completata con successo."
        )
    except Exception as e:
        print(f"❌ {magenta('[CLOUD]')} Errore critico durante l'upload del DB: {e}")
