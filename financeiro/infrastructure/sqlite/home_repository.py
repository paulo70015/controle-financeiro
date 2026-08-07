from financeiro.infrastructure.sqlite.anos_utils import descobrir_anos


class SQLiteHomeRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def get_anos(self):
        conn = self.connection_factory()
        anos_set = descobrir_anos(conn)
        conn.close()
        return anos_set

    def ensure_year_exists(self, ano: int) -> None:
        """Garante que o ano existe na tabela `anos` (idempotente)."""
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (ano,))
        conn.commit()
        conn.close()
