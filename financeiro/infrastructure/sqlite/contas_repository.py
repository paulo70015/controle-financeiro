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

    def ano_existe(self, ano: int) -> bool:
        """Verifica se o ano existe na tabela `anos` (fonte da verdade)."""
        conn = self.connection_factory()
        row = conn.execute("SELECT 1 FROM anos WHERE ano=? LIMIT 1", (ano,)).fetchone()
        conn.close()
        return row is not None

    def delete_conta(self, conta_id: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM contas_correntes WHERE id=?", (conta_id,))
        conn.execute("DELETE FROM depositos_conta WHERE conta_id=?", (conta_id,))
        conn.execute("DELETE FROM movimentacoes_mensais WHERE conta_id=?", (conta_id,))
        conn.execute(
            "UPDATE categorias SET conta_vinculada_id=NULL WHERE conta_vinculada_id=?",
            (conta_id,),
        )
        conn.execute(
            "UPDATE rendimentos_locais SET conta_vinculada_id=NULL WHERE conta_vinculada_id=?",
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

    def _update_movimentacao(self, conn, movimentacao: MovimentacaoMensal, movimentacao_id: int) -> None:
        conn.execute(
            """UPDATE movimentacoes_mensais
            SET ano=?, mes=?, conta_id=?, valor=?, nota=?, tipo=?
            WHERE id=?""",
            (
                movimentacao.ano,
                movimentacao.mes,
                movimentacao.conta_id,
                movimentacao.valor,
                movimentacao.nota,
                movimentacao.tipo or "",
                movimentacao_id,
            ),
        )

    def _insert_movimentacao(self, conn, movimentacao: MovimentacaoMensal, lancamento_id: int | None = None) -> int:
        cur = conn.execute(
            """INSERT INTO movimentacoes_mensais(ano,mes,conta_id,valor,nota,tipo,rendimento_lancamento_id)
            VALUES(?,?,?,?,?,?,?)""",
            (
                movimentacao.ano,
                movimentacao.mes,
                movimentacao.conta_id,
                movimentacao.valor,
                movimentacao.nota,
                movimentacao.tipo or "",
                lancamento_id,
            ),
        )
        return cur.lastrowid

    def save_movimentacao(self, movimentacao: MovimentacaoMensal, movimentacao_id: int | None = None) -> int:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (movimentacao.ano,))
        if movimentacao_id:
            self._update_movimentacao(conn, movimentacao, movimentacao_id)
            saved_id = movimentacao_id
        else:
            saved_id = self._insert_movimentacao(conn, movimentacao)
        conn.commit()
        conn.close()
        return saved_id

    def save_movimentacao_reflexo(self, lancamento_id: int, movimentacao: MovimentacaoMensal) -> int:
        """
        Insere ou atualiza a movimentação refletida de um lançamento da aba
        Rendimentos, identificada por `rendimento_lancamento_id`. Upsert
        idempotente: editar o lançamento apenas atualiza a movimentação.
        """
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (movimentacao.ano,))
        row = conn.execute(
            "SELECT id FROM movimentacoes_mensais WHERE rendimento_lancamento_id=?",
            (lancamento_id,),
        ).fetchone()
        if row:
            self._update_movimentacao(conn, movimentacao, row["id"])
            saved_id = row["id"]
        else:
            saved_id = self._insert_movimentacao(conn, movimentacao, lancamento_id)
        conn.commit()
        conn.close()
        return saved_id

    def delete_movimentacao_reflexo(self, lancamento_id: int) -> None:
        """Remove a movimentação refletida de um lançamento de rendimento."""
        conn = self.connection_factory(auto_sync=True)
        conn.execute(
            "DELETE FROM movimentacoes_mensais WHERE rendimento_lancamento_id=?",
            (lancamento_id,),
        )
        conn.commit()
        conn.close()

    def delete_movimentacao(self, movimentacao_id: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM movimentacoes_mensais WHERE id=?", (movimentacao_id,))
        conn.commit()
        conn.close()

    def delete_movimentacoes_mes(self, ano: int, mes: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM movimentacoes_mensais WHERE ano=? AND mes=?", (ano, mes))
        conn.commit()
        conn.close()
