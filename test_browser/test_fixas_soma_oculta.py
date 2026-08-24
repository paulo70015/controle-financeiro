"""
Teste E2E específico do bug: lançamento físico "Soma das Despesas Fixas"
não deve aparecer nem contar no modal quando a fixa da célula está excluída
(existe registro em fixas_excecoes).

Contexto: ao marcar uma célula como PAGA, o backend materializa as despesas
fixas ativas como um lançamento real com nota "Soma das Despesas Fixas\u200b"
e insere uma exceção. Mesmo assim, esse lançamento deve deixar de ser
contabilizado/exibido (fixa removida). Este teste garante isso.
"""

import requests
import pytest
from playwright.sync_api import Page

from test_browser.helpers import (
    wait_for_load,
    wait_for_table,
    get_table_data,
    modal_should_be_visible,
    ANO_TESTE,
)

VALOR_FIXA = "856,90"      # fixa materializada
VALOR_MANUAL = 14148.84    # despesa manual (o que deve restar no total)
FIXA_DIA = 10


def _req(base: str, method: str, url: str, **kwargs):
    return requests.request(method, f"{base}{url}", timeout=10, **kwargs)


@pytest.fixture(autouse=True)
def setup_celula_materializada(flask_server):
    """Prepara uma categoria com fixa, despesa manual e status PAGA via API.

    O nome da categoria é único por teste (timestamp) para evitar colisão entre
    execuções que compartilham o mesmo servidor/ano de teste.
    """
    from test_browser.helpers import MES_TESTE
    import time
    global CAT_NOME
    CAT_NOME = "SomaOcultaE2E_" + str(int(time.time() * 1000))
    base = flask_server

    # Cria categoria SEM inclui_fixas (fixa vinculada por cat_id => determinístico)
    resp = _req(base, "POST", "/api/categoria",
                json={"ano": ANO_TESTE, "nome": CAT_NOME, "ordem": 996, "inclui_fixas": False})
    assert resp.status_code == 200, resp.text

    dados = _req(base, "GET", f"/api/dados/{ANO_TESTE}").json()
    cat = next(c for c in dados["categorias"] if c["nome"] == CAT_NOME)
    cat_id = cat["id"]

    # Cria a fixa vinculada (R$ 856,90)
    resp = _req(base, "POST", "/api/fixa",
                json={"ano": ANO_TESTE, "descricao": "Fixa Soma E2E",
                      "valor": float(VALOR_FIXA.replace(",", ".")), "dia": FIXA_DIA,
                      "cat_id": cat_id})
    assert resp.status_code == 200, resp.text
    dados2 = _req(base, "GET", f"/api/dados/{ANO_TESTE}").json()
    assert any(f.get("cat_id") == cat_id for f in dados2.get("fixas", [])), \
        "Fixa não relacionada à categoria"

    # Despesa manual (o que deve restar no total após a ocultação)
    resp = _req(base, "POST", "/api/despesa",
                json={"ano": ANO_TESTE, "mes": MES_TESTE, "categoria": CAT_NOME,
                      "valor": VALOR_MANUAL, "nota": "Gasto manual e2e"})
    assert resp.status_code == 200, resp.text

    # Marca como PAGA => materializa "Soma das Despesas Fixas" + insert exceção
    resp = _req(base, "POST", "/api/pagamento_status",
                json={"ano": ANO_TESTE, "mes": MES_TESTE, "categoria": CAT_NOME, "status": 2})
    assert resp.status_code == 200, resp.text

    # Pré-condição: a célula ficou PAGA e com fixas_excecoes (a materialização
    # ocorreu no backend). O lançamento "Soma" já NÃO aparece no detalhe
    # (comportamento corrigido) — os asserts do teste garantem essa ocultação.
    dados3 = _req(base, "GET", f"/api/dados/{ANO_TESTE}").json()
    pag_cat = dados3.get("pagamentos", {}).get(CAT_NOME, {})
    celula_paga = pag_cat.get(MES_TESTE) or pag_cat.get(str(MES_TESTE))
    assert celula_paga == 2, f"Status PAGA não aplicado: {celula_paga}"
    exc_key = f"{cat_id}_{MES_TESTE}"
    assert exc_key in dados3.get("fixas_excecoes", {}), \
        f"fixas_excecoes não criada: {dados3.get('fixas_excecoes')}"

    yield

    # Teardown: apaga categoria (remove despesas + 'Soma' + exceções) e a fixa
    # criada — a remoção da categoria apenas desvincula a fixa (cat_id=NULL),
    # deixando-a órfã no drawer; por isso a deletamos explicitamente.
    dados_limpeza = _req(base, "GET", f"/api/dados/{ANO_TESTE}").json()
    for f in dados_limpeza.get("fixas", []):
        if f.get("descricao") == "Fixa Soma E2E":
            _req(base, "DELETE", f"/api/fixa/{f['id']}")
    _req(base, "DELETE", f"/api/categoria/{ANO_TESTE}/{CAT_NOME}")


def _encontrar_linha(dados, nome):
    for i, row in enumerate(dados):
        if row and nome in (row[0] or ""):
            return i
    return None


class TestSomaFixasOcultaNoModal:
    def test_lancamento_soma_nao_aparece_no_modal(self, page: Page):
        """O modal da célula não deve exibir o lançamento 'Soma das Despesas Fixas'."""
        from test_browser.helpers import MES_TESTE
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_linha(dados, CAT_NOME)
        assert linha_idx is not None, f"Categoria {CAT_NOME} não encontrada na tabela"

        page.click(f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child({MES_TESTE + 1})")
        page.wait_for_selector("#ovDet.show", timeout=5000)
        modal_should_be_visible(page, "ovDet")

        conteudo = page.locator("#ovDet").inner_text()
        assert "Soma das Despesas Fixas" not in conteudo, \
            f"Lançamento 'Soma das Despesas Fixas' apareceu no modal:\n{conteudo}"
        assert "Gasto manual e2e" in conteudo, "Despesa manual não encontrada no modal"

        page.click('#ovDet button:has-text("Fechar")')
        wait_for_load(page)

    def test_valor_celula_nao_inclui_soma(self, page: Page):
        """A célula deve somar só a despesa manual (sem a fixa materializada).

        Sem a correção, a célula exibe R$ 15.005,74 (14.148,84 + 856,90).
        Com a correção, deve mostrar apenas R$ 14.148,84.
        """
        from test_browser.helpers import MES_TESTE
        wait_for_table(page)
        dados = get_table_data(page)
        linha_idx = _encontrar_linha(dados, CAT_NOME)
        assert linha_idx is not None

        celula_texto = page.locator(
            f"#tw table tbody tr:nth-child({linha_idx + 1}) td:nth-child({MES_TESTE + 1})"
        ).inner_text()

        assert "14.148,84" in celula_texto.replace("R$", ""), \
            f"Valor manual não exibido na célula: {celula_texto!r}"
        assert "15.005,74" not in celula_texto, \
            f"A célula incluiu indevidamente o lançamento 'Soma' (856,90): {celula_texto!r}"
