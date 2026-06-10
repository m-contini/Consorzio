import json
import re
import warnings
from pathlib import Path
from typing import NamedTuple

import pandas as pd
from tabulate import tabulate

from .scraper import MenuCompleto


class Rule(NamedTuple):
    """
    Rappresenta una RegEx.

    Attributes:
        pattern (str): La stringa regex utilizzata per identificare e catturare i dati.
        invert_groups (bool): Se True, inverte l'ordine dei gruppi catturati (es. Size prima di Prezzo).
        flags (int): Flag opzionali dal modulo re (es. re.IGNORECASE).
    """

    pattern: str
    invert_groups: bool = False
    flags: int = 0


class Cleaner:
    """Applica una serie di operazioni di pulizia e trasformazione al DataFrame del menu."""

    def __init__(self, input_file: Path) -> None:
        # File JSON da cui leggere il menù
        self.input_file = input_file
        self.menu: MenuCompleto = self.load_json()
        # DataFrame contenente il menù ripulito
        self.df: pd.DataFrame = pd.DataFrame()

    def load_json(self) -> MenuCompleto:
        """
        Carica il contenuto del file JSON specificato da `self.input_file`.
        """
        try:
            with open(self.input_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def clean_pipeline(self) -> None:
        """
        Applica una serie di operazioni di pulizia e trasformazione al DataFrame del menu.
        """

        # 1. Costruzione DataFrame da menù JSON
        self._build_df()

        # 2. Estrazione prezzi mancanti dai dettagli
        self._fill_empty_prices()

        # 3. Parsing degli importi
        self._parse_prices()

        # 4. Riempimento `Size` vuoti
        self._fill_empty_size()

        # 5. Rimozione spazi bianchi
        self.strip_all()

        # 6. Rimozione duplicati
        self.df.drop_duplicates(inplace=True)

    def strip_all(self) -> None:
        for col in ("Articolo", "Dettagli", "Categoria"):
            if col in self.df.columns:
                # Rimozione spazi iniziali/finali
                self.df[col] = self.df[col].astype(str).str.strip()
                # Spazi consecutivi
                self.df[col] = self.df[col].str.replace(r"\s+", " ", regex=True)

    def _build_df(self) -> None:
        """Costruisce il DataFrame a partire dal dizionario `self.menu`"""
        records: list[dict[str, str]] = []
        for macro, categorie in self.menu.items():
            for categoria, lista_prodotti in categorie.items():
                for prodotto in lista_prodotti:
                    records.append(
                        {
                            "Macro-categoria": macro,
                            "Categoria": categoria,
                            "Articolo": prodotto.get("name1", ""),
                            "Dettagli": prodotto.get("name2", ""),
                            "Prezzo": prodotto.get("price", ""),
                        }
                    )

        self.df = pd.DataFrame(records)

        # Multi-index su 3 livelli
        self.df.set_index(["Macro-categoria", "Categoria", "Articolo"], inplace=True)

    def _parse_prices(self) -> None:

        rules: list[Rule] = [
            Rule(r"(€.+?)(media|piccola)"),
            # Gruppo 1: Size, Gruppo 2: Prezzo -> da invertire
            Rule(r"(Bicchiere\s\d+\scl)\s(€\s[\d,.]+)", True),
            # Gruppo 1: Size, Gruppo 2: Prezzo -> da invertire
            Rule(r"(Bottiglia\s[\d,.]+\slt)\s(€\s[\d,.]+)", True),
            Rule(r"(€\s*[\d,]+)\s(bottiglia|calice)", flags=re.IGNORECASE),
            Rule(r"(€\s[\d\,]+)\sbicchiere\sda\s([\d\,cl\s]+)"),
        ]

        processed_chunks: list[pd.DataFrame] = []

        df = self.df
        for rule in rules:
            # Righe che soddisfano la regex
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                mask = (
                    df["Prezzo"]
                    .astype(str)
                    .str.contains(rule.pattern, flags=rule.flags, na=False, regex=True)
                )

            if not mask.any():
                print(f"⚠️ No products satisfy this RegEx: {rule.pattern}")
                continue

            slice = df[mask].copy()

            # Estrazione dei gruppi definiti nella regex
            extracts = slice["Prezzo"].str.extractall(rule.pattern, flags=rule.flags)
            # Elimina l'indice 'match' creato dalla RegEx
            extracts = extracts.droplevel(level=-1)

            # Inverte i gruppi: il gruppo 1 diventa Prezzo e il gruppo 0 diventa Size, se previsto
            col_order = (
                {1: "Prezzo", 0: "Size"}
                if rule.invert_groups
                else {0: "Prezzo", 1: "Size"}
            )

            # Applica la rinomina delle colonne basata sull'ordine dei gruppi
            clean_slice = slice.drop(columns=["Prezzo"]).join(
                extracts.rename(columns=col_order)
            )

            # Blocco ripulito con prezzo isolato
            processed_chunks.append(clean_slice)

            # Rimozione dal DataFrame corrente delle righe appena fatte, così non subiscono le altre regex
            df = df[~mask]

        # Fase finale: Gestione di tutto ciò che NON ha subìto RegEx, se c'è
        if not df.empty:
            single_prices = df.copy()
            # Estrae solo il prezzo pulito se c'è testo residuo inutile attorno
            single_prices["Prezzo"] = (
                single_prices["Prezzo"].astype(str).str.extract(r"(€\s*[\d,.]+)")[0]
            )
            # Non distinguendo fra "piccola", "media", "bottiglia", ..., si setta "N/A"
            single_prices["Size"] = "N/A"
            processed_chunks.append(single_prices)

        # DataFrame ricomposto unendo tutti i pezzi
        self.df = pd.concat(processed_chunks).sort_index()

        # Ordine delle colonne
        remaining_cols = self.df.columns.drop(["Size", "Prezzo"])
        self.df = self.df[[*remaining_cols, "Size", "Prezzo"]]

        # Pulizia del prezzo
        self._price_to_float()

    def _fill_empty_size(self) -> None:
        """
        Estrae la dimensione (`Size`) dal campo `Dettagli` per gli articoli in cui è mancante.

        **Esempio di record da correggere:**
        ```python
        df = self.df
        df[df['Size'].eq('N/A') & df['Dettagli'].str.contains("[\\d,]+\\scl", regex=True)]
        ```

        **Struttura dei dati interessati:**
        ```
        Articolo                                           Dettagli                                           Size  Prezzo
        DEGUSTAZIONE BIRRE                                 4 Bicchieri da 0,15 cl a scelta dalla taplist      N/A    10.0
        BIRRA GLUTEN FREE                                  33 cl                                              N/A     7.5
        BIRRA ALCOHOL FREE <0,5 VOL                        50 cl                                              N/A     8.5
        CHUPITO LIQUORE                                    chiedere tipologie, 2,5 cl                         N/A     2.5
        ```
        """
        pattern = r"([\d,]+\scl)"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            mask = self.df["Size"].eq("N/A") & self.df["Dettagli"].str.contains(
                pattern, regex=True
            )
        slice = self.df.loc[mask, "Dettagli"]

        self.df.loc[slice.index, "Size"] = self.df.loc[
            slice.index, "Dettagli"
        ].str.extract(pattern)[0]

    def _fill_empty_prices(self) -> None:
        """
        Estrae informazioni sul prezzo, laddove vuoto,
        direttamente dal campo `Dettagli` tramite espressioni regolari.

        Le righe risultanti ereditano lo stesso multi-indice della riga originale.

        **Esempio di record da correggere:**
        Alcuni elementi hanno prezzo vuoto, ad es.:
        ```python
        >>> df = self.df
        >>> # Prezzo vuoto
        >>> df.loc[('MANGIA BENE', 'TAGLIERI DI SALUMI E FORMAGGI', 'EXTRA'), 'Prezzo'].item()
        >>> ''
        >>> # Dettagli dell'articolo con prezzo vuoto
        >>> df.loc[('MANGIA BENE', 'TAGLIERI DI SALUMI E FORMAGGI', 'EXTRA'), 'Dettagli'].item()
        >>> 'Pane extra € 2.50Salsa per formaggi extra € 3,00Miele extra € 2.50Pane senza Glutine € 3,00'
        ```

        Mediante il RegEx pattern `(.+?)€([\\s\\.\\,\\d]{5})` si può estrarre:
        ```python
        >>> [('Pane extra ', ' 2.50'), ..., ('Pane senza Glutine ', ' 3,00')]
        ```

        **Struttura del DataFrame (`slice`) estratto:**
        ```
        Articolo         Dettagli                      Prezzo
        EXTRA            Pane extra                    2.50
        EXTRA            Salsa per formaggi extra      3,00
        EXTRA            Miele extra                   2.50
        EXTRA            Pane senza Glutine            3,00
        ```
        """

        # Esploderà in 4 nuove righe tramite RegEx, ciascuna con suo prezzo,
        # poste sullo stesso 3-indice della riga originale inesplosa.
        empty_price = self.df["Prezzo"] == ""

        pattern = r"(.+?)€([\s\.\,\d]{5})"
        slice = self.df.loc[empty_price, "Dettagli"].str.extractall(pattern)
        # Elimina l'indice 'match' creato dalla RegEx
        slice = slice.droplevel(level=-1)

        # Assegna Dettagli della slice a Dettagli del menu e Prezzo della slice a Prezzo del menu
        self.df.loc[slice.index, "Dettagli"] = slice[0].str.strip()
        self.df.loc[slice.index, "Prezzo"] = "€ " + slice[1].str.strip()

    def _price_to_float(self) -> None:
        """Rimuove simboli valuta, spazi e caratteri speciali, normalizza la virgola in punto"""
        self.df["Prezzo"] = self.df["Prezzo"].str.replace(r"[€\s\xa0]", "", regex=True)
        self.df["Prezzo"] = self.df["Prezzo"].str.replace(",", ".", regex=False)
        self.df["Prezzo"] = pd.to_numeric(self.df["Prezzo"], errors="coerce")

        if not pd.api.types.is_numeric_dtype(self.df.dtypes["Prezzo"]):
            raise ValueError(
                "Attenzione: la colonna 'Prezzo' non è di tipo float. Parsing fallito."
            )

    def preview(self, cols: list[str], n: int) -> str:
        """Anteprima del DataFrame"""
        return tabulate(
            self.df[cols].sample(n).to_dict(orient="records"),
            headers="keys",
            tablefmt="grid",
            maxcolwidths=25,
            showindex=False,
        )

    def to_xlsx(self) -> None:
        """Salva il DataFrame in un file Excel"""
        self.input_file.parent.mkdir(parents=True, exist_ok=True)
        fpath: Path = self.input_file.with_suffix(".xlsx")
        with pd.ExcelWriter(fpath, engine="xlsxwriter") as writer:
            self.df.to_excel(writer)  # type: ignore
