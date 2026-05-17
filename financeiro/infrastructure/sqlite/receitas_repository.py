from financeiro.domain.receitas.entities import Receita, ReceitaLote


class SQLiteReceitasRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def add_receita(self, receita: Receita) -> int:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (receita.ano,))
        cur = conn.execute(
            "INSERT INTO receitas(ano,mes,descricao,valor,nota,data_alteracao) VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)",
            (receita.ano, receita.mes, receita.descricao, receita.valor, receita.nota),
        )
        receita_id = cur.lastrowid
        conn.commit()
        conn.close()
        return receita_id

    def get_receitas_mes(self, ano: int, mes: int) -> list[dict]:
        conn = self.connection_factory()
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM receitas WHERE ano=? AND mes=?",
                (ano, mes),
            ).fetchall()
        ]
        conn.close()
        return rows

    def update_receita(self, receita_id: int, valor: float, nota: str, descricao: str, mes: int | None = None) -> None:
        conn = self.connection_factory(auto_sync=True)
        if mes is None:
            row = conn.execute("SELECT mes FROM receitas WHERE id=?", (receita_id,)).fetchone()
            mes = int(row["mes"]) if row else None
        conn.execute(
            "UPDATE receitas SET mes=?, valor=?, nota=?, descricao=?, data_alteracao=CURRENT_TIMESTAMP WHERE id=?",
            (mes, valor, nota, descricao, receita_id),
        )
        conn.commit()
        conn.close()

    def delete_receita(self, receita_id: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM receitas WHERE id=?", (receita_id,))
        conn.commit()
        conn.close()

    def add_receita_lote(self, lote: ReceitaLote, meses: list[int]) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (lote.ano,))
        for i, mes in enumerate(meses):
            valor = round(lote.valor_base + (lote.acrescimo * i), 2)
            conn.execute(
                "INSERT INTO receitas(ano,mes,descricao,valor,nota,data_alteracao) VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)",
                (lote.ano, mes, lote.descricao, valor, lote.nota),
            )
        conn.commit()
        conn.close()

    def delete_receitas_ano(self, ano: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM receitas WHERE ano=?", (ano,))
        conn.commit()
        conn.close()
