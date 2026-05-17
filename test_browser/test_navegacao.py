"""
Testes de navegacao: carregamento, troca de ano, alternancia de visao, drawer.
"""

import pytest
from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    wait_for_table,
    alternar_visao,
    abrir_drawer,
    fechar_drawer,
)


class TestCarregaPagina:
    def test_titulo_pagina(self, page: Page):
        expect(page).to_have_title("Controle Financeiro v1.3.0")

    def test_header_visivel(self, page: Page):
        header = page.locator("header h1")
        expect(header).to_be_visible()
        expect(header).to_contain_text("Controle Financeiro")

    def test_tabela_renderizada(self, page: Page):
        wait_for_table(page)
        expect(page.locator("#tw table")).to_be_visible()

    def test_abas_visao_presentes(self, page: Page):
        tab_desp = page.locator("#viewTabDespesas")
        tab_rend = page.locator("#viewTabRendimentos")
        expect(tab_desp).to_be_visible()
        expect(tab_rend).to_be_visible()
        expect(tab_desp).to_have_class("view-tab ativo")

    def test_botoes_acao_visiveis(self, page: Page):
        acoes = page.locator("#acoesDespesas")
        expect(acoes).to_be_visible()
        expect(acoes).to_contain_text("Despesa")

    def test_versao_visivel(self, page: Page):
        expect(page.locator("span.versao")).to_contain_text("v1.3.0")


class TestTrocaAno:
    def test_abas_ano_existem(self, page: Page):
        tabs = page.locator("#anoTabs a")
        expect(tabs.first).to_be_visible()
        assert tabs.count() >= 1

    def test_aba_ano_atual_ativa(self, page: Page):
        expect(page.locator("#anoTabs a.ativo")).to_have_count(1)

    def test_criar_e_navegar_novo_ano(self, page: Page):
        import datetime, random

        # Usa offset aleatorio para evitar colisao com outros testes que criam anos
        ano_futuro = str(datetime.datetime.now().year + 2 + random.randint(0, 3))
        tabs_antes = page.locator("#anoTabs a").count()

        page.click('button:has-text("+ Ano")')
        page.wait_for_selector("#ovAno.show")
        page.fill("#anoNovoVal", ano_futuro)
        page.click("#ovAno .btn.bv")
        # Aguarda a navegacao (confirmarNovoAno faz window.location)
        try:
            page.wait_for_url(f"**/?ano={ano_futuro}", timeout=10000)
        except Exception:
            # Se a navegacao falhou (ex: alerta de erro), tenta fechar dialog e seguir
            pass
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)

        page.wait_for_selector(f"#anoTabs a:has-text('{ano_futuro}')", timeout=5000)
        assert page.locator("#anoTabs a").count() >= tabs_antes + 1

        aba_ativa = page.locator(f"#anoTabs a.ativo:has-text('{ano_futuro}')")
        expect(aba_ativa).to_be_visible()
        wait_for_table(page)

        # Volta ao ano corrente
        ano_atual = str(datetime.datetime.now().year)
        page.click(f"#anoTabs a:has-text('{ano_atual}')")
        wait_for_load(page)
        wait_for_table(page)


class TestAlternaVisao:
    def test_alterna_para_rendimentos(self, page: Page):
        alternar_visao(page, "rendimentos")
        expect(page.locator("#acoesRendimentos")).to_be_visible()
        expect(page.locator("#acoesDespesas")).to_be_hidden()

    def test_alterna_para_despesas(self, page: Page):
        alternar_visao(page, "rendimentos")
        alternar_visao(page, "despesas")
        expect(page.locator("#acoesDespesas")).to_be_visible()

    def test_titulo_abas_atualiza(self, page: Page):
        import datetime
        ano_str = str(datetime.datetime.now().year)
        expect(page.locator("#viewTabDespesas")).to_contain_text(ano_str)
        expect(page.locator("#viewTabRendimentos")).to_contain_text(ano_str)


class TestDrawerLateral:
    def test_abrir_drawer_fixas(self, page: Page):
        abrir_drawer(page, "fixas")
        expect(page.locator("#drawerFixas.open")).to_be_visible()

    def test_fechar_drawer(self, page: Page):
        abrir_drawer(page, "fixas")
        fechar_drawer(page)
        expect(page.locator("#drawerFixas.open")).to_be_hidden()

    def test_abrir_drawer_metas(self, page: Page):
        abrir_drawer(page, "metas")
        expect(page.locator("#drawerMetas.open")).to_be_visible()

    def test_alternar_drawer(self, page: Page):
        abrir_drawer(page, "fixas")
        page.click("#drawerOverlay.show")
        page.wait_for_timeout(300)
        page.click("#tabMetas")
        page.wait_for_selector("#drawerMetas.open", timeout=3000)
        expect(page.locator("#drawerFixas.open")).to_be_hidden()
        expect(page.locator("#drawerMetas.open")).to_be_visible()
