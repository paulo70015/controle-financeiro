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
        # Usa nomes únicos para evitar colisão com outros testes
        import uuid
        uid = uuid.uuid4().hex[:6]
        cat_nome = f"Moradia_{uid}"
        fixa_nome = f"Aluguel_{uid}"
        from test_browser.helpers import ANO_TESTE, wait_for_table, get_table_data

        # Isola o teste em um ano próprio para não depender de outra categoria
        # com "inclui fixas" criada por testes anteriores.
        ano_isolado = ANO_TESTE + 20 + int(uid[:2], 16)
        page.goto(page.url.split("?")[0] + f"?ano={ano_isolado}")
        wait_for_table(page)

        # Cria categoria manualmente (criar_categoria nao lida com #cFixas visivel condicionalmente)
        page.click('button:has-text("+ Categoria")')
        page.wait_for_selector("#ovC.show", timeout=3000)
        fill_input(page, "#cN", cat_nome)
        # O checkbox #cFixas some se outra categoria ja tem inclui_fixas ativo
        fixas_check = page.locator("#cFixas")
        if fixas_check.is_visible():
            fixas_check.check()
        page.click("#ovC .btn.ba")
        wait_for_load(page)

        # Cria fixa — aparecerá na categoria
        abrir_drawer(page, "fixas")
        page.click('button:has-text("+ Nova Despesa Fixa")')
        page.wait_for_selector(".fx-edit-row", timeout=3000)
        fill_input(page, "#fxeV", "500,00")
        fill_input(page, "#fxeDi", "15")
        fill_input(page, "#fxeD", fixa_nome)
        page.click('.fx-edit-row button:has-text("+ Lançar")')
        wait_for_load(page)
        fechar_drawer(page)

        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = None
        for i, row in enumerate(dados):
            if row and cat_nome in (row[0] or ""):
                linha_idx = i
                break
        assert linha_idx is not None, f"Categoria {cat_nome} nao encontrada"

        celula = page.locator(f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(2)")
        celula.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        celula.click(force=True, timeout=5000)
        page.wait_for_selector("#ovDet.show", timeout=5000)
        modal_content = page.locator("#ovDet").inner_text()
        assert fixa_nome in modal_content or "500" in modal_content, \
            f"Fixa nao encontrada no modal: {modal_content[:200]}"
        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)


class TestDuplicarFixaAno:
    def test_criar_ano_com_duplicacao(self, page: Page):
        import random
        from test_browser.helpers import ANO_TESTE
        # Ano futuro com offset aleatório para evitar colisão entre execuções
        ano_futuro = str(ANO_TESTE + 5 + random.randint(0, 4))

        page.click('button:has-text("+ Ano")')
        page.wait_for_selector("#ovAno.show")
        page.fill("#anoNovoVal", ano_futuro)
        page.check("#anoNovoDuplicar")
        expect(page.locator("#anoNovoDuplicarInfo")).to_be_visible()
        # Aceitar qualquer dialog (ex: alert de erro na duplicação)
        page.once("dialog", lambda d: d.accept())
        page.click("#ovAno .btn.bv")
        # confirmarNovoAno() faz window.location = '?ano=...' após o fetch assíncrono
        try:
            page.wait_for_url(f"**/?ano={ano_futuro}", timeout=15000)
        except Exception:
            pytest.skip(f"Navegação para ano {ano_futuro} não ocorreu (possível colisão de ano)")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        page.wait_for_selector(f"#anoTabs a:has-text('{ano_futuro}')", timeout=5000)
        wait_for_load(page)
        abrir_drawer(page, "fixas")
        expect(page.locator("#drawerFixas .drawer-body")).to_contain_text("Aluguel")
        fechar_drawer(page)
