from typing import Optional

from financeiro.domain.rendimentos.entities import RendimentoLancamento, RendimentoLocal


class SQLiteRendimentosRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def get_locais(self, ano: int) -> list[dict]:
        conn = self.connection_factory()
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT id,ano,nome,ordem,projecao_taxa FROM rendimentos_locais WHERE ano=? ORDER BY ordem,id",
                (ano,),
            ).fetchall()
        ]
        conn.close()
        return rows

    def add_local(self, local: RendimentoLocal) -> int:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (local.ano,))
        prox_ordem = conn.execute(
            "SELECT COALESCE(MAX(ordem), 0) + 1 AS prox FROM rendimentos_locais WHERE ano=?",
            (local.ano,),
        ).fetchone()["prox"]
        cur = conn.execute(
            "INSERT INTO rendimentos_locais(ano,nome,ordem) VALUES(?,?,?)",
            (local.ano, local.nome, prox_ordem),
        )
        conn.commit()
        local_id = cur.lastrowid
        conn.close()
        return local_id

    def update_local(self, local_id: int, nome: str) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("UPDATE rendimentos_locais SET nome=? WHERE id=?", (nome, local_id))
        conn.commit()
        conn.close()

    def update_projecao_taxa(self, local_id: int, taxa: Optional[float]) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute(
            "UPDATE rendimentos_locais SET projecao_taxa=? WHERE id=?", (taxa, local_id)
        )
        conn.commit()
        conn.close()

    def delete_local(self, local_id: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM rendimentos_lancamentos WHERE local_id=?", (local_id,))
        conn.execute("DELETE FROM rendimentos_locais WHERE id=?", (local_id,))
        conn.commit()
        conn.close()

    def delete_lancamentos_local_ano(self, ano: int, local_id: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute(
            "DELETE FROM rendimentos_lancamentos WHERE ano=? AND local_id=?",
            (ano, local_id),
        )
        conn.execute(
            "UPDATE rendimentos_locais SET projecao_taxa=NULL WHERE id=?", (local_id,)
        )
        conn.commit()
        conn.close()

    def get_lancamentos_detalhe(self, ano: int, mes: int, local_id: int) -> list[dict]:
        conn = self.connection_factory()
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT id,ano,mes,local_id,tipo,valor,nota,data_alteracao FROM rendimentos_lancamentos WHERE ano=? AND mes=? AND local_id=? ORDER BY id DESC",
                (ano, mes, local_id),
            ).fetchall()
        ]
        conn.close()
        return rows

    def add_lancamento(self, lanc: RendimentoLancamento) -> int:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (lanc.ano,))
        cur = conn.execute(
            "INSERT INTO rendimentos_lancamentos(ano,mes,local_id,tipo,valor,nota,data_alteracao) VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (lanc.ano, lanc.mes, lanc.local_id, lanc.tipo, lanc.valor, lanc.nota),
        )
        conn.commit()
        lancamento_id = cur.lastrowid
        conn.close()
        return lancamento_id

    def update_lancamento(self, lancamento_id: int, tipo: str, valor: float, nota: str) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute(
            "UPDATE rendimentos_lancamentos SET tipo=?, valor=?, nota=?, data_alteracao=CURRENT_TIMESTAMP WHERE id=?",
            (tipo, valor, nota, lancamento_id),
        )
        conn.commit()
        conn.close()

    def delete_lancamento(self, lancamento_id: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM rendimentos_lancamentos WHERE id=?", (lancamento_id,))
        conn.commit()
        conn.close()

    def reorder_locais(self, ordem_ids: list[int]) -> None:
        conn = self.connection_factory(auto_sync=True)
        for i, local_id in enumerate(ordem_ids):
            conn.execute("UPDATE rendimentos_locais SET ordem=? WHERE id=?", (i, local_id))
        conn.commit()
        conn.close()
