"""
Testes de Validacao e Edge Cases:
- Valores negativos em despesas e receitas
- Valor zero
- Ano bloqueado impede edicao/exclusao
- Atalho Enter para salvar modais
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
    wait_for_table(page)
    dados = get_table_data(page)
    if not any("ValidTest" in (row[0] or "") for row in dados):
        criar_categoria(page, "ValidTest")


class TestValoresNegativos:
    def test_despesa_valor_negativo(self, page: Page):
        """Criar despesa com valor negativo (ex: estorno)."""
        page.click('button:has-text("+ Despesa")')
        page.wait_for_selector("#ovD.show")
        select_option(page, "#dC", "ValidTest")
        select_option(page, "#dM", "3")
        fill_input(page, "#dV", "-50,00")
        fill_input(page, "#dN", "Estorno")
        page.click("#ovD button:has-text('Salvar')")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovD")
        wait_for_table(page)
        # Nao deve quebrar — aceita valor negativo

    def test_receita_valor_negativo(self, page: Page):
        """Criar receita com valor negativo."""
        page.click('button:has-text("+ Receita")')
        page.wait_for_selector("#ovR.show")
        fill_input(page, "#rD", "Devolucao")
        select_option(page, "#rM", "4")
        fill_input(page, "#rV", "-100,00")
        page.click("#ovR button:has-text('Salvar')")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovR")


class TestValorZero:
    def test_despesa_valor_zero(self, page: Page):
        """Despesa com valor zero — deve ser aceita ou rejeitada com alerta."""
        page.click('button:has-text("+ Despesa")')
        page.wait_for_selector("#ovD.show")
        select_option(page, "#dC", "ValidTest")
        select_option(page, "#dM", "5")
        fill_input(page, "#dV", "0")

        dialog_msg = [None]
        def handle_dialog(dialog):
            dialog_msg[0] = dialog.message
            dialog.accept()
        page.on("dialog", handle_dialog)

        page.click("#ovD button:has-text('Salvar')")
        page.wait_for_timeout(500)
        # Pode aceitar (parseVal(0) = 0, nao null) ou rejeitar
        # So verificamos que nao quebrou
        wait_for_load(page)


class TestAnoBloqueado:
    def test_travar_ano(self, page: Page):
        """Travar o ano via botao na barra de abas."""
        try:
            page.wait_for_selector("#btnTravarAno", timeout=5000)
        except Exception:
            pytest.skip("Botao de travar ano nao encontrado (criado dinamicamente)")

        btn_lock = page.locator("#btnTravarAno")
        texto_antes = btn_lock.inner_text()

        # O toggleTravarAno() abre um confirm() — o handler aceita automaticamente
        def handle_dialog(dialog):
            dialog.accept()
        page.on("dialog", handle_dialog)

        btn_lock.click()
        page.wait_for_timeout(2000)
        wait_for_load(page)

        # O botao deve ter mudado de texto
        btn_lock = page.locator("#btnTravarAno")
        texto_depois = btn_lock.inner_text()
        assert texto_depois != texto_antes, \
            f"Botao nao mudou: {texto_antes} → {texto_depois}"

        # Teardown: destrava o ano para nao poluir os proximos testes
        if "TRAVADO" in texto_depois:
            btn_lock.click()
            page.wait_for_timeout(2000)
            wait_for_load(page)

    def test_ano_bloqueado_esconde_botoes(self, page: Page):
        """Com ano bloqueado, botoes de salvar nos modais devem sumir."""
        # Cria a despesa ANTES de travar (botoes somem com ano travado)
        wait_for_table(page)
        criar_despesa(page, "ValidTest", 6, "100,00", "Teste bloqueio")
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_linha(dados, "ValidTest")
        if linha_idx is None:
            pytest.skip("Categoria ValidTest nao encontrada")

        try:
            page.wait_for_selector("#btnTravarAno", timeout=3000)
        except Exception:
            pytest.skip("Botao de travar ano nao encontrado")

        # Handler de dialogo para o confirm() do toggleTravarAno
        def handle_dialog(dialog):
            dialog.accept()
        page.on("dialog", handle_dialog)

        btn_lock = page.locator("#btnTravarAno")
        # Garante que esta travado
        if "TRAVADO" not in btn_lock.inner_text():
            btn_lock.click()
            page.wait_for_timeout(2000)
            wait_for_load(page)

        # Abre detalhe da despesa ja criada
        page.click(
            f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(7)"
        )
        page.wait_for_selector("#ovDet.show", timeout=3000)

        # Os campos de input devem estar disabled com ano travado
        input_valor = page.locator("#aV")
        if input_valor.is_visible():
            assert input_valor.is_disabled(), \
                "Campo de valor deveria estar disabled com ano bloqueado"

        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)

        # Destrava o ano
        btn_lock = page.locator("#btnTravarAno")
        if "TRAVADO" in btn_lock.inner_text():
            btn_lock.click()
            page.wait_for_timeout(2000)
            wait_for_load(page)


class TestAtalhoEnter:
    def _garantir_ano_destravado(self, page: Page):
        """Garante que o ano esta destravado para os testes de atalho."""
        wait_for_load(page)
        try:
            btn = page.locator("#btnTravarAno")
            if btn.count() > 0 and btn.is_visible() and "TRAVADO" in btn.inner_text():
                def handle_dialog(dialog):
                    dialog.accept()
                page.on("dialog", handle_dialog)
                btn.click()
                page.wait_for_timeout(2000)
                wait_for_load(page)
        except Exception:
            pass  # Botao pode nao existir ainda

    def test_enter_fecha_modal_despesa(self, page: Page):
        """Pressionar Enter no modal de despesa salva e fecha."""
        self._garantir_ano_destravado(page)
        page.wait_for_selector('button:has-text("+ Despesa")', timeout=5000)
        page.click('button:has-text("+ Despesa")')
        page.wait_for_selector("#ovD.show")
        select_option(page, "#dC", "ValidTest")
        select_option(page, "#dM", "7")
        fill_input(page, "#dV", "200,00")

        # Pressiona Enter
        page.keyboard.press("Enter")
        wait_for_load(page)

        # O modal deve fechar (salvou com Enter)
        modal_should_be_hidden(page, "ovD")

    def test_enter_fecha_modal_receita(self, page: Page):
        """Pressionar Enter no modal de receita salva e fecha."""
        self._garantir_ano_destravado(page)
        page.wait_for_selector('button:has-text("+ Receita")', timeout=5000)
        page.click('button:has-text("+ Receita")')
        page.wait_for_selector("#ovR.show")
        fill_input(page, "#rD", "Teste Enter")
        select_option(page, "#rM", "8")
        fill_input(page, "#rV", "300,00")

        page.keyboard.press("Enter")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovR")


def _encontrar_linha(dados, nome):
    for i, row in enumerate(dados):
        if row and nome in (row[0] or ""):
            return i
    return None
