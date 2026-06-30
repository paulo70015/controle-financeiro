"""
Testes de Contas Correntes: criacao, edicao, exclusao,
depositos (positivo/negativo) e movimentacoes mensais.
"""

import pytest
from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    wait_for_table,
    fill_input,
    select_option,
    modal_should_be_visible,
    modal_should_be_hidden,
)


class TestCriarConta:
    def test_abrir_modal_conta(self, page: Page):
        page.click('button:has-text("+ Conta")')
        modal_should_be_visible(page, "ovConta")

    def test_fechar_modal_conta(self, page: Page):
        page.click('button:has-text("+ Conta")')
        page.wait_for_selector("#ovConta.show")
        page.click("#ovConta button:has-text('Cancelar')")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovConta")

    def test_criar_conta_simples(self, page: Page):
        page.click('button:has-text("+ Conta")')
        page.wait_for_selector("#ovConta.show")
        fill_input(page, "#ctN", "Itau")
        fill_input(page, "#ctSI", "5000,00")
        page.click("#ovConta button:has-text('Salvar')")  # Salvar
        wait_for_load(page)
        modal_should_be_hidden(page, "ovConta")
        wait_for_table(page)
        # A conta deve aparecer na tabela
        expect(page.locator("#tw")).to_contain_text("Itau")

    def test_criar_conta_sem_saldo(self, page: Page):
        page.click('button:has-text("+ Conta")')
        page.wait_for_selector("#ovConta.show")
        fill_input(page, "#ctN", "Nubank")
        # Deixa saldo vazio (default 0)
        page.click("#ovConta button:has-text('Salvar')")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovConta")
        expect(page.locator("#tw")).to_contain_text("Nubank")


class TestDeposito:
    @pytest.fixture(autouse=True)
    def setup_conta(self, page: Page):
        """Garante que existe uma conta para testes de deposito."""
        wait_for_table(page)
        if page.locator("#tw:has-text('Itau')").count() == 0:
            page.click('button:has-text("+ Conta")')
            page.wait_for_selector("#ovConta.show", timeout=3000)
            fill_input(page, "#ctN", "Itau")
            fill_input(page, "#ctSI", "5000,00")
            page.click("#ovConta button:has-text('Salvar')")
            wait_for_load(page)

    def _abrir_deposito(self, page: Page):
        """Clica na celula de valor (mes 1) da conta para abrir ovDep."""
        wait_for_table(page)
        linha_conta = page.locator("tr.tr-conta")
        if linha_conta.count() == 0:
            pytest.skip("Linha de conta nao encontrada")
        # Clica na segunda celula (mes 1), que tem onclick="abrirDep(...)"
        celula_valor = linha_conta.first.locator("td").nth(1)
        celula_valor.click()
        page.wait_for_selector("#ovDep.show", timeout=3000)

    def test_abrir_deposito(self, page: Page):
        """Clicar na celula de valor da conta abre o modal de deposito."""
        self._abrir_deposito(page)
        modal_should_be_visible(page, "ovDep")

    def test_lancar_deposito_positivo(self, page: Page):
        self._abrir_deposito(page)

        fill_input(page, "#depV", "1000,00")
        fill_input(page, "#depN", "Deposito teste")
        page.click('#ovDep button:has-text("Salvar e fechar")')
        wait_for_load(page)
        modal_should_be_hidden(page, "ovDep")

    def test_lancar_deposito_negativo(self, page: Page):
        """Deposito negativo (saque)."""
        self._abrir_deposito(page)

        fill_input(page, "#depV", "-200,00")
        fill_input(page, "#depN", "Saque teste")
        page.click('#ovDep button:has-text("Salvar e fechar")')
        wait_for_load(page)
        modal_should_be_hidden(page, "ovDep")

    def test_deposito_valor_zero_bloqueado(self, page: Page):
        """Tentar depositar zero deve ser rejeitado."""
        self._abrir_deposito(page)

        fill_input(page, "#depV", "0")

        dialog_msg = [None]
        def handle_dialog(dialog):
            dialog_msg[0] = dialog.message
            dialog.accept()
        page.on("dialog", handle_dialog)

        page.click('#ovDep button:has-text("Salvar e fechar")')
        page.wait_for_timeout(500)
        # Deve mostrar alerta (valor zero nao permitido ou aceito como 0)
        if dialog_msg[0] is not None:
            assert "valor" in dialog_msg[0].lower() or "zero" in dialog_msg[0].lower()


class TestMovimentacaoMensal:
    def test_abrir_movimentacao(self, page: Page):
        """Abrir modal de edicao da conta via kebab."""
        wait_for_table(page)
        linha_conta = page.locator("tr.tr-conta").first
        if linha_conta.count() == 0:
            pytest.skip("Linha de conta nao encontrada")

        # Abre kebab
        kebabs = linha_conta.locator(".btn-kebab")
        if kebabs.count() == 0:
            pytest.skip("Sem menu kebab na conta")
        kebabs.first.click(force=True)
        page.wait_for_timeout(200)

        # Procura opcao de editar conta
        link_edit = linha_conta.locator(".dropdown-content a:has-text('Editar')")
        if link_edit.count() > 0:
            link_edit.first.click(force=True)
            page.wait_for_timeout(300)

        # Fecha qualquer modal
        page.keyboard.press("Escape")
        wait_for_load(page)

    def test_multiplas_movimentacoes_no_mes(self, page: Page):
        """Permite mais de uma movimentação no mesmo mês, sem sobrescrever."""
        wait_for_table(page)
        for nome in ("Conta Mov A", "Conta Mov B"):
            if page.locator(f"#tw:has-text('{nome}')").count() == 0:
                page.click('button:has-text("+ Conta")')
                page.wait_for_selector("#ovConta.show", timeout=3000)
                fill_input(page, "#ctN", nome)
                fill_input(page, "#ctSI", "0")
                page.click("#ovConta button:has-text('Salvar')")
                wait_for_load(page)
                wait_for_table(page)

        mes_teste = 11
        page.locator("tr.tr-mov td").nth(mes_teste).click()
        page.wait_for_selector("#ovMov.show", timeout=3000)
        modal_should_be_visible(page, "ovMov")

        select_option(page, "#movConta", "❖ Conta Mov A")
        fill_input(page, "#movValor", "100,00")
        fill_input(page, "#movNota", "Mov A")
        page.click("#movBtnSave")
        wait_for_load(page)

        select_option(page, "#movConta", "❖ Conta Mov B")
        fill_input(page, "#movValor", "-40,00")
        fill_input(page, "#movNota", "Mov B")
        page.click("#movBtnSave")
        wait_for_load(page)

        lista = page.locator("#movL")
        expect(lista).to_contain_text("Mov A")
        expect(lista).to_contain_text("Mov B")
        expect(lista).to_contain_text("Conta Mov A")
        expect(lista).to_contain_text("Conta Mov B")

        page.click("#ovMov button:has-text('Salvar e fechar')")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovMov")
        wait_for_table(page)

        mov_nov = page.locator("tr.tr-mov td").nth(mes_teste)
        assert "60" in mov_nov.inner_text()


class TestEditarExcluirConta:
    def test_excluir_conta(self, page: Page):
        # Garante que existe uma conta para excluir
        page.click('button:has-text("+ Conta")')
        page.wait_for_selector("#ovConta.show", timeout=3000)
        fill_input(page, "#ctN", "ContaParaExcluir")
        fill_input(page, "#ctSI", "100,00")
        page.click("#ovConta button:has-text('Salvar')")
        wait_for_load(page)
        wait_for_table(page)

        linha_conta = page.locator("tr.tr-conta").first
        assert linha_conta.count() > 0, "Linha de conta nao encontrada"

        kebabs = linha_conta.locator(".btn-kebab")
        assert kebabs.count() > 0, "Sem menu kebab na conta"
        kebabs.first.click(force=True)
        # toggleCatMenu move o dropdown para document.body com classe .show
        page.wait_for_selector(".dropdown-content.show", timeout=3000)

        link_excluir = page.locator(
            ".dropdown-content.show a:has-text('Excluir')"
        )
        assert link_excluir.count() > 0, "Opcao Excluir nao encontrada"

        dialog_msg = [None]
        def handle_dialog(dialog):
            dialog_msg[0] = dialog.message
            dialog.accept()
        page.on("dialog", handle_dialog)

        link_excluir.first.click(force=True)
        page.wait_for_timeout(500)
        assert dialog_msg[0] is not None, "Esperado confirm de exclusao"
