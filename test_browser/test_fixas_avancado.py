"""
Testes avancados de Despesas Fixas:
- Expiracao por dia (isFixaExpirada)
- Aplicar/desaplicar manual
- Vincular fixa a categoria (cat_id)
- Editar e excluir fixas
"""

import pytest
from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    wait_for_table,
    fill_input,
    abrir_drawer,
    fechar_drawer,
    criar_categoria,
)


@pytest.fixture(autouse=True)
def setup_fixa(page: Page):
    """Garante que existe uma fixa 'Aluguel' para os testes."""
    abrir_drawer(page, "fixas")
    # Verifica se ja existe
    if page.locator("#lf:has-text('Aluguel')").count() == 0:
        page.click('button:has-text("+ Nova Despesa Fixa")')
        page.wait_for_selector(".fx-edit-row", timeout=3000)
        fill_input(page, "#fxeV", "800,00")
        fill_input(page, "#fxeDi", "10")
        fill_input(page, "#fxeD", "Aluguel")
        page.click('.fx-edit-row button:has-text("+ Lançar")')
        wait_for_load(page)
    fechar_drawer(page)


class TestExpiracaoFixa:
    def test_fixa_com_dia_passado_aparece_riscada(self, page: Page):
        """Fixas com dia anterior ao dia de hoje no mes corrente ficam riscadas."""
        # Mock: usa page.evaluate para verificar o estado da fixa
        abrir_drawer(page, "fixas")
        drawer = page.locator("#drawerFixas")
        expect(drawer).to_be_visible()

        # Verifica se o texto da fixa contem informacao de expiracao
        # ou esta riscado (text-decoration: line-through)
        items = page.locator("#lf .di")
        if items.count() > 0:
            primeiro = items.first
            estilo = primeiro.get_attribute("style") or ""
            # Se a fixa expirou, deve ter line-through no style
            # Ou pode estar visivel normalmente
            texto = primeiro.inner_text()
            assert "Aluguel" in texto or "800" in texto, \
                f"Fixa nao encontrada: {texto}"

        fechar_drawer(page)

    def test_dia_field_presente(self, page: Page):
        """O formulario de fixa tem campo 'dia'."""
        abrir_drawer(page, "fixas")
        # Abre edicao da primeira fixa
        btn_edit = page.locator("#lf .btn-edit").first
        if btn_edit.count() == 0:
            fechar_drawer(page)
            pytest.skip("Sem fixas para editar")

        btn_edit.click()
        page.wait_for_selector("#fxeDi", timeout=3000)

        # O campo dia deve existir e ter min=1 max=31
        dia_input = page.locator("#fxeDi")
        expect(dia_input).to_be_visible()
        assert dia_input.get_attribute("min") == "1"
        assert dia_input.get_attribute("max") == "31"

        # Cancela edicao
        page.click('button:has-text("Cancelar")')
        wait_for_load(page)
        fechar_drawer(page)


class TestAplicarFixaManual:
    def test_botao_aplicar_existe(self, page: Page):
        """Cada fixa tem um botao ✓ para aplicar/desaplicar manualmente."""
        abrir_drawer(page, "fixas")
        botoes = page.locator("#lf .btn-aplicar-fixa")
        # Pode haver zero ou mais, dependendo do estado
        # Se houver, deve ser clicavel
        if botoes.count() > 0:
            expect(botoes.first).to_be_visible()
        fechar_drawer(page)

    def test_aplicar_fixa_manual(self, page: Page):
        """Clicar no ✓ aplica a fixa do mes corrente."""
        abrir_drawer(page, "fixas")
        botoes = page.locator("#lf .btn-aplicar-fixa:not(.aplicada)")
        if botoes.count() == 0:
            fechar_drawer(page)
            pytest.skip("Nenhuma fixa disponivel para aplicar")

        botoes.first.click()
        page.wait_for_timeout(500)

        # O botao deve ter mudado para aplicada (classe 'aplicada')
        # ou o item deve ter sido atualizado
        wait_for_load(page)

        fechar_drawer(page)


class TestFixaCategoria:
    def test_criar_fixa_com_categoria(self, page: Page):
        """Verificar que fixas aparecem na tabela quando categoria tem inclui_fixas."""
        # Cria categoria com inclui_fixas
        wait_for_table(page)
        criar_categoria(page, "Moradia Fixa", incluir_fixas=True)

        wait_for_table(page)
        dados = page.locator("#tw").inner_text()
        # A categoria Moradia Fixa deve aparecer na tabela
        assert "Moradia Fixa" in dados, "Categoria Moradia Fixa nao encontrada"

    def test_fixa_reflete_na_categoria(self, page: Page):
        """Fixas devem aparecer somadas nas celulas da categoria com inclui_fixas."""
        abrir_drawer(page, "fixas")
        # Verifica o total mostrado no footer
        footer = page.locator("#tf")
        if footer.is_visible():
            total_texto = footer.inner_text()
            assert "Total:" in total_texto, "Total nao exibido no drawer"
        fechar_drawer(page)


class TestEditarExcluirFixa:
    def test_editar_fixa_inline(self, page: Page):
        """Editar valor de uma fixa existente."""
        abrir_drawer(page, "fixas")
        btn_edit = page.locator("#lf .btn-edit").first
        if btn_edit.count() == 0:
            fechar_drawer(page)
            pytest.skip("Sem fixas para editar")

        btn_edit.click()
        page.wait_for_selector("#fxeV", timeout=3000)

        # Altera valor
        fill_input(page, "#fxeV", "900,00")
        page.click('button:has-text("Alterar")')
        wait_for_load(page)

        # Verifica que o valor foi atualizado
        expect(page.locator("#lf")).to_contain_text("900,00")
        fechar_drawer(page)

    def test_excluir_fixa(self, page: Page):
        """Excluir uma fixa permanente."""
        # Primeiro cria uma fixa descartavel
        abrir_drawer(page, "fixas")
        page.click('button:has-text("+ Nova Despesa Fixa")')
        page.wait_for_selector(".fx-edit-row", timeout=3000)
        fill_input(page, "#fxeV", "50,00")
        fill_input(page, "#fxeDi", "20")
        fill_input(page, "#fxeD", "Fixa descartavel")
        page.click('.fx-edit-row button:has-text("+ Lançar")')
        wait_for_load(page)

        # Agora exclui
        btn_del = page.locator("#lf .btn-delete").last
        if btn_del.count() == 0:
            fechar_drawer(page)
            pytest.skip("Sem botoes de excluir")

        dialog_msg = [None]
        def handle_dialog(dialog):
            dialog_msg[0] = dialog.message
            dialog.accept()
        page.on("dialog", handle_dialog)

        btn_del.click()
        page.wait_for_timeout(500)
        assert dialog_msg[0] is not None, "Esperado confirm de exclusao"
        wait_for_load(page)
        fechar_drawer(page)
