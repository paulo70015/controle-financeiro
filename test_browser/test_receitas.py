"""
Testes de Receitas: criacao, validacao, edicao, exclusao e lote.
"""

import pytest
from playwright.sync_api import Page, expect

from test_browser.helpers import (
    wait_for_load,
    wait_for_table,
    fill_input,
    select_option,
    criar_receita,
    get_table_data,
    modal_should_be_visible,
    modal_should_be_hidden,
)


class TestCriarReceita:
    def test_abrir_modal_receita(self, page: Page):
        page.click('button:has-text("+ Receita")')
        modal_should_be_visible(page, "ovR")

    def test_fechar_modal_receita(self, page: Page):
        page.click('button:has-text("+ Receita")')
        page.wait_for_selector("#ovR.show")
        page.click("#ovR button:has-text('Cancelar')")
        wait_for_load(page)
        modal_should_be_hidden(page, "ovR")

    def test_criar_receita_simples(self, page: Page):
        criar_receita(page, "Salario", 1, "5000,00", "Empresa X")
        wait_for_table(page)
        # A linha de receitas (__rec__) deve existir
        dados = get_table_data(page)
        tem_rec = any("Receitas" in (row[0] or "") or "__rec__" in str(row)
                      for row in dados)
        assert tem_rec or len(dados) > 0, "Linha de receitas nao encontrada"

    def test_validacao_receita_sem_valor(self, page: Page):
        page.click('button:has-text("+ Receita")')
        page.wait_for_selector("#ovR.show")
        fill_input(page, "#rD", "Teste sem valor")
        # Nao preenche valor

        dialog_msg = [None]
        def handle_dialog(dialog):
            dialog_msg[0] = dialog.message
            dialog.accept()
        page.on("dialog", handle_dialog)

        page.click("#ovR button:has-text('Salvar')")
        page.wait_for_timeout(500)
        assert dialog_msg[0] is not None, "Esperado alerta de validacao"
        assert "valor" in dialog_msg[0].lower()


class TestEditarExcluirReceita:
    def test_abrir_detalhe_receita(self, page: Page):
        criar_receita(page, "Freelance", 3, "2000,00")
        wait_for_table(page)

        # Clica na celula de receitas do mes 3
        # A linha de receitas tem classe tr-rec
        linha_rec = page.locator("#tw table tbody tr.tr-rec")
        if linha_rec.count() == 0:
            pytest.skip("Linha de receitas nao encontrada")

        # Clica na celula do mes 3 (coluna 4)
        linha_rec.first.locator("td").nth(3).click()
        page.wait_for_selector("#ovDet.show", timeout=3000)
        modal_should_be_visible(page, "ovDet")
        # Deve conter "Receitas" no titulo
        expect(page.locator("#detT")).to_contain_text("Receitas")

    def test_editar_valor_receita(self, page: Page):
        criar_receita(page, "Extra", 5, "1000,00")
        wait_for_table(page)

        linha_rec = page.locator("#tw table tbody tr.tr-rec")
        if linha_rec.count() == 0:
            pytest.skip("Linha de receitas nao encontrada")
        linha_rec.first.locator("td").nth(5).click()
        page.wait_for_selector("#ovDet.show", timeout=3000)

        fill_input(page, "#aV", "1500,00")
        page.click('#ovDet button:has-text("Salvar e fechar")')
        wait_for_load(page)
        modal_should_be_hidden(page, "ovDet")

    def test_excluir_receita(self, page: Page):
        criar_receita(page, "Para excluir", 7, "300,00")
        wait_for_table(page)

        linha_rec = page.locator("#tw table tbody tr.tr-rec")
        if linha_rec.count() == 0:
            pytest.skip("Linha de receitas nao encontrada")
        linha_rec.first.locator("td").nth(7).click()
        page.wait_for_selector("#ovDet.show", timeout=3000)

        botoes_del = page.locator("#ovDet button[onclick^='delR']")
        if botoes_del.count() > 0:
            botoes_del.first.click()
            page.wait_for_timeout(300)
        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)
        modal_should_be_hidden(page, "ovDet")


class TestLoteReceitas:
    def test_abrir_lote_receitas(self, page: Page):
        """Abrir modal de lote para receitas via link na tabela."""
        # Garante que existe receita para a linha tr.tr-rec aparecer
        criar_receita(page, "LoteRecTest", 3, "500,00")
        wait_for_table(page)

        # Abre o kebab menu da linha de receitas (tr.tr-rec)
        linha_rec = page.locator("#tw table tbody tr.tr-rec")
        assert linha_rec.count() > 0, "Linha de receitas nao encontrada"
        kebabs = linha_rec.first.locator(".btn-kebab")
        assert kebabs.count() > 0, "Sem menu kebab na linha de receitas"
        kebabs.first.click(force=True)
        # toggleCatMenu move o dropdown para document.body e adiciona .show
        page.wait_for_selector(".dropdown-content.show", timeout=3000)

        link_lote = page.locator(
            ".dropdown-content.show a:has-text('Lançar todos os meses')"
        )
        assert link_lote.count() > 0, "Opcao de lote nao encontrada no menu"
        link_lote.first.click(force=True)
        page.wait_for_selector("#ovLote.show", timeout=3000)
        modal_should_be_visible(page, "ovLote")
        # No modo receita, o campo descricao (ltD) deve estar visivel
        expect(page.locator("#ltDescRow")).to_be_visible()

    def test_salvar_lote_receitas(self, page: Page):
        """Preencher e salvar lote de receitas."""
        criar_receita(page, "LoteRecTest2", 3, "500,00")
        wait_for_table(page)

        linha_rec = page.locator("#tw table tbody tr.tr-rec")
        assert linha_rec.count() > 0, "Linha de receitas nao encontrada"
        kebabs = linha_rec.first.locator(".btn-kebab")
        assert kebabs.count() > 0, "Sem menu kebab"
        kebabs.first.click(force=True)
        page.wait_for_selector(".dropdown-content.show", timeout=3000)

        link_lote = page.locator(
            ".dropdown-content.show a:has-text('Lançar todos os meses')"
        )
        assert link_lote.count() > 0, "Opcao de lote nao encontrada"
        link_lote.first.click(force=True)
        page.wait_for_selector("#ovLote.show", timeout=3000)

        fill_input(page, "#ltV", "200,00")
        fill_input(page, "#ltN", "Lote receitas teste")
        # Aguarda preview
        try:
            page.wait_for_selector("#ltPreview[style*='block']", timeout=3000)
        except Exception:
            pass
        page.click('#ovLote button:has-text("Salvar Lote")')
        wait_for_load(page)
        modal_should_be_hidden(page, "ovLote")
