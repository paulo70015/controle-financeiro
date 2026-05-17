from financeiro.domain.contas.entities import Conta, DepositoConta, MovimentacaoMensal


class SQLiteContasRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def add_conta(self, conta: Conta) -> None:
        conn = self.connection_factory(auto_sync=True)
        ordem = conn.execute("SELECT COALESCE(MAX(ordem),0) FROM contas_correntes").fetchone()[0]
        conn.execute(
            "INSERT OR IGNORE INTO contas_correntes(nome,ordem,saldo_inicial) VALUES(?,?,?)",
            (conta.nome, ordem + 1, conta.saldo_inicial),
        )
        conn.commit()
        conn.close()

    def update_conta(self, conta_id: int, payload: dict) -> None:
        conn = self.connection_factory(auto_sync=True)
        if "saldo_inicial" in payload:
            conn.execute(
                "UPDATE contas_correntes SET saldo_inicial=? WHERE id=?",
                (float(payload["saldo_inicial"]), conta_id),
            )
        if "nome" in payload and payload["nome"].strip():
            conn.execute(
                "UPDATE contas_correntes SET nome=? WHERE id=?",
                (payload["nome"].strip(), conta_id),
            )
        conn.commit()
        conn.close()

    def delete_conta(self, conta_id: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM contas_correntes WHERE id=?", (conta_id,))
        conn.execute("DELETE FROM depositos_conta WHERE conta_id=?", (conta_id,))
        conn.execute("DELETE FROM movimentacoes_mensais WHERE conta_id=?", (conta_id,))
        conn.execute(
            "UPDATE categorias SET conta_vinculada_id=NULL WHERE conta_vinculada_id=?",
            (conta_id,),
        )
        conn.commit()
        conn.close()

    def add_deposito(self, deposito: DepositoConta) -> int:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (deposito.ano,))
        cur = conn.execute(
            "INSERT INTO depositos_conta(ano,mes,conta_id,valor,nota,despesa_id) VALUES(?,?,?,?,?,NULL)",
            (deposito.ano, deposito.mes, deposito.conta_id, deposito.valor, deposito.nota),
        )
        deposito_id = cur.lastrowid
        conn.commit()
        conn.close()
        return deposito_id

    def update_deposito(self, deposito_id: int, valor: float, nota: str) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute(
            "UPDATE depositos_conta SET valor=?, nota=? WHERE id=?",
            (valor, nota, deposito_id),
        )
        conn.commit()
        conn.close()

    def delete_deposito(self, deposito_id: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM depositos_conta WHERE id=?", (deposito_id,))
        conn.commit()
        conn.close()

    def get_depositos_detalhe(self, ano: int, mes: int, conta_id: int) -> list[dict]:
        conn = self.connection_factory()
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM depositos_conta WHERE ano=? AND mes=? AND conta_id=?",
                (ano, mes, conta_id),
            ).fetchall()
        ]
        conn.close()
        return rows

    def upsert_movimentacao(self, movimentacao: MovimentacaoMensal) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (movimentacao.ano,))
        conn.execute(
            """INSERT INTO movimentacoes_mensais(ano,mes,conta_id,valor,nota)
            VALUES(?,?,?,?,?)
            ON CONFLICT(ano,mes) DO UPDATE SET conta_id=excluded.conta_id,
            valor=excluded.valor, nota=excluded.nota""",
            (
                movimentacao.ano,
                movimentacao.mes,
                movimentacao.conta_id,
                movimentacao.valor,
                movimentacao.nota,
            ),
        )
        conn.commit()
        conn.close()

    def delete_movimentacao(self, ano: int, mes: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM movimentacoes_mensais WHERE ano=? AND mes=?", (ano, mes))
        conn.commit()
        conn.close()
