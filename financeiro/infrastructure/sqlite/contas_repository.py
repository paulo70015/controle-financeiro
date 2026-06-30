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

    def delete_deposito_matching(
        self,
        ano: int,
        mes: int,
        conta_id: int,
        valor: float,
        nota: str,
    ) -> int:
        """
        Apaga UM depósito que casa exatamente com (ano, mes, conta_id, valor, nota).
        Usada para reverter o reflexo automático de um rendimento. Se o usuário
        editou o depósito no modal de detalhes da conta, o match falha e nada
        é removido (permanece para edição/remoção manual). Retorna a qtd
        removida (0 ou 1).
        """
        conn = self.connection_factory(auto_sync=True)
        row = conn.execute(
            """SELECT id FROM depositos_conta
               WHERE ano=? AND mes=? AND conta_id=? AND valor=? AND COALESCE(nota,'')=?
               ORDER BY id DESC LIMIT 1""",
            (ano, mes, conta_id, valor, nota or ""),
        ).fetchone()
        if not row:
            conn.close()
            return 0
        conn.execute("DELETE FROM depositos_conta WHERE id=?", (row["id"],))
        conn.commit()
        conn.close()
        return 1

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

    def save_movimentacao(self, movimentacao: MovimentacaoMensal, movimentacao_id: int | None = None) -> int:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (movimentacao.ano,))
        if movimentacao_id:
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
            saved_id = movimentacao_id
        else:
            cur = conn.execute(
                "INSERT INTO movimentacoes_mensais(ano,mes,conta_id,valor,nota,tipo) VALUES(?,?,?,?,?,?)",
                (
                    movimentacao.ano,
                    movimentacao.mes,
                    movimentacao.conta_id,
                    movimentacao.valor,
                    movimentacao.nota,
                    movimentacao.tipo or "",
                ),
            )
            saved_id = cur.lastrowid
        conn.commit()
        conn.close()
        return saved_id

    def delete_movimentacao_matching(
        self,
        ano: int,
        mes: int,
        conta_id: int,
        valor: float,
        nota: str,
        tipo: str = "",
    ) -> int:
        """
        Apaga UMA movimentação que casa exatamente com (ano, mes, conta_id, valor, nota, tipo).
        Usada para reverter o reflexo automático de um rendimento. Se o usuário
        editou a movimentação no modal de detalhes da conta, o match falha e nada
        é removido (ela permanece para edição/remoção manual). Retorna a qtd
        removida (0 ou 1).
        """
        conn = self.connection_factory(auto_sync=True)
        row = conn.execute(
            """SELECT id FROM movimentacoes_mensais
               WHERE ano=? AND mes=? AND conta_id=? AND valor=? AND COALESCE(nota,'')=? AND COALESCE(tipo,'')=?
               ORDER BY id DESC LIMIT 1""",
            (ano, mes, conta_id, valor, nota or "", tipo or ""),
        ).fetchone()
        if not row:
            conn.close()
            return 0
        conn.execute("DELETE FROM movimentacoes_mensais WHERE id=?", (row["id"],))
        conn.commit()
        conn.close()
        return 1

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
