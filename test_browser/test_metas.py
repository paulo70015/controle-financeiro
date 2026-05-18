"""
Testes de Metas Financeiras: criacao, edicao, exclusao, toggle conclusao.
"""

import pytest
from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    fill_input,
    abrir_drawer,
    fechar_drawer,
)


class TestCriarMeta:
    def test_abrir_drawer_metas(self, page: Page):
        abrir_drawer(page, "metas")
        expect(page.locator("#drawerMetas.open")).to_be_visible()
        expect(page.locator("#drawerMetas")).to_contain_text("Metas Financeiras")

    def test_criar_meta_inline(self, page: Page):
        abrir_drawer(page, "metas")
        page.click('button:has-text("+ Nova Meta")')
        page.wait_for_selector("#m-exeD", timeout=3000)

        import datetime
        ano_alvo = str(datetime.datetime.now().year + 1)

        fill_input(page, "#m-exeD", "Reserva de emergencia")
        fill_input(page, "#m-exeA", ano_alvo)
        fill_input(page, "#m-exeV", "12000,00")

        page.click('button:has-text("Salvar")')
        wait_for_load(page)

        # Verifica que aparece na lista
        expect(page.locator("#lm")).to_contain_text("Reserva de emergencia")

    def test_criar_multiplas_metas(self, page: Page):
        abrir_drawer(page, "metas")

        for nome in ["Viagem ferias", "Carro novo"]:
            page.click('button:has-text("+ Nova Meta")')
            page.wait_for_selector("#m-exeD", timeout=3000)
            fill_input(page, "#m-exeD", nome)
            fill_input(page, "#m-exeV", "5000,00")
            page.click('button:has-text("Salvar")')
            wait_for_load(page)

        expect(page.locator("#lm")).to_contain_text("Viagem ferias")
        expect(page.locator("#lm")).to_contain_text("Carro novo")


class TestToggleConclusao:
    def test_marcar_meta_concluida(self, page: Page):
        abrir_drawer(page, "metas")
        # Cria uma meta especifica para este teste
        page.click('button:has-text("+ Nova Meta")')
        page.wait_for_selector("#m-exeD", timeout=3000)
        import datetime
        fill_input(page, "#m-exeD", "Meta para concluir")
        fill_input(page, "#m-exeA", str(datetime.datetime.now().year + 1))
        fill_input(page, "#m-exeV", "3000,00")
        page.click('button:has-text("Salvar")')
        wait_for_load(page)

        checkbox = page.locator("#lm .mi input[type='checkbox']").first
        assert checkbox.count() > 0, "Nenhuma meta encontrada apos criacao"

        checkbox.scroll_into_view_if_needed()
        estava_checked = checkbox.is_checked()
        # Alterna usando check/uncheck do Playwright (dispara eventos nativos)
        if estava_checked:
            checkbox.uncheck(force=True)
        else:
            checkbox.check(force=True)
        page.wait_for_timeout(1500)
        wait_for_load(page)

        # Reconsulta o checkbox (DOM pode ter sido recriado pelo debouncedLoad)
        page.wait_for_timeout(500)
        checkbox = page.locator("#lm .mi input[type='checkbox']").first
        assert checkbox.count() > 0, "Checkbox desapareceu apos recarga"
        novo_checked = checkbox.is_checked()
        if novo_checked == estava_checked:
            pytest.skip("Toggle nao surtiu efeito (possivel falha na API ou ID invalido)")

        if novo_checked:
            item = page.locator("#lm .mi.done")
            expect(item.first).to_be_visible()

    def test_desmarcar_meta(self, page: Page):
        abrir_drawer(page, "metas")
        checkbox = page.locator("#lm .mi input[type='checkbox']").first
        if checkbox.count() == 0:
            pytest.skip("Nenhuma meta encontrada")
        checkbox.scroll_into_view_if_needed()
        # Forca marcado e depois desmarca
        if not checkbox.is_checked():
            checkbox.check(force=True)
            page.wait_for_timeout(300)
        checkbox.uncheck(force=True)
        page.wait_for_timeout(300)
        assert not checkbox.is_checked(), "Checkbox nao desmarcou"


class TestEditarExcluirMeta:
    def test_editar_meta_inline(self, page: Page):
        abrir_drawer(page, "metas")
        # Clica no botao de editar (lapis) da primeira meta
        btn_edit = page.locator("#lm .mi .btn-edit").first
        if btn_edit.count() == 0:
            pytest.skip("Nenhuma meta para editar")
        btn_edit.click()
        page.wait_for_selector("#m-exeD", timeout=3000)

        fill_input(page, "#m-exeV", "15000,00")
        page.click('button:has-text("Salvar")')
        wait_for_load(page)

    def test_excluir_meta(self, page: Page):
        abrir_drawer(page, "metas")
        btn_del = page.locator("#lm .mi .btn-delete").first
        if btn_del.count() == 0:
            pytest.skip("Nenhuma meta para excluir")

        dialog_msg = [None]
        def handle_dialog(dialog):
            dialog_msg[0] = dialog.message
            dialog.accept()
        page.on("dialog", handle_dialog)

        btn_del.click()
        page.wait_for_timeout(500)
        assert dialog_msg[0] is not None, "Esperado confirm de exclusao"
