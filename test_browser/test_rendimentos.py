"""
Testes de Rendimentos: locais, aportes, projecao de taxa.
"""

import datetime

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

    def test_adicionar_rendimento_negativo_fica_vermelho(self, page: Page):
        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", "Conta XPTO")
        select_option(page, "#rendAddTipo", "rendimento")
        select_option(page, "#rendAddMes", "3")
        fill_input(page, "#rendAddValor", "-25,00")
        fill_input(page, "#rendAddNota", "Rendimento negativo")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

        classes_rendimentos_mar = page.locator("#tw .tr-rend-rendimentos td").nth(3).get_attribute("class") or ""
        assert "neg" in classes_rendimentos_mar


class TestSaqueRendimentos:
    def test_saque_reduz_saldo_e_aparece_no_modal(self, page: Page):
        alternar_visao(page, "rendimentos")
        local_nome = "Carteira Saque"
        if page.locator(f"text={local_nome}").count() == 0:
            page.click('button:has-text("+ Local")')
            page.wait_for_selector("#ovRendLocal.show", timeout=3000)
            fill_input(page, "#rendLocalNome", local_nome)
            page.click("#ovRendLocal .btn.ba")
            wait_for_load(page)
            wait_for_table(page)

        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", local_nome)
        select_option(page, "#rendAddTipo", "aporte")
        select_option(page, "#rendAddMes", "1")
        fill_input(page, "#rendAddValor", "1000,00")
        fill_input(page, "#rendAddNota", "Aporte para saque")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", local_nome)
        select_option(page, "#rendAddTipo", "saque")
        select_option(page, "#rendAddMes", "1")
        fill_input(page, "#rendAddValor", "200,00")
        fill_input(page, "#rendAddNota", "Resgate parcial")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

        linha_local = page.locator("#tw tbody tr").filter(has_text=local_nome).first
        assert "800" in linha_local.locator("td").nth(1).inner_text()
        assert "800" in page.locator("#tw .tr-rend-total td").nth(1).inner_text()
        assert page.locator("#tw .tr-rend-aportes").count() == 0
        assert page.locator("#tw .tr-rend-saques").count() == 0

        linha_local.locator("td").nth(1).click()
        page.wait_for_selector("#ovRendLanc.show", timeout=3000)
        lista = page.locator("#rendLancLista")
        expect(lista).to_contain_text("Aporte")
        expect(lista).to_contain_text("Saque")
        expect(lista).to_contain_text("Resgate parcial")
        modal_should_be_visible(page, "ovRendLanc")


class TestProjecaoTaxa:
    def test_abrir_projecao(self, page: Page):
        alternar_visao(page, "rendimentos")
        kebabs = page.locator("#tw .btn-kebab")
        if kebabs.count() == 0:
            pytest.skip("Nenhum local com menu kebab")
        kebabs.first.click(force=True)
        page.wait_for_timeout(200)
        link_proj = page.locator(".dropdown-content a:has-text('Projetar rendimentos'):visible")
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
        link_proj = page.locator(".dropdown-content a:has-text('Projetar rendimentos'):visible")
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


class TestStatusRealizado:
    def test_ano_passado_marca_coluna_como_realizada(self, page: Page, server_url: str):
        ano_passado = datetime.datetime.now().year - 1

        page.goto(f"{server_url}/?ano={ano_passado}")
        page.wait_for_function(
            "() => window.CF_BOOT && (document.querySelector('#tw table') || document.querySelector('.view-tab'))"
        )
        page.wait_for_timeout(100)

        alternar_visao(page, "rendimentos")
        page.click('button:has-text("+ Local")')
        page.wait_for_selector("#ovRendLocal.show", timeout=3000)
        fill_input(page, "#rendLocalNome", "Conta Historica")
        page.click("#ovRendLocal .btn.ba")
        wait_for_load(page)
        wait_for_table(page)

        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", "Conta Historica")
        select_option(page, "#rendAddTipo", "aporte")
        select_option(page, "#rendAddMes", "1")
        fill_input(page, "#rendAddValor", "1000,00")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        wait_for_table(page)

        linha_local = page.locator("#tw tbody tr").filter(has_text="Conta Historica").first
        classes_jan_local = linha_local.locator("td").nth(1).get_attribute("class") or ""
        classes_jan_total = page.locator("#tw .tr-rend-total td").nth(1).get_attribute("class") or ""

        assert "pg-2" in classes_jan_local
        assert page.locator("#tw .tr-rend-aportes").count() == 0
        assert "pg-2" in classes_jan_total


class TestRendimentoPorDiferencaComAporte:
    """
    Regressao: ao usar o checkbox "lançar só a diferença em relação ao mês
    anterior" no modal ovRendLanc, o aporte do mês corrente NÃO deve ser
    considerado no cálculo. O rendimento é calculado como:
    rendimento = valorFinal - saldoMesAnterior - aporte + saque - outrosRendimentos.

    Cenário:
      - Local sem vínculo.
      - Jan: aporte 10.000 -> saldo Jan = 10.000.
      - Fev: aporte 2.000 (no próprio mês).
      - Fev: lançar rendimento via "diff", informando valor final = 12.500.
      - Esperado: rendimento = 12.500 - 10.000 - 2.000 = +500 (positivo).
      - Antes do fix (bug): rendimento = 12.500 - 10.000 = +2.500 (aportes ignorados).
    """

    def test_aporte_no_mes_nao_contamina_calculo_da_diferenca(self, page: Page):
        alternar_visao(page, "rendimentos")
        local_nome = "Conta DiffAporte"

        if page.locator(f"text={local_nome}").count() == 0:
            page.click('button:has-text("+ Local")')
            page.wait_for_selector("#ovRendLocal.show", timeout=3000)
            fill_input(page, "#rendLocalNome", local_nome)
            page.click("#ovRendLocal .btn.ba")
            wait_for_load(page)
            wait_for_table(page)

        # Jan: aporte 10.000 -> saldo Jan = 10.000
        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", local_nome)
        select_option(page, "#rendAddTipo", "aporte")
        select_option(page, "#rendAddMes", "1")
        fill_input(page, "#rendAddValor", "10000,00")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

        # Fev: aporte 2.000 no proprio mes
        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", local_nome)
        select_option(page, "#rendAddTipo", "aporte")
        select_option(page, "#rendAddMes", "2")
        fill_input(page, "#rendAddValor", "2000,00")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

        # Abre o modal de Fev (celula da coluna 2 do local)
        linha_local = page.locator("#tw tbody tr").filter(has_text=local_nome).first
        linha_local.locator("td").nth(2).click()
        page.wait_for_selector("#ovRendLanc.show", timeout=3000)

        # Confirma que o label reflete o saldo antes do rendimento (10.000 + 2.000 = 12.000)
        label = page.locator("#rendLancDiffLabel").inner_text()
        assert "12.000,00" in label, f"Label inesperado: {label}"

        # Seleciona tipo rendimento, mantem o checkbox "diff" marcado, digita 12500
        select_option(page, "#rendLancTipo", "rendimento")
        diff = page.locator("#rendLancDiff")
        if not diff.is_checked():
            diff.check()
        fill_input(page, "#rendLancValor", "12500,00")
        page.click("#ovRendLanc button:has-text('+ Lançar')")
        wait_for_load(page)

        # Reabre o detalhe para validar o valor persistido
        page.wait_for_selector("#rendLancLista", timeout=3000)
        lista = page.locator("#rendLancLista").inner_text()
        # Deve haver uma linha "Rendimento: R$ 500,00" (positivo, sem sinal de menos)
        assert "Rendimento: R$ 500,00" in lista, (
            f"Esperado rendimento positivo de 500 (=12500-10000-2000); lista atual:\n{lista}"
        )
        assert "-R$ 2.500" not in lista, (
            "Calculo do diff esta ignorando o aporte do mes (regressao)"
        )

        # Fecha o modal e confirma na tabela: o local deve refletir o rendimento
        page.locator("#ovRendLanc button:has-text('Fechar')").first.click()
        wait_for_table(page)

        # Localiza a linha do local especifico (evita poluicao de outros testes)
        linha_local = page.locator("#tw tbody tr").filter(has_text=local_nome).first
        cel_fev = linha_local.locator("td").nth(2)
        texto_cel = cel_fev.inner_text()
        classes_cel = cel_fev.get_attribute("class") or ""
        # Saldo em Fev = 10.000 (Jan) + 2.000 (aporte Fev) + 500 (rendimento) = 12.500
        assert "12.500" in texto_cel or "12500" in texto_cel, (
            f"Saldo do local '{local_nome}' em Fev incorreto: '{texto_cel}' (esperado 12.500)"
        )
        assert "neg" not in classes_cel, (
            f"Celula do local '{local_nome}' em Fev nao deveria estar negativo. classes='{classes_cel}'"
        )
