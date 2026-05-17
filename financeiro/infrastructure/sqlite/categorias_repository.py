from financeiro.domain.categorias.entities import Categoria


class SQLiteCategoriasRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def add_categoria(self, categoria: Categoria) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (categoria.ano,))
        ultima_ordem = (
            conn.execute(
                "SELECT MAX(ordem) FROM categorias WHERE ano=?",
                (categoria.ano,),
            ).fetchone()[0]
            or 0
        )
        conn.execute(
            "INSERT INTO categorias(nome,ordem,inclui_fixas,conta_vinculada_id,ano,is_cartao,tooltip) VALUES(?,?,?,?,?,?,?)",
            (
                categoria.nome,
                ultima_ordem + 1,
                categoria.inclui_fixas,
                categoria.conta_vinculada_id,
                categoria.ano,
                categoria.is_cartao,
                categoria.tooltip,
            ),
        )
        conn.commit()
        conn.close()

    def update_categoria(self, categoria_id: int, payload: dict) -> bool:
        conn = self.connection_factory(auto_sync=True)
        novo_nome = payload.get("nome", "").strip()
        row = conn.execute(
            "SELECT nome, ano FROM categorias WHERE id=?",
            (categoria_id,),
        ).fetchone()
        if not row:
            conn.close()
            return False
        if novo_nome and novo_nome != row["nome"]:
            conn.execute("UPDATE categorias SET nome=? WHERE id=?", (novo_nome, categoria_id))
            conn.execute(
                "UPDATE despesas SET categoria=? WHERE categoria=? AND ano=?",
                (novo_nome, row["nome"], row["ano"]),
            )
            conn.execute(
                "UPDATE pagamento_status SET categoria=? WHERE categoria=? AND ano=?",
                (novo_nome, row["nome"], row["ano"]),
            )
        if "inclui_fixas" in payload:
            conn.execute(
                "UPDATE categorias SET inclui_fixas=? WHERE id=?",
                (1 if payload["inclui_fixas"] else 0, categoria_id),
            )
        if "is_cartao" in payload:
            conn.execute(
                "UPDATE categorias SET is_cartao=? WHERE id=?",
                (1 if payload["is_cartao"] else 0, categoria_id),
            )
        if "tooltip" in payload:
            conn.execute(
                "UPDATE categorias SET tooltip=? WHERE id=?",
                (payload["tooltip"], categoria_id),
            )
        if "conta_vinculada_id" in payload:
            conta_id = payload["conta_vinculada_id"] if payload["conta_vinculada_id"] else None
            conn.execute(
                "UPDATE categorias SET conta_vinculada_id=? WHERE id=?",
                (conta_id, categoria_id),
            )
        conn.commit()
        conn.close()
        return True

    def delete_categoria(self, categoria_id: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        row = conn.execute(
            "SELECT nome, ano FROM categorias WHERE id=?",
            (categoria_id,),
        ).fetchone()
        if row:
            nome = row["nome"]
            ano = row["ano"]
            ids_despesas = [
                r[0]
                for r in conn.execute(
                    "SELECT id FROM despesas WHERE categoria=? AND ano=?",
                    (nome, ano),
                ).fetchall()
            ]
            for despesa_id in ids_despesas:
                conn.execute("DELETE FROM depositos_conta WHERE despesa_id=?", (despesa_id,))
            conn.execute("DELETE FROM despesas WHERE categoria=? AND ano=?", (nome, ano))
            conn.execute(
                "UPDATE despesas_fixas_cartao SET cat_id=NULL WHERE cat_id=? AND ano=?",
                (categoria_id, ano),
            )
            conn.execute("DELETE FROM categorias WHERE id=?", (categoria_id,))
        conn.commit()
        conn.close()

    def move_categoria(self, categoria_id: int, direcao: str) -> bool:
        conn = self.connection_factory(auto_sync=True)
        row_ano = conn.execute(
            "SELECT ano FROM categorias WHERE id=?",
            (categoria_id,),
        ).fetchone()
        if not row_ano:
            conn.close()
            return False
        ano = row_ano["ano"]
        rows = conn.execute(
            "SELECT id,ordem FROM categorias WHERE ano=? ORDER BY ordem",
            (ano,),
        ).fetchall()
        ids = [r["id"] for r in rows]
        ordens = [r["ordem"] for r in rows]
        if categoria_id not in ids:
            conn.close()
            return False
        idx = ids.index(categoria_id)
        swap = idx - 1 if direcao == "cima" else idx + 1
        if 0 <= swap < len(ids):
            conn.execute("UPDATE categorias SET ordem=? WHERE id=?", (ordens[swap], ids[idx]))
            conn.execute("UPDATE categorias SET ordem=? WHERE id=?", (ordens[idx], ids[swap]))
        conn.commit()
        conn.close()
        return True

    def reorder_categorias(self, ordem_ids: list[int]) -> None:
        conn = self.connection_factory(auto_sync=True)
        for i, categoria_id in enumerate(ordem_ids):
            conn.execute("UPDATE categorias SET ordem=? WHERE id=?", (i, categoria_id))
        conn.commit()
        conn.close()

    def get_conta_vinculada(self, categoria: str, ano: int) -> int | None:
        """Retorna o ID da conta vinculada à categoria, ou None."""
        conn = self.connection_factory()
        row = conn.execute(
            "SELECT conta_vinculada_id FROM categorias WHERE nome=? AND ano=?",
            (categoria, ano),
        ).fetchone()
        conn.close()
        return row["conta_vinculada_id"] if row and row["conta_vinculada_id"] else None
