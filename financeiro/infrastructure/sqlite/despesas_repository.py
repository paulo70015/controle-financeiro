from financeiro.domain.despesas.entities import Despesa, DespesaLote


class SQLiteDespesasRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def add_despesa(self, despesa: Despesa) -> int:
        """Insere despesa e retorna o ID. Persistência pura."""
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (despesa.ano,))
        cur = conn.execute(
            "INSERT INTO despesas(ano,mes,categoria,valor,nota,ignorar_total,data_alteracao) VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (despesa.ano, despesa.mes, despesa.categoria, despesa.valor, despesa.nota, getattr(despesa, "ignorar_total", False)),
        )
        despesa_id = cur.lastrowid
        conn.commit()
        conn.close()
        return despesa_id

    def add_deposito_vinculado_simples(
        self,
        ano: int,
        mes: int,
        conta_id: int,
        valor: float,
        nota: str,
        despesa_id: int,
    ) -> None:
        """Insere depósito vinculado a uma despesa. Persistência pura."""
        conn = self.connection_factory(auto_sync=True)
        conn.execute(
            "INSERT INTO depositos_conta(ano,mes,conta_id,valor,nota,despesa_id) VALUES(?,?,?,?,?,?)",
            (ano, mes, conta_id, valor, nota, despesa_id),
        )
        conn.commit()
        conn.close()

    def add_despesa_lote_com_depositos(
        self,
        despesas_data: list[dict],
        depositos_data: list[dict],
    ) -> list[int]:
        """Insere lote de despesas e depósitos em transação atômica. Retorna IDs."""
        conn = self.connection_factory(auto_sync=True)
        
        try:
            # Garantir que todos os anos existem na tabela `anos`
            for desp in despesas_data:
                conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (desp['ano'],))
            # Inserir despesas e coletar IDs
            despesa_ids = []
            for desp in despesas_data:
                cur = conn.execute(
                    "INSERT INTO despesas(ano,mes,categoria,valor,nota,ignorar_total,data_alteracao) VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                    (desp['ano'], desp['mes'], desp['categoria'], desp['valor'], desp['nota'], desp['ignorar_total']),
                )
                despesa_ids.append(cur.lastrowid)
            
            # Inserir depósitos vinculados
            for dep in depositos_data:
                idx = dep.get('despesa_idx')
                desp_id = despesa_ids[idx] if idx is not None else None
                conn.execute(
                    "INSERT INTO depositos_conta(ano,mes,conta_id,valor,nota,despesa_id) VALUES(?,?,?,?,?,?)",
                    (dep['ano'], dep['mes'], dep['conta_id'], dep['valor'], dep['nota'], desp_id),
                )
            
            conn.commit()
            return despesa_ids
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_despesa_by_id(self, despesa_id: int) -> dict | None:
        """Retorna dados da despesa por ID."""
        conn = self.connection_factory()
        row = conn.execute(
            "SELECT ano, mes, categoria, valor, nota, ignorar_total FROM despesas WHERE id=?",
            (despesa_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def update_despesa_com_deposito(
        self,
        despesa_id: int,
        valor: float,
        nota: str,
        ignorar_total: bool,
        conta_id: int | None,
        ano: int,
        mes: int,
        categoria: str,
    ) -> None:
        """Atualiza despesa e recria depósito vinculado se aplicável."""
        conn = self.connection_factory(auto_sync=True)
        
        try:
            # Atualizar despesa
            conn.execute(
                "UPDATE despesas SET mes=?, valor=?, nota=?, ignorar_total=?, data_alteracao=CURRENT_TIMESTAMP WHERE id=?",
                (mes, valor, nota, ignorar_total, despesa_id),
            )
            
            # Remover depósito antigo
            conn.execute("DELETE FROM depositos_conta WHERE despesa_id=?", (despesa_id,))
            
            # Recriar depósito se aplicável
            if conta_id and not ignorar_total and valor > 0:
                conn.execute(
                    "INSERT INTO depositos_conta(ano,mes,conta_id,valor,nota,despesa_id) VALUES(?,?,?,?,?,?)",
                    (ano, mes, conta_id, -valor, nota or categoria, despesa_id),
                )
            
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_despesa(self, despesa_id: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM depositos_conta WHERE despesa_id=?", (despesa_id,))
        conn.execute("DELETE FROM despesas WHERE id=?", (despesa_id,))
        conn.commit()
        conn.close()

    def get_despesas_detalhe(self, ano: int, mes: int, categoria: str) -> list[dict]:
        conn = self.connection_factory()
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM despesas WHERE ano=? AND mes=? AND categoria=?",
                (ano, mes, categoria),
            ).fetchall()
        ]
        conn.close()
        return rows

    def delete_despesas_da_categoria_no_ano(self, ano: int, categoria: str) -> None:
        conn = self.connection_factory(auto_sync=True)
        ids = [
            r[0]
            for r in conn.execute(
                "SELECT id FROM despesas WHERE ano=? AND categoria=?",
                (ano, categoria),
            ).fetchall()
        ]
        for despesa_id in ids:
            conn.execute("DELETE FROM depositos_conta WHERE despesa_id=?", (despesa_id,))
        conn.execute(
            "DELETE FROM despesas WHERE ano=? AND categoria=?",
            (ano, categoria),
        )
        conn.commit()
        conn.close()
