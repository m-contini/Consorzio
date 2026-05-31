import json
from pathlib import Path
from typing import Any, TypeAlias
import requests
from bs4 import BeautifulSoup

from .const import MENU_JSON

SottoCategoria: TypeAlias = list[dict[str, Any]]
SezioneMenu: TypeAlias = dict[str, SottoCategoria]
MenuCompleto: TypeAlias = dict[str, SezioneMenu]


class Scraper:
    """
    Esegue lo scraping del menu dal sito web del Consorzio Birre.
    Utilizza BeautifulSoup per navigare la struttura HTML e organizzare i dati
    in una gerarchia a tre livelli: Macro-categoria, Categoria e Prodotto.
    """

    def __init__(self, output_file: Path):
        # File JSON su cui scrivere il menù
        self.output_file = output_file
        self.menu: MenuCompleto = {}

    def parse_menu(self, url: str) -> MenuCompleto:

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ Errore durante la richiesta HTTP: {e}")
            raise e

        soup = BeautifulSoup(response.text, "lxml")

        for div in soup.find_all("div", class_="vc_row wpb_row vc_row-fluid"):
            # Non ci interessa questo elemento
            if div.find("div", class_="wpb_column vc_column_container vc_col-sm-1/5"):
                continue

            wpb_column = div.find(
                "div", class_="wpb_column vc_column_container vc_col-sm-12"
            )
            if not wpb_column:
                print("Skipping div")
                continue

            element = wpb_column.find(
                "div",
                class_="vc_tta-container",
                attrs={"data-vc-action": "collapseAll"},
            )
            if not element:
                continue

            # MACROCATEGORIA: ('BEVI BENE', 'MANGIA BENE', 'DOPO CENA')
            h2 = element.find("h2")
            if not h2:
                print("Warning: h2 not found (MACROCATEGORIA)")
                continue

            macro_categoria = h2.get_text(strip=True)

            for panel in element.find_all("div", class_="vc_tta-panel"):
                # CATEGORIA: "BIRRE ALLA SPINA (possibili allergeni: glutine)"
                h4 = panel.find("h4", class_="vc_tta-panel-title")
                if not h4:
                    print("Warning: h4 not found (CATEGORIA)")
                    continue

                categoria = h4.get_text(strip=True)

                for prodotto in panel.find_all("div", class_="basel-menu-price"):
                    # NOME: "SANFALERFO Consorzio birre official (Birra agricola)"
                    titolo_el = prodotto.find("h3", class_="menu-price-title")
                    nome = titolo_el.get_text(strip=True) if titolo_el else ""

                    # DETTAGLI: "LAGER German style 4,9% Alc vol"
                    dettagli_el = prodotto.find("div", class_="menu-price-details")
                    dettagli = dettagli_el.get_text(strip=True) if dettagli_el else ""

                    # PREZZI
                    # Talvolta contiene capacità: "€ 13,5 bicchiere 0,5 cl € 7,00 bicchiere 0,25 cl"
                    # oppure prezzo singolo: "€ 5,50"
                    prezzo_el = prodotto.find("div", class_="menu-price-price")
                    prezzo = prezzo_el.get_text(" ", strip=True) if prezzo_el else ""

                    if macro_categoria not in self.menu:
                        self.menu[macro_categoria] = {}

                    if categoria not in self.menu[macro_categoria]:
                        self.menu[macro_categoria][categoria] = []

                    self.menu[macro_categoria][categoria].append(
                        {"name1": nome, "name2": dettagli, "price": prezzo}
                    )
        return self.menu

    def save_json(self, menu_json: MenuCompleto) -> None:
        """Salva il menù in due file JSON:

        - Quello passato al costruttore di classe
        - Quello di default (menu_updated.json)
        """

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        MENU_JSON.parent.mkdir(parents=True, exist_ok=True)
        for file in (self.output_file, MENU_JSON):
            with open(file, "w", encoding="utf-8") as f:
                json.dump(menu_json, f, ensure_ascii=False, indent=4)
