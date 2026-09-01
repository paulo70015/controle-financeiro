"""
Testes E2E: reflexo automático da aba Rendimentos nas contas correntes.

Fluxo completo: local vinculado a conta -> lançamentos refletem na conta
no mesmo mês (tags [Aporte]/[Saque]/[Rendimento], somente leitura) ->
editar/excluir na aba Rendimentos acompanha o reflexo.
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

CONTA_NOME = "Conta Reflexo"
LOCAL_NOME = "Invest Reflexo"


class TestReflexoRendimentoConta:
    def test_fluxo_completo_reflexo(self, page: Page):
        # ── Setup: conta corrente ─────────────────────────────────────────
        wait_for_table(page)
        if page.locator(f"#tw:has-text('{CONTA_NOME}')").count() == 0:
            page.click('button:has-text("+ Conta")')
            page.wait_for_selector("#ovConta.show", timeout=3000)
            fill_input(page, "#ctN", CONTA_NOME)
            fill_input(page, "#ctSI", "1000,00")
            page.click("#ovConta button:has-text('Salvar')")
            wait_for_load(page)
            wait_for_table(page)

        # ── Setup: local de rendimento vinculado à conta ──────────────────
        alternar_visao(page, "rendimentos")
        if page.locator(f"text={LOCAL_NOME}").count() == 0:
            page.click('button:has-text("+ Local")')
            page.wait_for_selector("#ovRendLocal.show", timeout=3000)
            fill_input(page, "#rendLocalNome", LOCAL_NOME)
            conta_val = page.eval_on_selector_all(
                "#rendLocalConta option",
                "opts => { const o = opts.find(x => x.textContent.includes('Conta Reflexo')); return o ? o.value : ''; }",
            )
            assert conta_val, "Conta Reflexo nao encontrada no select do local"
            page.select_option("#rendLocalConta", value=conta_val)
            page.click("#ovRendLocal .btn.ba")
            wait_for_load(page)
            wait_for_table(page)

        # ── Aporte no mês 1 e rendimento no mês 2 ─────────────────────────
        alternar_visao(page, "rendimentos")
        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", LOCAL_NOME)
        select_option(page, "#rendAddTipo", "aporte")
        select_option(page, "#rendAddMes", "1")
        fill_input(page, "#rendAddValor", "1000,00")
        fill_input(page, "#rendAddNota", "Aporte reflexo")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

        page.click('button:has-text("+ Lançamento")')
        page.wait_for_selector("#ovRendAdd.show", timeout=3000)
        select_option(page, "#rendAddLocal", LOCAL_NOME)
        select_option(page, "#rendAddTipo", "rendimento")
        select_option(page, "#rendAddMes", "2")
        fill_input(page, "#rendAddValor", "50,00")
        fill_input(page, "#rendAddNota", "Rendimento reflexo")
        page.click("#ovRendAdd .btn.ba")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovRendAdd")
        wait_for_table(page)

        # ── Reflexo na conta: mês 1 com [Aporte] +1.000,00 (crédito) ───────
        alternar_visao(page, "despesas")
        wait_for_table(page)
        linha_conta = page.locator("tr.tr-conta").filter(has_text=CONTA_NOME).first

        linha_conta.locator("td").nth(1).click()  # mês 1
        page.wait_for_selector("#ovDep.show", timeout=3000)
        dep_lista = page.locator("#depL")
        expect(dep_lista).to_contain_text("Rendimentos vinculados")
        expect(dep_lista).to_contain_text("Aporte em Invest Reflexo")
        expect(dep_lista).to_contain_text("[Aporte]")
        expect(dep_lista).to_contain_text("R$ 1.000,00")
        # Visão B: aporte é crédito na conta (patrimônio total) — nunca negativo
        expect(dep_lista).not_to_contain_text("-R$ 1.000,00")
        page.locator("#ovDep button:has-text('Fechar')").first.click()
        wait_for_load(page)

        # ── Reflexo na conta: mês 2 com [Rendimento] +50,00 ───────────────
        linha_conta.locator("td").nth(2).click()  # mês 2
        page.wait_for_selector("#ovDep.show", timeout=3000)
        expect(page.locator("#depL")).to_contain_text("Rendimentos vinculados")
        expect(page.locator("#depL")).to_contain_text("Rendimento de Invest Reflexo")
        expect(page.locator("#depL")).to_contain_text("[Rendimento]")
        expect(page.locator("#depL")).to_contain_text("50,00")
        page.locator("#ovDep button:has-text('Fechar')").first.click()
        wait_for_load(page)

        # ── Editar rendimento para 75,00 na aba Rendimentos → reflexo segue ─
        alternar_visao(page, "rendimentos")
        wait_for_table(page)
        linha_local = page.locator("#tw tbody tr").filter(has_text=LOCAL_NOME).first
        linha_local.locator("td").nth(2).click()  # mês 2
        page.wait_for_selector("#ovRendLanc.show", timeout=3000)
        linha_rend = page.locator("#rendLancLista .di").filter(has_text="Rendimento reflexo").first
        linha_rend.locator(".btn-edit").click()
        fill_input(page, "#rendLancValor", "75,00")
        page.locator('button[onclick="salvarRendimentoLancamento()"]').click()
        page.wait_for_timeout(500)
        page.locator("#ovRendLanc button:has-text('Fechar')").first.click()
        wait_for_load(page)
        wait_for_table(page)

        alternar_visao(page, "despesas")
        wait_for_table(page)
        linha_conta.locator("td").nth(2).click()  # mês 2
        page.wait_for_selector("#ovDep.show", timeout=3000)
        expect(page.locator("#depL")).to_contain_text("75,00")
        page.locator("#ovDep button:has-text('Fechar')").first.click()
        wait_for_load(page)

        # ── Excluir aporte na aba Rendimentos → reflexo some da conta ─────
        alternar_visao(page, "rendimentos")
        wait_for_table(page)
        linha_local.locator("td").nth(1).click()  # mês 1
        page.wait_for_selector("#ovRendLanc.show", timeout=3000)
        linha_aporte = page.locator("#rendLancLista .di").filter(has_text="Aporte reflexo").first
        linha_aporte.locator(".btn-delete").click()
        page.wait_for_timeout(300)
        page.locator('button[onclick="salvarRendimentoLancamentoEFechar()"]').click()
        wait_for_load(page)
        wait_for_table(page)

        alternar_visao(page, "despesas")
        wait_for_table(page)
        linha_conta.locator("td").nth(1).click()  # mês 1
        page.wait_for_selector("#ovDep.show", timeout=3000)
        dep_texto = page.locator("#depL").inner_text()
        assert "Aporte em Invest Reflexo" not in dep_texto
        assert "[Aporte]" not in dep_texto
        page.locator("#ovDep button:has-text('Fechar')").first.click()
        wait_for_load(page)

        # ── Modal de Movimentação Geral: reflexos sem botões de edição ────
        linha_mov_geral = page.locator("tr.tr-mov").first
        linha_mov_geral.locator("td").nth(2).click()  # mês 2 (tem o rendimento refletido)
        page.wait_for_selector("#ovMov.show", timeout=3000)
        mov_lista = page.locator("#movL")
        if mov_lista.filter(has_text="Rendimento de Invest Reflexo").count() > 0:
            linha_mov = mov_lista.locator(".di").filter(has_text="Rendimento de Invest Reflexo").first
            expect(linha_mov.locator(".btn-delete, .btn-edit")).to_have_count(0)
        page.locator("#ovMov button:has-text('Fechar')").first.click()
        wait_for_load(page)
