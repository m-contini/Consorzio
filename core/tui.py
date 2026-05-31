import html
import os
from typing import Any
import pandas as pd
from InquirerPy.prompts.list import ListPrompt
from InquirerPy.base.control import Choice
from tabulate import tabulate

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.formatted_text import HTML


class InteractiveMenu:
    """
    Gestisce un menu interattivo da terminale per esplorare i dati del menù.
    """
    COLS = ["Macro-categoria", "Categoria", "Articolo", "Dettagli", "Size", "Prezzo"]

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def run(self) -> None:
        """
        Avvia il loop principale del menu di navigazione.
        """
        s: str = ">>>>> MENU PRINCIPALE <<<<<"
        print("=" * len(s))
        print(s)
        print("=" * len(s))

        while True:
            try:
                # `Choice` mappa testo leggibile a un valore
                options = [
                    Choice(value="naviga", name="🍔 1) Sfoglia"),
                    Choice(value="ricerca", name="🔍 2) Ricerca"),
                    Choice(value="statistiche", name="📊 3) Statistiche"),
                    Choice(value="visualizza", name="📖 4) Visualizza tutto"),
                    Choice(value="esci", name="❌ 5) Esci"),
                ]

                # `select` crea menu navigabile tramite frecce tastiera
                choice = ListPrompt(
                    message="Muoviti con [↑/↓] e premi [Enter] per selezionare:",
                    choices=options,
                    default="naviga",
                    pointer="→",
                    border=True,
                ).execute()

                # Gestione scelte e keybindings
                if choice == "naviga":
                    self._browse_recursively(livello=0, last_keys=())
                elif choice == "ricerca":
                    self._handle_lookup()
                elif choice == "statistiche":
                    self._show_stats()
                elif choice == "visualizza":
                    self._showall()
                elif choice == "esci":
                    raise KeyboardInterrupt

            except KeyboardInterrupt:
                print("\n\n🚪 Addio...\n")
                break

    def _showall(self) -> None:
        """
        Stampa a video l'intero menu in formato tabella.
        """
        df = self.df.reset_index()
        print(
            tabulate(
                df[self.COLS].to_dict(orient="records"),
                headers="keys",
                tablefmt="fancy_grid",
                colalign=["left"] * 4 + ["right"] * 2,
                maxcolwidths=40,
                showindex=False,
            )
        )

    @staticmethod
    def strcontains(series: pd.Series, word: str, case: bool = False):
        """Helper per verificare se una stringa è contenuta in una serie pandas."""
        return series.str.contains(word, case=case)

    def _browse_recursively(self, livello: int, last_keys: tuple[str, ...]) -> None:
        """
        Permette la navigazione gerarchica del menu (Macro-categoria -> Categoria -> Articolo).

        Args:
            livello (int): Il livello di profondità attuale nell'indice (0, 1, 2).
            last_keys (tuple[str, ...]): Le chiavi selezionate ai livelli precedenti.
        """
        try:
            # Oltre l'ultimo indice, mostra i prodotti finali
            if livello == 3:
                # Filtra DataFrame combinando i 3 indici selezionati
                selected_product: pd.DataFrame = self.df.xs(last_keys, level=[0, 1, 2])  # type: ignore
                print("\n" + "-" * 40)
                print(f"📃 Dettaglio per: {' > '.join(last_keys)}")
                print("-" * 40)
                print(
                    tabulate(
                        selected_product.to_dict(orient="records"),
                        headers="keys",
                        tablefmt="grid",
                    )
                )
                input("\nPremi [Enter] per tornare indietro...")
                return self._browse_recursively(livello - 1, last_keys=last_keys[:-1])

            # Recupera opzioni disponibili per il livello attuale basandosi sulle scelte precedenti
            if livello == 0:
                available_options = self.df.index.get_level_values(0).unique()
                title = "Selezionare la Categoria (es. Birre, Panini)"
            else:
                # Filtra il 3-indice per mantenere solo figli delle categorie in indice
                sub_df = self.df.xs(last_keys, level=list(range(livello)))
                available_options = sub_df.index.get_level_values(0).unique()
                title = f"Seleziona in {' > '.join(last_keys)}:"

            # Costruzione scelte + opzione "Indietro"
            choices = [Choice(value=opt, name=str(opt)) for opt in available_options]
            choices.append(Choice(value="..indietro", name="⬅️ [Torna Indietro]"))

            choice = ListPrompt(
                message=title, choices=choices, pointer="➡️", border=True
            ).execute()
        except KeyboardInterrupt:
            choice = "..indietro"
        
        # Logica di ritorno al livello superiore o discesa nel prossimo livello
        if choice == "..indietro":
            if livello == 0:
                return
            self._browse_recursively(livello - 1, last_keys[:-1])
        else:
            self._browse_recursively(livello + 1, last_keys + (choice,))

    def _handle_lookup(self) -> None:
        """
        Gestisce la ricerca globale in tempo reale su tutto il DataFrame.
        """
        # Inizializzazione keybindings
        kb = KeyBindings()

        # Questa stringa conterrà l'output della tabella renderizzata
        tabella_renderizzata: list[str] = [
            "💡 Digita qualcosa per iniziare a filtrare il menu..."
        ]

        def on_change(buffer: Buffer) -> None:
            """Callback invocata a ogni pressione di tasto nel campo di ricerca."""
            nonlocal tabella_renderizzata
            current_search: str = buffer.text

            if not current_search.strip():
                tabella_renderizzata = [
                    "💡 Digita qualcosa per iniziare a filtrare il menu..."
                ]
                return

            # RICERCA FLESSIBILE
            # controlla sia il testo nei 3 indici
            # che il testo nelle colonne "Size" e "Prezzo"
            df_flattened = self.df.copy()
            if "Macro-categoria" not in df_flattened.columns:
                df_flattened.reset_index(inplace=True)
            mask = (
                df_flattened.astype(str)
                .apply(self.strcontains, args=(current_search,))
                .any(axis=1)
            )
            results = df_flattened.loc[mask]

            if not results.empty:
                tabella_renderizzata = [
                    f"✨ Risultati trovati per '{current_search}':",
                    tabulate(
                        results[self.COLS].to_dict(orient="records"),
                        headers="keys",
                        tablefmt="fancy_grid",
                        maxcolwidths=40,
                        showindex=False,
                    ),
                ]
            else:
                tabella_renderizzata = [
                    f"❌ Nessun risultato corrisponde a '{current_search}'."
                ]

        # ----------------------- #
        # ----- KEYBINDINGS ----- #
        # ----------------------- #
        @kb.add("enter")
        @kb.add("escape")  # Esce dalla ricerca
        def _(event: KeyPressEvent):
            os.system("cls" if os.name == "nt" else "clear")
            event.app.exit()

        @kb.add("c-c")  # Pulisce il campo di input
        def _(event: KeyPressEvent):
            event.current_buffer.text = ""

        # ----------------------- #
        # ----- INTERFACCIA ----- #
        # ----------------------- #
        search_buffer = Buffer(on_text_changed=on_change)

        # Questa funzione viene invocata da prompt_toolkit a ogni frame per generare l'area sotto l'input
        def get_table_content() -> HTML:
            # Uniamo le righe della tabella e le passiamo al motore di rendering
            # escapando i caratteri speciali
            corpo_testo = html.escape("\n".join(tabella_renderizzata))
            return HTML(f"\n<ansicyan><b>[Risultati]</b></ansicyan>\n{corpo_testo}")

        # 1. Una riga di intestazione fissa
        # 2. Il campo di input (dove il testo inserito resta visibile e non sparisce)
        # 3. Una finestra dinamica che mostra la tabella aggiornata in tempo reale
        input_layout = HSplit(
            [
                Window(
                    content=FormattedTextControl(
                        HTML(
                            "==================================================\n"
                            "🔍 RICERCA IN TEMPO REALE\n"
                            "==================================================\n"
                            "[Invio] o [Esc] per uscire | [Ctrl+C] svuota testo\n\n"
                            "<ansigreen>Cerca nel menu ➔ </ansigreen>"
                        )
                    ),
                    height=5,
                ),
                Window(
                    content=BufferControl(buffer=search_buffer, key_bindings=kb),
                    height=1,
                ),
                Window(
                    content=FormattedTextControl(get_table_content)
                ),  # Si aggiorna da sola!
            ]
        )

        layout = Layout(container=input_layout, focused_element=search_buffer)

        app = Application[None](layout=layout, key_bindings=kb, full_screen=True)
        app.run()

    def _show_stats(self) -> None:
        print("\n" + "=" * 30)
        print("📊 STATISTICHE DEL MENU")
        print("=" * 30)

        if self.df.empty:
            print("Menu vuoto. Nessuna statistica disponibile.")
            return

        # Calcola il numero di elementi per la prima categoria dell'indice (es. Bevande. Cibo)
        count = self.df.groupby(level=0).size().reset_index(name="Numero ARticoli")
        count.columns = ["Categoria", "Articoli"]
        print("\n📦 QUANTITÀ PER CATEGORIA:")
        print(
            tabulate(
                count.to_dict(orient="records"),
                headers="keys",
                tablefmt="grid",
                showindex=False,
            )
        )

        # Statistiche sui prezzi se la colonna è numerica
        if "Prezzo" in self.df.columns:
            price_stats = (
                self.df.groupby(level=0)["Prezzo"]
                .agg(["mean", "min", "max"])
                .reset_index()
            )
            price_stats.columns = ["Categoria", "Media (€)", "Min (€)", "Max (€)"]
            price_stats["Media (€)"] = price_stats["Media (€)"].round(2)

            total_items = len(self.df)
            avg_price = self.df["Prezzo"].mean()
            most_expensive = self.df["Prezzo"].max()
            cheapest = self.df["Prezzo"].min()

            overview: list[list[Any]] = [
                ["Totale Articoli in Menu", total_items],
                ["Prezzo Medio Globale", f"{avg_price:.2f} €"],
                ["Piatto più Economico", f"{cheapest:.2f} €"],
                ["Piatto più Caro", f"{most_expensive:.2f} €"],
            ]

            print("\n🌍 PANORAMICA GENERALE:")
            print(
                tabulate(overview, headers=["Descrizione", "Valore"], tablefmt="grid")
            )
        else:
            print("\n⚠️ Colonna 'Prezzo' non trovata.")
