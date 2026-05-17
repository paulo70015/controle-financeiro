class SQLiteHomeRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def get_anos(self):
        conn = self.connection_factory()
        rows = conn.execute("SELECT ano FROM anos ORDER BY ano DESC").fetchall()
        conn.close()
        return {r[0] for r in rows}

    def ensure_year_exists(self, ano: int) -> None:
        """Garante que o ano existe na tabela `anos` (idempotente)."""
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (ano,))
        conn.commit()
        conn.close()

