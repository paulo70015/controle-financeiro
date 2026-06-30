"""
Utilitarios DRY para testes E2E com Playwright.

Seletores, preenchimento de formularios, verificacao de modais,
extracao de dados da tabela e helpers de sincronizacao.
"""

import datetime

from playwright.sync_api import Page, expect

# ═══════════════════════════════════════════════════════════════
#  Constantes de isolamento — testes operam no futuro para
#  nunca colidirem com dados reais do usuario.
# ═══════════════════════════════════════════════════════════════
ANO_TESTE = datetime.datetime.now().year + 10
MES_TESTE = 12  # Dezembro (evita conflitos com dados existentes)

DEBOUNCE_WAIT_MS = 200


# ═══════════════════════════════════════════════════════════════
#  Sincronizacao
# ═══════════════════════════════════════════════════════════════

def wait_for_load(page: Page, timeout_ms: int = DEBOUNCE_WAIT_MS):
    """Aguarda o ciclo de load/debouncedLoad estabilizar."""
    page.wait_for_timeout(timeout_ms)


def wait_for_table(page: Page, timeout_ms: int = 5000):
    """Aguarda a tabela principal ser renderizada dentro de #tw."""
    page.wait_for_selector("#tw table", timeout=timeout_ms)


# ═══════════════════════════════════════════════════════════════
#  Modal helpers
# ═══════════════════════════════════════════════════════════════

def modal_should_be_visible(page: Page, modal_id: str):
    """Verifica que o modal esta visivel (classe .show)."""
    expect(page.locator(f"#{modal_id}.show")).to_be_visible()


def modal_should_be_hidden(page: Page, modal_id: str):
    """Verifica que o modal NAO esta visivel."""
    expect(page.locator(f"#{modal_id}.show")).to_be_hidden()


# ═══════════════════════════════════════════════════════════════
#  Form helpers
# ═══════════════════════════════════════════════════════════════

def fill_input(page: Page, selector: str, value: str):
    """Limpa e preenche um campo de input/textarea."""
    el = page.locator(selector)
    el.clear()
    if value:
        el.fill(value)


def select_option(page: Page, selector: str, value: str):
    """Seleciona uma opcao em um <select> pelo value do option.
       Se nao encontrar, tenta pelo label (texto visivel)."""
    try:
        page.select_option(selector, value=value, timeout=2000)
    except Exception:
        page.select_option(selector, label=value)


# ═══════════════════════════════════════════════════════════════
#  Tabela helpers
# ═══════════════════════════════════════════════════════════════

def get_table_data(page: Page) -> list[list[str]]:
    """Extrai dados da tabela principal como matriz de strings."""
    wait_for_table(page)
    rows = page.locator("#tw table tbody tr")
    data = []
    count = rows.count()
    for i in range(count):
        cells = rows.nth(i).locator("td, th")
        cell_count = cells.count()
        row = []
        for j in range(cell_count):
            row.append(cells.nth(j).inner_text())
        data.append(row)
    return data


# ═══════════════════════════════════════════════════════════════
#  Pre-condicoes (setup helpers)
# ═══════════════════════════════════════════════════════════════

def criar_categoria(page: Page, nome: str, incluir_fixas: bool = False, is_cartao: bool = False, tooltip: str = ""):
    """Cria uma categoria via modal ovC."""
    page.click('button:has-text("+ Categoria")')
    page.wait_for_selector("#ovC.show")
    fill_input(page, "#cN", nome)
    if incluir_fixas:
        page.check("#cFixas")
    if is_cartao:
        page.check("#cCartao")
    if tooltip:
        fill_input(page, "#cTooltip", tooltip)
    page.click("#ovC .btn.ba")  # Botao Salvar (azul)
    wait_for_load(page)
    expect(page.locator("#ovC.show")).to_be_hidden()


def criar_despesa(
    page: Page,
    categoria: str,
    mes: int,
    valor: str,
    nota: str = "",
    ignorar_total: bool = False,
):
    """Cria uma despesa via modal ovD."""
    page.click('button:has-text("+ Despesa")')
    page.wait_for_selector("#ovD.show")

    select_option(page, "#dC", categoria)
    select_option(page, "#dM", str(mes))
    fill_input(page, "#dV", valor)
    if nota:
        fill_input(page, "#dN", nota)
    if ignorar_total:
        page.check("#dIgnorar")

    page.click("#ovD button:has-text('Salvar')")  # Salvar
    wait_for_load(page)
    expect(page.locator("#ovD.show")).to_be_hidden()


def criar_receita(
    page: Page,
    descricao: str,
    mes: int,
    valor: str,
    nota: str = "",
):
    """Cria uma receita via modal ovR."""
    page.click('button:has-text("+ Receita")')
    page.wait_for_selector("#ovR.show")

    fill_input(page, "#rD", descricao)
    select_option(page, "#rM", str(mes))
    fill_input(page, "#rV", valor)
    if nota:
        fill_input(page, "#rN", nota)

    page.click("#ovR .btn.bv")  # Salvar
    wait_for_load(page)
    expect(page.locator("#ovR.show")).to_be_hidden()


def alternar_visao(page: Page, visao: str):
    """Alterna entre 'despesas' e 'rendimentos'."""
    if visao == "rendimentos":
        page.click("#viewTabRendimentos")
    else:
        page.click("#viewTabDespesas")
    wait_for_load(page)


def abrir_drawer(page: Page, nome: str):
    """Abre o drawer lateral: 'fixas' ou 'metas'."""
    if nome == "fixas":
        page.click("#tabFixas")
    else:
        page.click("#tabMetas")
    page.wait_for_selector(f"#drawer{nome.capitalize()}.open", timeout=3000)


def fechar_drawer(page: Page):
    """Fecha o drawer lateral clicando no overlay."""
    page.click("#drawerOverlay.show")
    wait_for_load(page)
