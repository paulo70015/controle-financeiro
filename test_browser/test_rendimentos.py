"""
Testes de Rendimentos: locais, aportes, projecao de taxa.
"""

import pytest
from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    wait_for_table,
    fill_input,
    select_option,
    alternar_visao,
    modal_should_be_visible,
    modal_should_be_hidden,
)


class TestRendimentosBasico:
    def test_alterna_para_rendimentos(self, page: Page):
        alternar_visao(page, "rendimentos")
        expect(page.locator("#acoesRendimentos")).to_be_visible()

    def test_criar_local_rendimento(self, page: Page):
        alternar_visao(page, "rendimentos")
        page.click('button:has-text("+ Local")')
        page.wait_for_selector("#ovRendLocal.show", timeout=3000)
        modal_should_be_visible(page, "ovRendLocal")
        fill_input(page, "#rendLocalNome", "Conta XPTO")
        page.click("#ovRendLocal .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendLocal")
        wait_for_table(page)
        page.wait_for_selector("text=Conta XPTO", timeout=3000)


class TestAdicionarAporte:
    @pytest.fixture(autouse=True)
    def setup_local(self, page: Page):
        alternar_visao(page, "rendimentos")
        if page.locator("text=Conta XPTO").count() == 0:
            page.click('button:has-text("+ Local")')
            page.wait_for_selector("#ovRendLocal.show", timeout=3000)
            fill_input(page, "#rendLocalNome", "Conta XPTO")
            page.click("#ovRendLocal .btn.ba")
            wait_for_load(page)
        alternar_visao(page, "rendimentos")

    def test_abrir_modal_lancamento(self, page: Page):
        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        modal_should_be_visible(page, "ovRendAdd")

    def test_adicionar_aporte(self, page: Page):
        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", "Conta XPTO")
        select_option(page, "#rendAddTipo", "aporte")
        select_option(page, "#rendAddMes", "1")
        fill_input(page, "#rendAddValor", "10000,00")
        fill_input(page, "#rendAddNota", "Aporte inicial")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)
        tabela_texto = page.locator("#tw").inner_text()
        assert "10.000" in tabela_texto or "10000" in tabela_texto

    def test_adicionar_rendimento(self, page: Page):
        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", "Conta XPTO")
        select_option(page, "#rendAddTipo", "rendimento")
        select_option(page, "#rendAddMes", "2")
        fill_input(page, "#rendAddValor", "500,00")
        fill_input(page, "#rendAddNota", "Rendimento Fev")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)


class TestProjecaoTaxa:
    def test_abrir_projecao(self, page: Page):
        alternar_visao(page, "rendimentos")
        kebabs = page.locator("#tw .btn-kebab")
        if kebabs.count() == 0:
            pytest.skip("Nenhum local com menu kebab")
        kebabs.first.click(force=True)
        page.wait_for_timeout(200)
        link_proj = page.locator(".dropdown-content a:has-text('Projetar rendimentos')")
        if link_proj.count() == 0:
            page.keyboard.press("Escape")
            pytest.skip("Opcao Projetar rendimentos nao encontrada")
        link_proj.first.click(force=True)
        page.wait_for_selector("#ovRendProj.show", timeout=3000)
        modal_should_be_visible(page, "ovRendProj")
        expect(page.locator("#rendProjPct")).to_be_visible()

    def test_projecao_preview_atualiza(self, page: Page):
        alternar_visao(page, "rendimentos")
        kebabs = page.locator("#tw .btn-kebab")
        if kebabs.count() == 0:
            pytest.skip("Nenhum local com menu kebab")
        kebabs.first.click(force=True)
        page.wait_for_timeout(200)
        link_proj = page.locator(".dropdown-content a:has-text('Projetar rendimentos')")
        if link_proj.count() == 0:
            page.keyboard.press("Escape")
            pytest.skip("Opcao nao encontrada")
        link_proj.first.click(force=True)
        page.wait_for_selector("#ovRendProj.show", timeout=3000)
        fill_input(page, "#rendProjPct", "1,50")
        page.wait_for_timeout(300)
        preview = page.locator("#rendProjPreview")
        expect(preview).to_be_visible()
        assert len(preview.inner_text()) > 10, "Preview vazio ou muito curto"
