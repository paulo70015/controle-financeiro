"""
Testes de CRUD de Despesas: criacao, edicao, exclusao e lote.
"""

import pytest
from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    wait_for_table,
    fill_input,
    select_option,
    criar_categoria,
    criar_despesa,
    get_table_data,
    modal_should_be_visible,
    modal_should_be_hidden,
)


@pytest.fixture(autouse=True)
def setup_categoria(page: Page):
    dados = get_table_data(page)
    tem_cat = any("Alimentacao" in (row[0] or "") for row in dados)
    if not tem_cat:
        criar_categoria(page, "Alimentacao")


class TestCriarDespesa:
    def test_abrir_modal_despesa(self, page: Page):
        page.click('button:has-text("+ Despesa")')
        modal_should_be_visible(page, "ovD")

    def test_fechar_modal_despesa_cancelar(self, page: Page):
        page.click('button:has-text("+ Despesa")')
        page.wait_for_selector("#ovD.show")
        page.click("#ovD button:has-text('Cancelar')")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovD")

    def test_criar_despesa_simples(self, page: Page):
        criar_despesa(page, "Alimentacao", 1, "150,00", "Supermercado")
        wait_for_table(page)
        dados = get_table_data(page)
        assert any("Alimentacao" in (row[0] or "") for row in dados), \
            "Categoria Alimentacao nao encontrada"

    def test_criar_despesa_cartao(self, page: Page):
        page.click('button:has-text("+ Despesa")')
        page.wait_for_selector("#ovD.show")
        select_option(page, "#dC", "Alimentacao")
        select_option(page, "#dM", "2")
        fill_input(page, "#dV", "200,00")
        fill_input(page, "#dN", "Cartao credito")
        page.check("#dIgnorar")
        page.click("#ovD button:has-text('Salvar')")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovD")

    def test_validacao_campos_obrigatorios(self, page: Page):
        page.click('button:has-text("+ Despesa")')
        page.wait_for_selector("#ovD.show")
        select_option(page, "#dC", "Alimentacao")
        select_option(page, "#dM", "1")
        # Nao preenche valor nem nota

        dialog_msg = [None]

        def handle_dialog(dialog):
            dialog_msg[0] = dialog.message
            dialog.accept()

        page.on("dialog", handle_dialog)
        page.click("#ovD button:has-text('Salvar')")
        page.wait_for_timeout(500)
        assert dialog_msg[0] is not None, "Esperado alerta de validacao"
        assert "valor" in dialog_msg[0].lower() or "nota" in dialog_msg[0].lower()


class TestEditarDespesa:
    def test_abrir_detalhe_clicando_celula(self, page: Page):
        criar_despesa(page, "Alimentacao", 3, "300,00", "Teste edicao")
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_indice(dados, "Alimentacao")
        assert linha_idx is not None
        page.click(f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(4)")
        page.wait_for_selector("#ovDet.show", timeout=3000)
        modal_should_be_visible(page, "ovDet")

    def test_editar_valor_despesa(self, page: Page):
        criar_despesa(page, "Alimentacao", 4, "100,00", "Antes edicao")
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_indice(dados, "Alimentacao")
        assert linha_idx is not None
        page.click(f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(5)")
        page.wait_for_selector("#ovDet.show", timeout=3000)
        fill_input(page, "#aV", "250,00")
        page.click('button:has-text("Salvar e fechar")')
        wait_for_load(page)
        modal_should_be_hidden(page, "ovDet")


class TestExcluirDespesa:
    def test_excluir_despesa_modal(self, page: Page):
        criar_despesa(page, "Alimentacao", 5, "50,00", "Para excluir")
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_indice(dados, "Alimentacao")
        assert linha_idx is not None
        page.click(f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(6)")
        page.wait_for_selector("#ovDet.show", timeout=3000)
        botoes_del = page.locator("#ovDet button[onclick^='delD']")
        if botoes_del.count() > 0:
            botoes_del.first.click()
            page.wait_for_timeout(300)
        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)
        modal_should_be_hidden(page, "ovDet")


class TestLoteLancamentos:
    def test_abrir_modal_lote(self, page: Page):
        # Garante que existe categoria para o kebab aparecer
        criar_categoria(page, "LoteTestCat")
        wait_for_table(page)

        # Abre o kebab menu da categoria (o link fica dentro do dropdown)
        kebabs = page.locator("#tw .btn-kebab")
        assert kebabs.count() > 0, "Nenhum menu kebab encontrado"
        kebabs.first.click(force=True)
        page.wait_for_selector(".dropdown-content.show", timeout=3000)

        link_lote = page.locator(".dropdown-content.show a:has-text('Lançar todos os meses')")
        assert link_lote.count() > 0, "Link de lote nao disponivel"
        link_lote.first.click(force=True)
        page.wait_for_selector("#ovLote.show", timeout=3000)
        modal_should_be_visible(page, "ovLote")

    def test_criar_lote_despesas(self, page: Page):
        criar_categoria(page, "LoteTestCat2")
        wait_for_table(page)

        kebabs = page.locator("#tw .btn-kebab")
        assert kebabs.count() > 0, "Nenhum menu kebab encontrado"
        kebabs.first.click(force=True)
        page.wait_for_selector(".dropdown-content.show", timeout=3000)

        link_lote = page.locator(".dropdown-content.show a:has-text('Lançar todos os meses')")
        assert link_lote.count() > 0, "Link de lote nao disponivel"
        link_lote.first.click(force=True)
        page.wait_for_selector("#ovLote.show", timeout=3000)
        fill_input(page, "#ltV", "100,00")
        fill_input(page, "#ltN", "Lote teste")
        page.wait_for_selector("#ltPreview[style*='block']", timeout=3000)
        page.click('#ovLote button:has-text("Salvar Lote")')
        wait_for_load(page)
        modal_should_be_hidden(page, "ovLote")


def _encontrar_indice(dados, nome):
    for i, row in enumerate(dados):
        if row and nome in (row[0] or ""):
            return i
    return None
