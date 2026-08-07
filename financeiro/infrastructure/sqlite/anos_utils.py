"""
Utilidades de descoberta de anos no SQLite — DRY entre repositórios.

Antes: cada repositório executava `SELECT DISTINCT ano FROM <tabela>` para
13 tabelas (13 consultas por carga). Agora: 1 consulta UNION + 1 consulta
em sqlite_master para robustez contra bancos legados sem alguma tabela.
"""

_TABELAS_COM_ANO = [
    "anos", "categorias", "despesas", "receitas",
    "despesas_fixas_cartao", "fixas_excecoes", "fixas_aplicadas_manual",
    "pagamento_status", "rendimentos_realizados", "depositos_conta", "movimentacoes_mensais",
    "rendimentos_locais", "rendimentos_lancamentos",
]


def descobrir_anos(conn) -> set[int]:
    """Descobre todos os anos com dados em qualquer tabela, em 1 consulta.

    Os nomes de tabela abaixo são hardcoded — seguro contra SQL injection.
    Se esta lista se tornar dinâmica no futuro, use aspas duplas com
    identificadores escapados.
    """
    existentes = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    partes = [f"SELECT DISTINCT ano FROM {t}" for t in _TABELAS_COM_ANO if t in existentes]
    if not partes:
        return set()
    query = " UNION ".join(partes)
    return {int(r[0]) for r in conn.execute(query) if r[0] is not None}
