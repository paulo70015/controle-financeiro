class SQLiteHomeRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def get_anos(self):
        conn = self.connection_factory()
        anos = set(
            [r[0] for r in conn.execute("SELECT DISTINCT ano FROM despesas").fetchall()]
            + [r[0] for r in conn.execute("SELECT DISTINCT ano FROM receitas").fetchall()]
            + [r[0] for r in conn.execute("SELECT DISTINCT ano FROM categorias").fetchall()]
        )
        conn.close()
        return anos

