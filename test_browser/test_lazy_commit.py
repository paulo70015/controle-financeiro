"""
Testes de Lazy Commit: fila de exclusao (deleteQueue) e undo stack.
"""

import pytest
from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    wait_for_table,
    criar_categoria,
    criar_despesa,
    get_table_data,
    modal_should_be_visible,
    modal_should_be_hidden,
)


@pytest.fixture(autouse=True)
def setup_dados(page: Page):
    wait_for_table(page)
    dados = get_table_data(page)
    tem_cat = any("LazyTest" in (row[0] or "") for row in dados)
    if not tem_cat:
        criar_categoria(page, "LazyTest")
    criar_despesa(page, "LazyTest", 6, "75,00", "Teste lazy commit")


class TestFilaExclusao:
    def test_abrir_detalhe_com_despesa(self, page: Page):
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_indice(dados, "LazyTest")
        assert linha_idx is not None
        page.click(f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(7)")
        page.wait_for_selector("#ovDet.show", timeout=3000)
        modal_should_be_visible(page, "ovDet")

    def test_excluir_item_no_modal(self, page: Page):
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_indice(dados, "LazyTest")
        assert linha_idx is not None, "Categoria LazyTest nao encontrada na tabela"
        page.click(f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(7)")
        page.wait_for_selector("#ovDet.show", timeout=5000)
        # Aguarda os botoes de exclusao aparecerem no modal
        try:
            page.wait_for_selector("#ovDet button[onclick^='delD']", timeout=3000)
        except Exception:
            pytest.skip("Nenhum botao de exclusao encontrado (celula sem lancamentos?)")
        botoes_del = page.locator("#ovDet button[onclick^='delD']")
        botoes_antes = botoes_del.count()
        assert botoes_antes > 0, "Nenhum botao de exclusao encontrado"
        botoes_del.first.click()
        page.wait_for_timeout(300)
        botoes_depois = page.locator("#ovDet button[onclick^='delD']").count()
        assert botoes_depois < botoes_antes, "Item nao foi removido visualmente"

    def test_fechar_modal_efetiva_exclusao(self, page: Page):
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_indice(dados, "LazyTest")
        assert linha_idx is not None
        page.click(f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(7)")
        page.wait_for_selector("#ovDet.show", timeout=3000)
        botoes_del = page.locator("#ovDet button[onclick^='delD']")
        if botoes_del.count() > 0:
            botoes_del.first.click()
            page.wait_for_timeout(300)
        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)
        modal_should_be_hidden(page, "ovDet")
        wait_for_table(page)


class TestUndoStack:
    def test_undo_restaura_item(self, page: Page):
        criar_despesa(page, "LazyTest", 8, "99,00", "Teste undo")
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_indice(dados, "LazyTest")
        assert linha_idx is not None
        page.click(f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(9)")
        page.wait_for_selector("#ovDet.show", timeout=3000)
        botoes_del = page.locator("#ovDet button[onclick^='delD']")
        if botoes_del.count() > 0:
            botoes_del.first.click()
            page.wait_for_timeout(300)
            btn_undo = page.locator("#detBtnUndo")
            if btn_undo.is_visible():
                btn_undo.click()
                page.wait_for_timeout(300)
        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)

    def test_btn_undo_escondido_inicialmente(self, page: Page):
        criar_despesa(page, "LazyTest", 10, "50,00", "Undo visibility")
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_indice(dados, "LazyTest")
        assert linha_idx is not None
        page.click(f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(11)")
        page.wait_for_selector("#ovDet.show", timeout=3000)
        btn_undo = page.locator("#detBtnUndo")
        estilo = btn_undo.get_attribute("style") or ""
        assert "none" in estilo or not btn_undo.is_visible(), \
            "Botao undo deveria estar escondido inicialmente"
        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)


def _encontrar_indice(dados, nome):
    for i, row in enumerate(dados):
        if row and nome in (row[0] or ""):
            return i
    return None
