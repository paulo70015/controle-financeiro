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


class TestCategoriaCartao:
    def test_modal_criar_tem_checkbox_cartao(self, page: Page):
        """Verifica que o checkbox 'Cartão de Crédito' existe no modal de criar categoria."""
        page.click('button:has-text("+ Categoria")')
        page.wait_for_selector("#ovC.show")
        expect(page.locator("#cCartao")).to_be_visible()
        page.click("#ovC button:has-text('Cancelar')")
        wait_for_load(page)

    def test_criar_categoria_com_cartao(self, page: Page):
        """Cria uma categoria com flag cartão de crédito ativada."""
        criar_categoria(page, "Cartao Teste", is_cartao=True)
        wait_for_table(page)
        # Verifica se aparece na tabela (teste básico de que a categoria foi criada)
        dados = get_table_data(page)
        assert any("Cartao Teste" in (row[0] or "") for row in dados), "Categoria cartão não encontrada na tabela"

    def test_criar_categoria_sem_cartao(self, page: Page):
        """Cria uma categoria SEM a flag cartão e verifica sucesso."""
        criar_categoria(page, "Normal Teste", is_cartao=False)
        wait_for_table(page)
        dados = get_table_data(page)
        assert any("Normal Teste" in (row[0] or "") for row in dados)

    def _abrir_renomear_categoria(self, page: Page, nome: str):
        """Abre o modal de renomear categoria via chamada direta a abrirRen()."""
        cat_id = page.evaluate(f'''
            () => {{
                const cats = window.dados?.categorias || [];
                const found = cats.find(c => c.nome === "{nome}");
                return found ? found.id : null;
            }}
        ''')
        assert cat_id is not None, f"Categoria '{nome}' não encontrada nos dados"
        tooltip = ""
        page.evaluate(f'abrirRen({cat_id}, "{nome}", 0, null, "")')
        page.wait_for_selector("#ovRen.show")

    def test_modal_renomear_tem_checkbox_cartao(self, page: Page):
        """Verifica que o checkbox 'Cartão de Crédito' existe no modal de renomear categoria."""
        criar_categoria(page, "Renomear Cartao", is_cartao=True)
        wait_for_table(page)
        self._abrir_renomear_categoria(page, "Renomear Cartao")
        expect(page.locator("#renCartao")).to_be_visible()
        page.click("#ovRen button:has-text('Cancelar')")
        wait_for_load(page)

    def test_categoria_cartao_preserva_flag_ao_renomear(self, page: Page):
        """Renomeia uma categoria cartão e verifica que a flag permanece ativa."""
        criar_categoria(page, "Preservar Cartao", is_cartao=True)
        wait_for_table(page)

        self._abrir_renomear_categoria(page, "Preservar Cartao")

        # Verifica que o checkbox está marcado
        expect(page.locator("#renCartao")).to_be_checked()

        # Altera nome e salva
        fill_input(page, "#renN", "Preservar Cartao Renomeado")
        page.click("#ovRen .btn.ba")
        wait_for_load(page)

        # Confirma que apareceu com nome novo
        wait_for_table(page)
        dados = get_table_data(page)
        assert any("Preservar Cartao Renomeado" in (row[0] or "") for row in dados)

    def test_criar_categoria_com_tooltip(self, page: Page):
        """Cria categoria com tooltip preenchido."""
        page.click('button:has-text("+ Categoria")')
        page.wait_for_selector("#ovC.show")
        fill_input(page, "#cN", "Tooltip Teste")
        fill_input(page, "#cTooltip", "Descrição da categoria")
        page.click("#ovC .btn.ba")
        wait_for_load(page)
        wait_for_table(page)
        dados = get_table_data(page)
        assert any("Tooltip Teste" in (row[0] or "") for row in dados)
