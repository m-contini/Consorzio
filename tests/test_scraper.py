import pytest
from unittest.mock import MagicMock, patch

import json
from pathlib import Path
from core.scraper import Scraper


@pytest.fixture
def scraper_obj(tmp_path: Path):

    # Inizializza lo Scraper assegnandogli un file di output posizionato
    # in una cartella temporanea sicura generata da pytest.
    fake_json_menu = tmp_path / "menu_test.json"

    return Scraper(output_file=fake_json_menu)


# Parsing HTML
def test_parse_menu_extraction(scraper_obj: Scraper) -> None:
    """Simula una risposta HTTP contenente HTML affine a quello del Consorzio"""
    mock_html = """
    <html>
        <div class="vc_row wpb_row vc_row-fluid">
            <div class="wpb_column vc_column_container vc_col-sm-12">
                <div class="vc_tta-container" data-vc-action="collapseAll">
                    <h2>BEVI BENE</h2> <div class="vc_tta-panel">
                        <h4 class="vc_tta-panel-title">BIRRE ALLA SPINA</h4> <div class="basel-menu-price">
                            <h3 class="menu-price-title">SANFALERFO</h3>
                            <div class="menu-price-details">LAGER 4,9% Alc vol</div>
                            <div class="menu-price-price">€ 6,00 media<br>€ 4,50 piccola</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="vc_row wpb_row vc_row-fluid">
            <div class="wpb_column vc_column_container vc_col-sm-1/5">
                <div class="vc_tta-container" data-vc-action="collapseAll">
                    <h2>DA SCARTARE</h2>
                </div>
            </div>
        </div>
    </html>
    """

    # Finto oggetto requests.Response
    mock_response = MagicMock()
    mock_response.text = mock_html

    # Intercetta requests.get prima che esca dal computer
    with patch("core.scraper.requests.get", return_value=mock_response) as mock_get:
        target_url = "https://consorziobirre.com/menu-consorzio-pub/test"
        result = scraper_obj.parse_menu(target_url)

        # Verifica che sia avvenuto quanto previsto
        mock_get.assert_called_once_with(target_url, timeout=10)

        # Verifica strutturale
        assert "BEVI BENE" in result
        assert "DA SCARTARE" not in result
        assert "BIRRE ALLA SPINA" in result["BEVI BENE"]

        assert len(result["BEVI BENE"]["BIRRE ALLA SPINA"]) == 1
        assert result["BEVI BENE"]["BIRRE ALLA SPINA"][0] == {
            "name1": "SANFALERFO",
            "name2": "LAGER 4,9% Alc vol",
            "price": "€ 6,00 media € 4,50 piccola",
        }


# I/O
def test_save_json(scraper_obj: Scraper, tmp_path: Path) -> None:
    """
    Verifica che `save_json` scriva correttamente i dati sia in history che
    che nel file globale unico 'menu_updated.json'.
    """

    mock_menu = {
        "MANGIA BENE": {
            "NACHOS": [
                {
                    "name1": "Nachos TIPICOS",
                    "name2": "con Formaggella artigianale fusa (allergeni: 7)",
                    "price": "€ 11.50",
                }
            ]
        }
    }

    fake_menu_output = tmp_path / "menu_updated.json"
    with patch("core.scraper.MENU_JSON", fake_menu_output):
        scraper_obj.save_json(mock_menu)

        # Entrambi i file devono esistere
        assert scraper_obj.output_file.exists()
        assert fake_menu_output.exists()

        # Il contenuto salvato deve essere un JSON valido
        # e identico a quello di partenza
        for file in (scraper_obj.output_file, fake_menu_output):
            with open(file, "r", encoding="utf-8") as f:
                assert json.load(f) == mock_menu
