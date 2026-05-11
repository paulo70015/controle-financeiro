"""
Testes de Categorias: criacao e verificacao.
"""

from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    wait_for_table,
    fill_input,
    criar_categoria,
    get_table_data,
    modal_should_be_visible,
    modal_should_be_hidden,
)


class TestCriarCategoria:
    def test_abrir_modal_categoria(self, page: Page):
        page.click('button:has-text("+ Categoria")')
        modal_should_be_visible(page, "ovC")

    def test_fechar_modal_categoria(self, page: Page):
        page.click('button:has-text("+ Categoria")')
        page.wait_for_selector("#ovC.show")
        page.click("#ovC button:has-text('Cancelar')")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovC")

    def test_criar_categoria_simples(self, page: Page):
        criar_categoria(page, "Transporte")
        wait_for_table(page)
        dados = get_table_data(page)
        assert any("Transporte" in (row[0] or "") for row in dados)

    def test_criar_categoria_com_fixas(self, page: Page):
        page.click('button:has-text("+ Categoria")')
        page.wait_for_selector("#ovC.show")
        fill_input(page, "#cN", "Assinaturas")
        page.check("#cFixas")
        page.click("#ovC .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovC")
        wait_for_table(page)
        dados = get_table_data(page)
        assert any("Assinaturas" in (row[0] or "") for row in dados)

    def test_criar_multiplas_categorias(self, page: Page):
        for nome in ["Lazer", "Saude", "Educacao"]:
            criar_categoria(page, nome)
        wait_for_table(page)
        dados = get_table_data(page)
        for nome in ["Lazer", "Saude", "Educacao"]:
            assert any(nome in (row[0] or "") for row in dados), f"Faltou {nome}"


class TestReordenarCategoria:
    def test_categorias_sem_duplicatas(self, page: Page):
        wait_for_table(page)
        dados = get_table_data(page)
        nomes = [row[0].strip() for row in dados if row and row[0].strip()]
        assert len(nomes) > 0
        assert len(nomes) == len(set(nomes)), f"Duplicatas: {nomes}"
