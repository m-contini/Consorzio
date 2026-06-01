# 🧪 Consorzio Birre

Test d'integrazione e unitari per:

- [🧪 Consorzio Birre](#-consorzio-birre)
  - [Caratteristiche](#caratteristiche)
  - [Funzioni testate](#funzioni-testate)
  - [Continuos Integration (CI)](#continuos-integration-ci)
  - [Esecuzione](#esecuzione)

## Caratteristiche

1. **Mocking**: le chiamate HTTP e le connessioni SMTP vengono intercettate e simulate. Verifica che gli input e gli output siano corretti senza effettuare reali richieste;
2. **RAM**: i test sulla persistenza dei dati usano un database in-memory come permesso da DuckDB (`with duckdb.connect(":memory:")`). Il database si crea, testa e distrugge senza lasciare file residui;
3. **Cartelle temporanee**: i test per la scrittura dei file (es. salvataggio menù in JSON) utilizzano `pytest` per lavorare in cartelle isolate e temporanee.

## Funzioni testate

- `test_cleaner.py`: verifica che la classe gestisca diversi tipi di formato di prezzo, e che assicuri la pipeline isolando o segnalando valori non convertibili.
- `test_database.py`: verifica che gli id vengano hashati correttamente, simulando ciclo di vita del dato nel caso di nuovi articoli, articoli rimossi, articoli modificati di prezzo. Verifica anche la logica **SCD Type 2**.
- `test_scraper.py`: verifica che l'analisi di una stringa HTML estragga lo stesso albero di elementi e tag HTML, affinché vengano riconosciute categorie e sotto-categorie del menù.
- `test_alert.py`: verifica che il corpo dell'email e gli allegati CSV vengano generati solo se contengono variazioni e che il sistema blocchi l'esecuzione in caso di assenza delle credenziali.

## Continuos Integration (CI)

Il progetto integra una pipeline di CI tramite **GitHub Actions**.

Per ogni `git push` verso la repository, un'automazione si occupa di:

1. Configurare un ambiente isolato con la corretta versione di Python;
2. Installare le dipendenze da `requirements.txt`;
3. Lanciare l'intera suite di test in modalità headless (senza TUI per l'utente).

Questo garantisce, prima del deploy su Google Cloud, che qualsiasi modifica al codice non rompa le funzionalità.

## Esecuzione

1. Attivare ambiente virtuale:

    ```bash
    # Linux
    source venv/bin/activate
    # Windows
    venv\Scripts\Activate.ps1
    ```

2. Avvio: `pytest -vv`
