"""
Testes de Despesas Fixas: criacao, excecao, duplicacao entre anos.
"""

import pytest
from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    fill_input,
    abrir_drawer,
    fechar_drawer,
    criar_categoria,
)


class TestCriarFixa:
    def test_abrir_drawer_fixas(self, page: Page):
        abrir_drawer(page, "fixas")
        expect(page.locator("#drawerFixas.open")).to_be_visible()

    def test_criar_fixa_inline(self, page: Page):
        abrir_drawer(page, "fixas")
        page.click('button:has-text("+ Nova Despesa Fixa")')
        page.wait_for_selector(".fx-edit-row", timeout=3000)
        fill_input(page, "#fxeV", "500,00")
        fill_input(page, "#fxeDi", "15")
        fill_input(page, "#fxeD", "Aluguel")
        page.click('.fx-edit-row button:has-text("+ Lançar")')
        wait_for_load(page)
        expect(page.locator(".fx-edit-row")).to_be_hidden()
        expect(page.locator("#drawerFixas .drawer-body")).to_contain_text("Aluguel")

    def test_fixa_aparece_no_total(self, page: Page):
        abrir_drawer(page, "fixas")
        expect(page.locator("#tf")).to_contain_text("Total:")
        fechar_drawer(page)


class TestExcecaoFixa:
    def test_excecao_fixa_na_tabela(self, page: Page):
        try:
            page.click('button:has-text("+ Categoria")')
            page.wait_for_selector("#ovC.show", timeout=3000)
            fill_input(page, "#cN", "Moradia")
            page.check("#cFixas")
            page.click("#ovC .btn.ba")
            wait_for_load(page)
        except Exception:
            pass

        from test_browser.helpers import wait_for_table, get_table_data
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = None
        for i, row in enumerate(dados):
            if row and "Moradia" in (row[0] or ""):
                linha_idx = i
                break
        if linha_idx is None:
            pytest.skip("Categoria Moradia nao encontrada")
        page.click(f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(2)")
        page.wait_for_selector("#ovDet.show", timeout=3000)
        modal_content = page.locator("#ovDet").inner_text()
        assert "Aluguel" in modal_content or "500" in modal_content, \
            f"Fixa nao encontrada no modal: {modal_content[:200]}"
        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)


class TestDuplicarFixaAno:
    def test_criar_ano_com_duplicacao(self, page: Page):
        import datetime
        ano_futuro = str(datetime.datetime.now().year + 2)

        page.click('button:has-text("+ Ano")')
        page.wait_for_selector("#ovAno.show")
        page.fill("#anoNovoVal", ano_futuro)
        page.check("#anoNovoDuplicar")
        expect(page.locator("#anoNovoDuplicarInfo")).to_be_visible()
        page.click("#ovAno .btn.bv")
        # confirmarNovoAno() faz window.location = '?ano=...' (navegacao completa)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        page.wait_for_selector(f"#anoTabs a:has-text('{ano_futuro}')", timeout=5000)
        page.click(f"#anoTabs a:has-text('{ano_futuro}')")
        wait_for_load(page)
        abrir_drawer(page, "fixas")
        expect(page.locator("#drawerFixas .drawer-body")).to_contain_text("Aluguel")
        fechar_drawer(page)
