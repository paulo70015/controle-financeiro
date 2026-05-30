class SQLiteHomeRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def get_anos(self):
        conn = self.connection_factory()
        anos_set = set()
        tabelas = [
            "anos", "categorias", "despesas", "receitas",
            "despesas_fixas_cartao", "fixas_excecoes", "fixas_aplicadas_manual",
            "pagamento_status", "rendimentos_realizados", "depositos_conta", "movimentacoes_mensais",
            "rendimentos_locais", "rendimentos_lancamentos",
        ]
        for tabela in tabelas:
            try:
                for r in conn.execute(f"SELECT DISTINCT ano FROM {tabela}"):
                    if r[0] is not None:
                        anos_set.add(int(r[0]))
            except Exception:
                pass
        try:
            for r in conn.execute("SELECT DISTINCT ano_criacao, ano_meta FROM metas"):
                for val in (r[0], r[1]):
                    if val is not None:
                        anos_set.add(int(val))
        except Exception:
            pass
        conn.close()
        return anos_set

    def ensure_year_exists(self, ano: int) -> None:
        """Garante que o ano existe na tabela `anos` (idempotente)."""
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (ano,))
        conn.commit()
        conn.close()
