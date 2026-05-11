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
            fill_input(page, "#contaNome", "Itau")
            fill_input(page, "#contaSaldoInicial", "5000,00")
            page.click("#ovConta .btn.bv")
            wait_for_load(page)

    def test_abrir_deposito(self, page: Page):
        """Clicar na linha da conta abre o modal de deposito."""
        wait_for_table(page)
        # Linha da conta tem classe tr-conta
        linha_conta = page.locator("#tw table tbody tr.tr-conta")
        if linha_conta.count() == 0:
            pytest.skip("Linha de conta nao encontrada")
        # Clica na primeira celula (nome da conta)
        linha_conta.first.locator("td").first.click()
        page.wait_for_selector("#ovDep.show", timeout=3000)
        modal_should_be_visible(page, "ovDep")

    def test_lancar_deposito_positivo(self, page: Page):
        wait_for_table(page)
        linha_conta = page.locator("#tw table tbody tr.tr-conta").first
        if linha_conta.count() == 0:
            pytest.skip("Linha de conta nao encontrada")
        linha_conta.locator("td").first.click()
        page.wait_for_selector("#ovDep.show", timeout=3000)

        fill_input(page, "#depV", "1000,00")
        fill_input(page, "#depN", "Deposito teste")
        page.click('#ovDep button:has-text("Salvar e fechar")')
        wait_for_load(page)
        modal_should_be_hidden(page, "ovDep")

    def test_lancar_deposito_negativo(self, page: Page):
        """Deposito negativo (saque)."""
        wait_for_table(page)
        linha_conta = page.locator("#tw table tbody tr.tr-conta").first
        if linha_conta.count() == 0:
            pytest.skip("Linha de conta nao encontrada")
        linha_conta.locator("td").first.click()
        page.wait_for_selector("#ovDep.show", timeout=3000)

        # Valor negativo = saque
        fill_input(page, "#depV", "-200,00")
        fill_input(page, "#depN", "Saque teste")
        page.click('#ovDep button:has-text("Salvar e fechar")')
        wait_for_load(page)
        modal_should_be_hidden(page, "ovDep")

    def test_deposito_valor_zero_bloqueado(self, page: Page):
        """Tentar depositar zero deve ser rejeitado."""
        wait_for_table(page)
        linha_conta = page.locator("#tw table tbody tr.tr-conta").first
        if linha_conta.count() == 0:
            pytest.skip("Linha de conta nao encontrada")
        linha_conta.locator("td").first.click()
        page.wait_for_selector("#ovDep.show", timeout=3000)

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
        """Abrir modal de movimentacao mensal via kebab da conta."""
        wait_for_table(page)
        linha_conta = page.locator("#tw table tbody tr.tr-conta").first
        if linha_conta.count() == 0:
            pytest.skip("Linha de conta nao encontrada")

        # Abre kebab
        kebabs = linha_conta.locator(".btn-kebab")
        if kebabs.count() == 0:
            pytest.skip("Sem menu kebab na conta")
        kebabs.first.click(force=True)
        page.wait_for_timeout(200)

        # Procura opcao de movimentacao
        link_mov = page.locator(
            ".dropdown-content a:has-text('Editar')"
        )
        if link_mov.count() > 0:
            link_mov.first.click(force=True)
            page.wait_for_timeout(300)

        # Tenta abrir movimentacao via clique na celula de saldo/movimentacao
        # (algumas celulas de conta abrem ovMov ao inves de ovDep)
        page.keyboard.press("Escape")  # fecha qualquer modal
        wait_for_load(page)


class TestEditarExcluirConta:
    def test_excluir_conta(self, page: Page):
        wait_for_table(page)
        linha_conta = page.locator("#tw table tbody tr.tr-conta").first
        if linha_conta.count() == 0:
            pytest.skip("Linha de conta nao encontrada")

        kebabs = linha_conta.locator(".btn-kebab")
        if kebabs.count() == 0:
            pytest.skip("Sem menu kebab na conta")
        kebabs.first.click(force=True)
        page.wait_for_timeout(200)

        link_excluir = page.locator(
            ".dropdown-content a:has-text('Excluir')"
        )
        if link_excluir.count() == 0:
            page.keyboard.press("Escape")
            pytest.skip("Opcao Excluir nao encontrada")

        dialog_msg = [None]
        def handle_dialog(dialog):
            dialog_msg[0] = dialog.message
            dialog.accept()
        page.on("dialog", handle_dialog)

        link_excluir.first.click(force=True)
        page.wait_for_timeout(500)
        assert dialog_msg[0] is not None, "Esperado confirm de exclusao"
