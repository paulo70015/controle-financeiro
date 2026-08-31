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


class TestNormalizacaoSinaisRendimentos:
    def test_saque_negativo_aceito_e_aporte_negativo_vira_saque(self, page: Page):
        """Saque aceita valor positivo ou negativo (normalizado internamente) e
        aporte negativo vira saque automaticamente. A edição de saque exibe o
        valor com sinal negativo, consistente com a linha do modal."""
        alternar_visao(page, "rendimentos")
        local_nome = "Carteira Sinais"
        if page.locator(f"text={local_nome}").count() == 0:
            page.click('button:has-text("+ Local")')
            page.wait_for_selector("#ovRendLocal.show", timeout=3000)
            fill_input(page, "#rendLocalNome", local_nome)
            page.click("#ovRendLocal .btn.ba")
            wait_for_load(page)
            wait_for_table(page)

        # Jan: aporte 1.000 positivo
        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", local_nome)
        select_option(page, "#rendAddTipo", "aporte")
        select_option(page, "#rendAddMes", "1")
        fill_input(page, "#rendAddValor", "1000,00")
        fill_input(page, "#rendAddNota", "Aporte base")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

        # Jan: saque digitado como negativo (-200) -> aceito e normalizado
        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", local_nome)
        select_option(page, "#rendAddTipo", "saque")
        select_option(page, "#rendAddMes", "1")
        fill_input(page, "#rendAddValor", "-200,00")
        fill_input(page, "#rendAddNota", "Saque negativo digitado")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

        # Jan: aporte negativo (-300) -> vira saque automaticamente
        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", local_nome)
        select_option(page, "#rendAddTipo", "aporte")
        select_option(page, "#rendAddMes", "1")
        fill_input(page, "#rendAddValor", "-300,00")
        fill_input(page, "#rendAddNota", "Aporte que vira saque")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

        # Saldo Jan = 1.000 - 200 - 300 = 500
        linha_local = page.locator("#tw tbody tr").filter(has_text=local_nome).first
        assert "500,00" in linha_local.locator("td").nth(1).inner_text()

        # Abre o detalhe de Jan e confirma tipos e sinais
        linha_local.locator("td").nth(1).click()
        page.wait_for_selector("#ovRendLanc.show", timeout=3000)
        lista = page.locator("#rendLancLista")
        expect(lista).to_contain_text("Aporte: R$ 1.000,00")
        expect(lista).to_contain_text("Saque: -R$ 200,00")
        expect(lista).to_contain_text("Saque: -R$ 300,00")

        # Edição de saque exibe o valor com sinal negativo (consistente com a linha)
        linha_saque = page.locator("#rendLancLista .di").filter(has_text="Saque negativo digitado").first
        linha_saque.locator(".btn-edit").click()
        expect(page.locator("#rendLancValor")).to_have_value("-200,00")

        # Fecha sem salvar a edição
        page.locator("#ovRendLanc button:has-text('Fechar')").first.click()
        wait_for_table(page)


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


class TestLinhaSaldoSemProjecoes:
    """
    Valida a linha 'Saldo' (tr-rend-normal) que fica entre 'Rendimentos' e
    'Saldo acumulado'. Ela deve incluir rendimentos reais mas excluir projeções.

    Fórmula: Saldo = Σ (Aportes + Rendimentos − Projeções − Saques) acumulado.

    Cada teste usa um ano isolado diferente (ANO_TESTE + 50 + offset) para evitar
    interferência entre testes da mesma classe.
    """

    _ano_offset = 0

    @pytest.fixture(autouse=True)
    def usar_ano_isolado(self, page: Page, server_url: str):
        from test_browser.helpers import ANO_TESTE
        ano_isolado = ANO_TESTE + 50 + TestLinhaSaldoSemProjecoes._ano_offset
        TestLinhaSaldoSemProjecoes._ano_offset += 1
        page.goto(f"{server_url}/?ano={ano_isolado}")
        page.wait_for_function(
            "() => window.CF_BOOT && (document.querySelector('#tw table') || document.querySelector('.view-tab'))"
        )
        page.wait_for_timeout(150)

    def _criar_local_e_aporte(self, page: Page, nome: str, valor_aporte: str = "10000,00"):
        """Cria um local e adiciona um aporte em Janeiro."""
        alternar_visao(page, "rendimentos")
        if page.locator(f"text={nome}").count() == 0:
            page.click('button:has-text("+ Local")')
            page.wait_for_selector("#ovRendLocal.show", timeout=3000)
            fill_input(page, "#rendLocalNome", nome)
            page.click("#ovRendLocal .btn.ba")
            wait_for_load(page)
            wait_for_table(page)

        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", nome)
        select_option(page, "#rendAddTipo", "aporte")
        select_option(page, "#rendAddMes", "1")
        fill_input(page, "#rendAddValor", valor_aporte)
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

    def _valor_linha(self, page: Page, classe_css: str, coluna: int) -> str:
        """Extrai o texto da célula na coluna (1-based) de uma linha de totais."""
        cel = page.locator(f"#tw .{classe_css} td").nth(coluna)
        return cel.inner_text().strip()

    def _valor_numerico(self, texto: str) -> float:
        """Converte 'R$ 10.000,00' → 10000.0"""
        return float(texto.replace("R$", "").replace(".", "").replace(",", ".").strip())

    def test_linha_saldo_aparece_entre_rendimentos_e_saldo_acumulado(self, page: Page):
        """A linha 'Saldo' (tr-rend-normal) deve existir e estar na ordem correta."""
        self._criar_local_e_aporte(page, "Conta Ordem")

        expect(page.locator("#tw .tr-rend-rendimentos")).to_be_visible()
        expect(page.locator("#tw .tr-rend-normal")).to_be_visible()
        expect(page.locator("#tw .tr-rend-total")).to_be_visible()

        linhas = page.locator("#tw tbody tr").all()
        idx_rend = -1
        idx_normal = -1
        idx_total = -1
        for i, row in enumerate(linhas):
            classes = row.get_attribute("class") or ""
            if "tr-rend-rendimentos" in classes:
                idx_rend = i
            elif "tr-rend-normal" in classes:
                idx_normal = i
            elif "tr-rend-total" in classes:
                idx_total = i

        assert idx_rend < idx_normal < idx_total, (
            f"Ordem incorreta: Rendimentos={idx_rend}, Saldo={idx_normal}, Saldo acumulado={idx_total}"
        )

    def test_saldo_exclui_projecoes(self, page: Page):
        """
        Com projeção de 1% ao mês e sem rendimentos reais:
        Saldo (sem projeções) < Saldo acumulado (com projeções).
        Aporte 10.000 em Jan → Saldo Jan = 10.000, Saldo acum. Jan = 10.100.
        """
        local = "Conta Projecao"
        self._criar_local_e_aporte(page, local)

        # Configura projeção de 1%
        kebabs = page.locator("#tw .btn-kebab")
        assert kebabs.count() > 0, "Nenhum menu kebab encontrado"
        kebabs.first.click(force=True)
        page.wait_for_timeout(200)
        link_proj = page.locator(".dropdown-content a:has-text('Projetar rendimentos'):visible")
        assert link_proj.count() > 0, "Opção Projetar rendimentos não encontrada"
        link_proj.first.click(force=True)
        page.wait_for_selector("#ovRendProj.show", timeout=3000)
        fill_input(page, "#rendProjPct", "1,00")
        page.click("#ovRendProj .btn.ba")
        wait_for_load(page)
        wait_for_table(page)

        saldo_jan = self._valor_numerico(self._valor_linha(page, "tr-rend-normal", 1))
        saldo_acum_jan = self._valor_numerico(self._valor_linha(page, "tr-rend-total", 1))

        assert saldo_jan == 10000.0, f"Saldo Jan esperado 10000, obtido: {saldo_jan}"
        assert saldo_acum_jan == 10100.0, f"Saldo acumulado Jan esperado 10100, obtido: {saldo_acum_jan}"
        assert saldo_jan < saldo_acum_jan, "Saldo deve ser menor que Saldo acumulado com projeção"

        # Fevereiro: sem novos lançamentos
        saldo_fev = self._valor_numerico(self._valor_linha(page, "tr-rend-normal", 2))
        saldo_acum_fev = self._valor_numerico(self._valor_linha(page, "tr-rend-total", 2))

        assert saldo_fev == 10000.0, f"Saldo Fev esperado 10000, obtido: {saldo_fev}"
        assert saldo_acum_fev == 10201.0, f"Saldo acumulado Fev esperado 10201, obtido: {saldo_acum_fev}"

    def test_saldo_inclui_rendimentos_reais(self, page: Page):
        """
        Sem projeção, com rendimento real lançado:
        Saldo deve ser igual a Saldo acumulado (não há projeções para excluir).
        """
        local = "Conta Real"
        self._criar_local_e_aporte(page, local)

        # Lança rendimento real de 500 em Fev
        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", local)
        select_option(page, "#rendAddTipo", "rendimento")
        select_option(page, "#rendAddMes", "2")
        fill_input(page, "#rendAddValor", "500,00")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

        # Janeiro: sem rendimentos → Saldo = Saldo acumulado = 10.000
        saldo_jan = self._valor_numerico(self._valor_linha(page, "tr-rend-normal", 1))
        saldo_acum_jan = self._valor_numerico(self._valor_linha(page, "tr-rend-total", 1))
        assert saldo_jan == saldo_acum_jan == 10000.0, (
            f"Jan: Saldo={saldo_jan}, Saldo acumulado={saldo_acum_jan}"
        )

        # Fevereiro: com rendimento real de 500 → Saldo = Saldo acumulado = 10.500
        saldo_fev = self._valor_numerico(self._valor_linha(page, "tr-rend-normal", 2))
        saldo_acum_fev = self._valor_numerico(self._valor_linha(page, "tr-rend-total", 2))
        assert saldo_fev == saldo_acum_fev == 10500.0, (
            f"Fev: Saldo={saldo_fev}, Saldo acumulado={saldo_acum_fev}"
        )


class TestNotaNumericaComoValorFinal:
    def test_nota_numerica_com_valor_vazio_vira_valor_final(self, page: Page):
        """Nota numérica pura com campo Valor vazio (tipo rendimento) deve ser
        tratada como o valor final informado: o diff calcula a diferença em
        relação ao saldo anterior (considerando aportes/saques) e a célula
        reflete o valor final."""
        alternar_visao(page, "rendimentos")
        local = "Conta Nota Fmt"
        if page.locator(f"text={local}").count() == 0:
            page.click('button:has-text("+ Local")')
            page.wait_for_selector("#ovRendLocal.show", timeout=3000)
            fill_input(page, "#rendLocalNome", local)
            page.click("#ovRendLocal .btn.ba")
            wait_for_load(page)
        alternar_visao(page, "rendimentos")
        wait_for_table(page)

        # Abre o detalhe de Jan (célula 1) do local
        linha_local = page.locator("#tw tbody tr").filter(has_text=local).first
        linha_local.locator("td").nth(1).click()
        page.wait_for_selector("#ovRendLanc.show", timeout=3000)

        # Lança rendimento com valor vazio e nota numérica pura (como no bug relatado)
        select_option(page, "#rendLancTipo", "rendimento")
        fill_input(page, "#rendLancNota", "23691.55")
        page.click("#ovRendLanc button:has-text('+ Lançar')")
        wait_for_load(page)
        page.wait_for_selector("#rendLancLista", timeout=3000)

        lista = page.locator("#rendLancLista").inner_text()
        # Local novo (saldo anterior 0): rendimento = 23.691,55 - 0 = 23.691,55
        assert "Rendimento: R$ 23.691,55" in lista, (
            f"Nota numérica deveria ser usada como valor final do rendimento; lista atual:\n{lista}"
        )
        assert "23691.55" not in lista, (
            f"Valor cru não deveria aparecer; lista atual:\n{lista}"
        )

        # Fecha o modal e confirma na tabela: a célula de Jan reflete o valor final
        page.locator("#ovRendLanc button:has-text('Fechar')").first.click()
        wait_for_table(page)
        linha_local = page.locator("#tw tbody tr").filter(has_text=local).first
        cel_jan = linha_local.locator("td").nth(1)
        texto_cel = cel_jan.inner_text()
        assert "23.691,55" in texto_cel, (
            f"Saldo do local '{local}' em Jan incorreto: '{texto_cel}' (esperado 23.691,55)"
        )
