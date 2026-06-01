# 🍺 Consorzio Birre

Pipeline automatizzata che monitora le variazioni del menu del **Consorzio Birre** e invia notifiche email a ogni cambiamento rilevato.

- [🍺 Consorzio Birre](#-consorzio-birre)
  - [Panoramica](#panoramica)
  - [Architettura](#architettura)
  - [Storico](#storico)
  - [Infrastruttura](#infrastruttura)
  - [Interfaccia locale (TUI)](#interfaccia-locale-tui)
  - [Struttura del progetto](#struttura-del-progetto)
  - [Setup locale](#setup-locale)

## Panoramica

Lo scraper viene eseguito due volte al giorno su `Google Cloud`: recupera il menu corrente, lo confronta con l'ultima versione (se presente) e in caso di differenze invia un'email di notifica. Nessun intervento manuale richiesto.
In ambiente locale, lo script disabilita la modalità *headless* per offrire una TUI (**Terminal User Interface**) interattiva per navigare il menu, effettuare ricerche e consultare aggregazioni, il tutto da tastiera.  

La pipeline include un sistema di gestione errori integrato: in caso di anomalie (es. blocco dell'IP, cambiamenti nel layout del sito web), lo script solleva eccezioni gestite che garantiscono l'integrità dei dati e l'invio di alert di sistema, evitando falsi positivi nel database.

---

## Architettura

```mermaid
flowchart TD
    GCS[(Storage Volume\nDuckDB / JSON / XLSX)]

    subgraph GCP ["☁️ Google Cloud"]
        SCH[Cloud Scheduler]
        CB[Cloud Build]
        CR[Cloud Run Job]
    end

    subgraph pipeline ["Pipeline — main.py"]
        S[scraper.py]
        C[cleaner.py]
        DB[database.py]
        A[alert.py]
    end

    subgraph local ["💻 Esecuzione locale"]
        TUI[tui.py]
    end

    SITE([🌐 Sito Consorzio Birre])
    MAIL([📧 Email alert])
    USER([👤 Utente])

    SCH -->|trigger| CR
    CB -->|deploy| CR
    CR --> pipeline
    S -->|fetch| SITE
    S --> C --> DB
    DB <-->|read/write| GCS
    DB -->|diff| A
    A -->|alert| MAIL
    MAIL -->|notify| USER
    USER <-->|keyboard| TUI
```

1. **Scraping** — Recupera e analizza il menu con `requests` e `BeautifulSoup`
2. **Pulizia** — Normalizza i dati grezzi con `pandas` e `re` (stdlib).
3. **Persistenza** — `duckdb` salva il risultato con storico completo delle modifiche (**SCD Type 2**). Per ogni esecuzione si generano degli snapshot testuali (`.json` + `.xlsx`).
4. **Alert** — Notifica SMTP inviata in presenza di variazioni, completa di allegati `.csv` generati al volo in memoria con i dettagli dei cambiamenti.
5. **TUI** — In esecuzione locale, interfaccia interattiva a terminale per navigare e interrogare i dati

---

## Storico

Grazie alla logica SCD Type 2 (**SlowlyChangingData Type 2**), il database garantisce la piena auditability del dato: ogni variazione di prezzo o disponibilità è storicizzata, permettendo di ricostruire l'esatta evoluzione del menu nel tempo.

---

## Infrastruttura

| Componente | Servizio |
| --- | --- |
| Runtime | Google Cloud Run Job |
| Scheduling | Google Cloud Scheduler (2/gg) |
| Storage | Volume montato su Cloud Run / Ambiente Locale |
| CI/CD | Google Cloud Build |
| Container | Docker |

---

## Interfaccia locale (TUI)

In locale, lo script rileva l'assenza della variabile d'ambiente `HEADLESS` e avvia una TUI navigabile da tastiera che consente di:

- **Sfogliare** — navigazione per categoria tra le voci disponibili
- **Ricercare** — filtro testuale in tempo reale su nome e descrizione
- **Consultare statistiche** — numero di articoli, prezzo massimo, prezzo minimo, etc.

Su `Cloud Run` la stessa variabile d'ambiente, impostata direttamente nella configurazione del Job, disabilita la TUI e lascia girare la pipeline in modalità headless.

---

## Struttura del progetto

```plain
.
├── main.py
└── core/
    ├── scraper.py      # Download e parsing HTML
    ├── cleaner.py      # Normalizzazione dati
    ├── database.py     # Persistenza dati e logica SCD Type 2
    ├── alert.py        # Notifiche SMTP (Gmail)
    ├── tui.py          # Terminale interattivo (solo fuori dal cloud!)
    ├── const.py        # Costanti
    └── colors.py       # Colori per tui.py
```

## Setup locale

1. Clonare il repository: `git clone https://github.com/m-contini/Consorzio.git`
2. Creare ambiente virtuale: `python -m venv venv && source venv/bin/activate`
3. Installare le dipendenze: `python -m pip install -r requirements.txt`
4. Creare apposito file `.env` basato su `env.example` (richiede API key di `Google Cloud`).
5. Avvia: `python main.py`
