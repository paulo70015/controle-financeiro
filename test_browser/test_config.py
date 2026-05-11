"""
Testes de Configuracoes: tema escuro, linhas visiveis, dia inicio mes fiscal.
"""

from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    fill_input,
    modal_should_be_visible,
    modal_should_be_hidden,
)


class TestTemaEscuro:
    def test_abrir_config(self, page: Page):
        page.click("button.btn-cfg")
        page.wait_for_selector("#ovCfgApp.show", timeout=3000)
        modal_should_be_visible(page, "ovCfgApp")

    def test_ativar_dark_mode(self, page: Page):
        page.click("button.btn-cfg")
        page.wait_for_selector("#ovCfgApp.show", timeout=3000)

        # Verifica estado atual
        tema_checkbox = page.locator("#cfgTema")
        estava_escuro = tema_checkbox.is_checked()

        # Alterna
        tema_checkbox.click()

        # Salva
        page.click("#ovCfgApp button:has-text('Salvar')")  # Salvar config
        wait_for_load(page)

        # Verifica classe no html
        html = page.locator("html")
        if not estava_escuro:
            # Deveria ter ativado dark mode
            classe = html.get_attribute("class") or ""
            assert "dark-mode" in classe, "dark-mode nao foi ativado"
        else:
            # Deveria ter desativado
            classe = html.get_attribute("class") or ""
            assert "dark-mode" not in classe, "dark-mode nao foi desativado"

    def test_desativar_dark_mode(self, page: Page):
        """Garante que dark mode fica desativado ao final."""
        page.click("button.btn-cfg")
        page.wait_for_selector("#ovCfgApp.show", timeout=3000)

        tema_checkbox = page.locator("#cfgTema")
        if tema_checkbox.is_checked():
            tema_checkbox.click()
            page.click("#ovCfgApp button:has-text('Salvar')")
            wait_for_load(page)

        html = page.locator("html")
        classe = html.get_attribute("class") or ""
        assert "dark-mode" not in classe, "dark-mode nao foi desativado"


class TestLinhasVisiveis:
    def test_alterar_linhas(self, page: Page):
        page.click("button.btn-cfg")
        page.wait_for_selector("#ovCfgApp.show", timeout=3000)

        linhas_input = page.locator("#cfgLinhas")
        expect(linhas_input).to_be_visible()

        # Altera para 20
        fill_input(page, "#cfgLinhas", "20")
        page.click("#ovCfgApp button:has-text('Salvar')")
        wait_for_load(page)

        # Nao quebrou = sucesso
        from test_browser.helpers import wait_for_table
        wait_for_table(page)

    def test_linhas_valor_invalido(self, page: Page):
        """Tentar salvar com valor < 1 mostra alerta."""
        page.click("button.btn-cfg")
        page.wait_for_selector("#ovCfgApp.show", timeout=3000)

        fill_input(page, "#cfgLinhas", "0")

        dialog_msg = [None]
        def handle_dialog(dialog):
            dialog_msg[0] = dialog.message
            dialog.accept()
        page.on("dialog", handle_dialog)

        page.click("#ovCfgApp button:has-text('Salvar')")
        page.wait_for_timeout(500)
        assert dialog_msg[0] is not None, "Esperado alerta de validacao"


class TestDiaInicioMesFiscal:
    def test_alterar_dia_fiscal(self, page: Page):
        page.click("button.btn-cfg")
        page.wait_for_selector("#ovCfgApp.show", timeout=3000)

        dia_input = page.locator("#cfgDiaInicioMesFiscal")
        expect(dia_input).to_be_visible()

        fill_input(page, "#cfgDiaInicioMesFiscal", "20")
        page.click("#ovCfgApp button:has-text('Salvar')")
        wait_for_load(page)

        # O drawer de fixas deve refletir a alteracao
        from test_browser.helpers import abrir_drawer, fechar_drawer
        abrir_drawer(page, "fixas")
        info_fiscal = page.locator("#mesFiscalInfo")
        if info_fiscal.is_visible():
            texto = info_fiscal.inner_text()
            # A UI pode mostrar "Competência" (com acento) ou "Competencia"
            assert "compet" in texto.lower(), f"Info fiscal nao reconhecida: {texto}"
        fechar_drawer(page)

    def test_dia_fiscal_fora_range(self, page: Page):
        """Dia > 31 ou < 1 deve mostrar alerta."""
        page.click("button.btn-cfg")
        page.wait_for_selector("#ovCfgApp.show", timeout=3000)

        fill_input(page, "#cfgDiaInicioMesFiscal", "32")

        dialog_msg = [None]
        def handle_dialog(dialog):
            dialog_msg[0] = dialog.message
            dialog.accept()
        page.on("dialog", handle_dialog)

        page.click("#ovCfgApp button:has-text('Salvar')")
        page.wait_for_timeout(500)
        assert dialog_msg[0] is not None, "Esperado alerta de validacao"
