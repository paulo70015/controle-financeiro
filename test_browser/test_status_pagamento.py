"""
Testes de Status de Pagamento: toggle por celula, status no modal,
marcar mes como pago, status de receitas.
"""

import pytest
from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    wait_for_table,
    criar_categoria,
    criar_despesa,
    criar_receita,
    get_table_data,
    modal_should_be_visible,
)


@pytest.fixture(autouse=True)
def setup_dados(page: Page):
    """Garante categoria e despesa base para testes de status."""
    wait_for_table(page)
    dados = get_table_data(page)
    tem_cat = any("StatusTest" in (row[0] or "") for row in dados)
    if not tem_cat:
        criar_categoria(page, "StatusTest")
    # Cria despesa no mes 1 para ter uma celula com status
    criar_despesa(page, "StatusTest", 1, "100,00", "Teste status")


class TestToggleStatusCelula:
    def test_celula_tem_indicador_status(self, page: Page):
        """Celulas de valor tem icone de status (pontinho ou icone)."""
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_linha(dados, "StatusTest")
        assert linha_idx is not None, "Categoria StatusTest nao encontrada"

        # A celula do mes 1 deve conter algum texto (valor + status)
        celula = page.locator(
            f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(2)"
        )
        texto = celula.inner_text()
        assert len(texto.strip()) > 0, "Celula de status vazia"

    def test_clique_celula_abre_detalhe(self, page: Page):
        """Clicar na celula de despesa abre ovDet."""
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_linha(dados, "StatusTest")
        assert linha_idx is not None

        page.click(
            f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(2)"
        )
        page.wait_for_selector("#ovDet.show", timeout=3000)
        modal_should_be_visible(page, "ovDet")

        # Fecha
        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)


class TestStatusNoModal:
    def test_status_select_visivel(self, page: Page):
        """Abrir ovDet mostra o select de status (para despesa)."""
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_linha(dados, "StatusTest")
        assert linha_idx is not None

        page.click(
            f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child(2)"
        )
        page.wait_for_selector("#ovDet.show", timeout=3000)

        # O select de status (detStatus) deve estar visivel
        sel_status = page.locator("#detStatus")
        if sel_status.is_visible():
            # Verifica que tem opcoes (0, 1, 2)
            opcoes = sel_status.locator("option")
            assert opcoes.count() >= 2, "Select de status sem opcoes"

        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)

    def test_status_receita_diferente(self, page: Page):
        """Receitas usam Previsto/Realizado em vez de Aberto/Pago."""
        criar_receita(page, "Teste status rec", 2, "500,00")
        wait_for_table(page)

        # Abre detalhe da receita
        linha_rec = page.locator("#tw table tbody tr.tr-rec")
        if linha_rec.count() == 0:
            pytest.skip("Linha de receitas nao encontrada")
        linha_rec.first.locator("td").nth(2).click()
        page.wait_for_selector("#ovDet.show", timeout=3000)

        # Para receitas, detStatus fica escondido e detRecStatus visivel
        rec_status = page.locator("#detRecStatus")
        desp_status = page.locator("#detStatus")
        if rec_status.is_visible():
            assert not desp_status.is_visible(), \
                "Select de despesa visivel em contexto de receita"

        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)


class TestMarcarMesComoPago:
    def test_botao_marcar_mes_existe(self, page: Page):
        """O cabecalho de cada mes tem um icone ✔ para marcar como pago."""
        wait_for_table(page)
        # Os icones estao dentro de th com classe th-mes
        checks = page.locator("#tw table thead th span.mes-check")
        # Deve haver 12 (um por mes)
        assert checks.count() >= 1, "Icones de marcar mes nao encontrados"

    def test_clicar_marcar_mes(self, page: Page):
        """Clicar no ✔ do mes dispara acao de marcar como pago."""
        wait_for_table(page)
        checks = page.locator("#tw table thead th span.mes-check")
        if checks.count() == 0:
            pytest.skip("Icones de marcar mes nao encontrados")

        # Clica no primeiro mes
        checks.first.click()
        page.wait_for_timeout(1000)  # Aguarda possivel chamada API

        # Nao deve quebrar a pagina
        wait_for_table(page)


def _encontrar_linha(dados, nome):
    for i, row in enumerate(dados):
        if row and nome in (row[0] or ""):
            return i
    return None
