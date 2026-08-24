"""Utilidades compartilhadas para despesas fixas.

Centraliza a regra de contabilizacao/exibicao dos lancamentos fisicos
"Soma das Despesas Fixas" materializados pelo status de pagamento.

Regra de negocio: um lancamento com nota "Soma das Despesas Fixas\u200b"
representa a materializacao das despesas fixas de uma celula (ano, mes,
categoria) quando aquela celula foi marcada como paga. Se a celula tiver a
fixa excluida (existe registro em `fixas_excecoes`), esse lancamento deve
continuar existindo no banco (historico) mas NAO deve mais ser contabilizado
nem exibido como despesa — exatamente como a propria despesa fixa virtual
deixa de contar quando removida.

As funcoes abaixo sao puras (sem acesso a banco): recebem os dados ja
buscados e retornam o resultado transformado. Isso mantem a regra em um
unico lugar (DRY) e deixa os repositories focados apenas em persistencia.
"""

# O \u200b (zero-width space) e um marcador interno que distingue esses
# lancamentos de despesas reais do usuario.
NOTA_SOMA_FIXAS = "Soma das Despesas Fixas\u200b"
_PREFIXO_SOMA_FIXAS = "Soma das Despesas Fixas"


def eh_soma_fixas(nota) -> bool:
    """True se `nota` for um lancamento interno de soma de fixas."""
    return bool(nota) and str(nota).startswith(_PREFIXO_SOMA_FIXAS)


def excluir_soma_fixas_ocultas(rows, mes, cat_id, fixas_excecoes):
    """Remove de `rows` (lista de despesas de uma celula) os lancamentos
    'Soma' quando a fixa da celula esta excluida.

    Parametros:
        rows: lista de dicts de despesas (com chave ``nota``).
        mes: mes da celula.
        cat_id: id da categoria da celula.
        fixas_excecoes: dict com chaves ``f"{cat_id}_{mes}"``.
    """
    if not rows:
        return rows
    if fixas_excecoes and f"{cat_id}_{mes}" in fixas_excecoes:
        return [r for r in rows if not eh_soma_fixas(r.get("nota"))]
    return rows


def subtrair_soma_fixas_ocultas(despesas, somas, fixas_excecoes, cat_id_por_nome):
    """Subtrai dos agregados de `despesas` os lancamentos 'Soma' cuja celula
    (mes, categoria) esta excluida.

    Parametros:
        despesas: dict ``despesas[categoria][mes] = {"valor": ...}`` (in-place).
        somas: iteravel de dicts com chaves ``categoria``, ``mes`` e ``total``
            (o somatorio dos lancamentos 'Soma' por celula).
        fixas_excecoes: dict com chaves ``f"{cat_id}_{mes}"``.
        cat_id_por_nome: dict ``{nome_categoria: cat_id}``.
    """
    for soma in somas:
        cid = cat_id_por_nome.get(soma.get("categoria"))
        if cid is not None and fixas_excecoes and f"{cid}_{soma.get('mes')}" in fixas_excecoes:
            cell = despesas.get(soma.get("categoria"), {}).get(soma.get("mes"))
            if cell:
                cell["valor"] = round((cell.get("valor") or 0) - (soma.get("total") or 0), 2)
