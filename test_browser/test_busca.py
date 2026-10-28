"""
Testes E2E da funcionalidade Buscar (campo de busca com lupa, dropdown overflow,
regra de > 5 caracteres automático vs <= 5 manual, e destaque na planilha + modal).
"""

from playwright.sync_api import Page, expect

from test_browser.helpers import (
    alternar_visao,
    criar_categoria,
    criar_despesa,
    fill_input,
    wait_for_load,
    wait_for_table,
)


class TestBuscaUnificada:
    def test_busca_curta_exige_clique_na_lupa(self, page: Page):
        wait_for_table(page)
        criar_categoria(page, "Transporte Busca")
        criar_despesa(page, "Transporte Busca", 4, "42,90", nota="Uber")

        input_busca = page.locator("#inputBusca")
        dropdown = page.locator("#dropdownBusca")

        # 4 caracteres (<= 5): nao deve abrir dropdown automaticamente
        fill_input(page, "#inputBusca", "Uber")
        page.wait_for_timeout(400)
        expect(dropdown).to_be_hidden()

        # Ao clicar na lupa (#btnExecutarBusca), a busca deve ser executada
        page.click("#btnExecutarBusca")
        expect(dropdown).to_be_visible()
        expect(dropdown.locator(".search-item")).to_contain_text(["Uber"])

    def test_busca_longa_automatica_e_destaque_modal(self, page: Page):
        wait_for_table(page)
        criar_categoria(page, "Mercado Busca")
        criar_despesa(page, "Mercado Busca", 6, "580,00", nota="Supermercado Extra")

        dropdown = page.locator("#dropdownBusca")

        # Mais de 5 caracteres ("Supermercado"): busca automatica ao digitar
        fill_input(page, "#inputBusca", "Supermercado")
        expect(dropdown).to_be_visible(timeout=3000)
        item = dropdown.locator(".search-item").first
        expect(item).to_contain_text("Mercado Busca")
        expect(item).to_contain_text("Supermercado Extra")

        # Clicar no resultado destaca a celula e abre o modal com o item destacado
        item.click()
        expect(dropdown).to_be_hidden()
        expect(page.locator("#ovDet.show")).to_be_visible()
        expect(page.locator("#detL .di.search-item-highlight")).to_be_visible()
        expect(page.locator("#tw td.search-highlight-pulse")).to_be_visible()

    def test_busca_alterna_visao_para_rendimentos(self, page: Page):
        wait_for_table(page)
        alternar_visao(page, "rendimentos")

        # Cria um local e lancamento de rendimento
        page.click('button:has-text("+ Local")')
        page.wait_for_selector("#ovRendLocal.show")
        fill_input(page, "#rendLocalNome", "Tesouro Busca")
        page.click("#ovRendLocal .btn.ba")
        wait_for_load(page)

        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show")
        fill_input(page, "#rendAddValor", "1500,00")
        fill_input(page, "#rendAddNota", "Aporte Semestral")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)

        # Volta para a visao de Despesas
        alternar_visao(page, "despesas")
        expect(page.locator("#viewTabDespesas")).to_have_class("view-tab ativo")

        # Pesquisa pelo lancamento de rendimento (> 5 caracteres -> automatico)
        fill_input(page, "#inputBusca", "Semestral")
        dropdown = page.locator("#dropdownBusca")
        expect(dropdown).to_be_visible(timeout=3000)
        item = dropdown.locator(".search-item").first
        expect(item).to_contain_text("Tesouro Busca")

        # Clica no item: deve alternar para Rendimentos, destacar celula e abrir modal
        item.click()
        expect(page.locator("#viewTabRendimentos")).to_have_class("view-tab ativo")
        expect(page.locator("#ovRendLanc.show")).to_be_visible()
        expect(page.locator("#rendLancLista .di.search-item-highlight")).to_be_visible()
        expect(page.locator("#tw td.search-highlight-pulse")).to_be_visible()
