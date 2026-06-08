class SQLiteAdminRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def save_config(self, payload: dict) -> None:
        conn = self.connection_factory(auto_sync=True)
        for chave, valor in payload.items():
            conn.execute(
                "INSERT INTO config(chave,valor) VALUES(?,?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
                (chave, str(valor)),
            )
        conn.commit()
        conn.close()

    def duplicate_year(self, ano_origem: int, ano_destino: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        # Garantir que o ano de destino existe na tabela `anos`
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (ano_destino,))
        cat_map = {}
        cats = conn.execute("SELECT * FROM categorias WHERE ano=?", (ano_origem,)).fetchall()
        for c in cats:
            cur = conn.execute(
                "INSERT INTO categorias(nome,ordem,inclui_fixas,conta_vinculada_id,tooltip,ano) VALUES(?,?,?,?,?,?)",
                (c["nome"], c["ordem"], c["inclui_fixas"], c["conta_vinculada_id"], c["tooltip"], ano_destino),
            )
            cat_map[c["id"]] = cur.lastrowid

        fixas = conn.execute("SELECT * FROM despesas_fixas_cartao WHERE ano=?", (ano_origem,)).fetchall()
        for f in fixas:
            new_cat_id = cat_map.get(f["cat_id"]) if f["cat_id"] else None
            conn.execute(
                "INSERT INTO despesas_fixas_cartao(descricao,valor,dia,cat_id,ativa,ano) VALUES(?,?,?,?,?,?)",
                (f["descricao"], f["valor"], f["dia"], new_cat_id, f["ativa"], ano_destino),
            )

        desp = conn.execute("SELECT mes,categoria,valor,nota FROM despesas WHERE ano=?", (ano_origem,)).fetchall()
        for r in desp:
            cur = conn.execute(
                "INSERT INTO despesas(ano,mes,categoria,valor,nota) VALUES(?,?,?,?,?)",
                (ano_destino, r["mes"], r["categoria"], r["valor"], r["nota"]),
            )
            cat = conn.execute(
                "SELECT conta_vinculada_id FROM categorias WHERE nome=? AND ano=?",
                (r["categoria"], ano_destino),
            ).fetchone()
            if cat and cat["conta_vinculada_id"]:
                conn.execute(
                    "INSERT INTO depositos_conta(ano,mes,conta_id,valor,nota,despesa_id) VALUES(?,?,?,?,?,?)",
                    (ano_destino, r["mes"], cat["conta_vinculada_id"], -r["valor"], r["nota"], cur.lastrowid),
                )

        rec = conn.execute("SELECT mes,descricao,valor,nota FROM receitas WHERE ano=?", (ano_origem,)).fetchall()
        for r in rec:
            conn.execute(
                "INSERT INTO receitas(ano,mes,descricao,valor,nota) VALUES(?,?,?,?,?)",
                (ano_destino, r["mes"], r["descricao"], r["valor"], r["nota"]),
            )

        rend_locais_map = {}
        rend_locais = conn.execute(
            "SELECT id,nome,ordem,conta_vinculada_id FROM rendimentos_locais WHERE ano=?",
            (ano_origem,),
        ).fetchall()
        for rl in rend_locais:
            cur = conn.execute(
                "INSERT INTO rendimentos_locais(ano,nome,ordem,conta_vinculada_id) VALUES(?,?,?,?)",
                (ano_destino, rl["nome"], rl["ordem"], rl["conta_vinculada_id"]),
            )
            rend_locais_map[rl["id"]] = cur.lastrowid

        rend_lanc = conn.execute(
            "SELECT mes,local_id,tipo,valor,nota FROM rendimentos_lancamentos WHERE ano=?",
            (ano_origem,),
        ).fetchall()
        for rl in rend_lanc:
            novo_local_id = rend_locais_map.get(rl["local_id"])
            if not novo_local_id:
                continue
            conn.execute(
                "INSERT INTO rendimentos_lancamentos(ano,mes,local_id,tipo,valor,nota) VALUES(?,?,?,?,?,?)",
                (ano_destino, rl["mes"], novo_local_id, rl["tipo"], rl["valor"], rl["nota"]),
            )
        conn.commit()
        conn.close()

    def create_year(self, ano: int) -> None:
        """Registra um ano na tabela `anos` sem duplicar dados."""
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (ano,))
        conn.commit()
        conn.close()

    def year_has_data(self, ano: int) -> bool:
        conn = self.connection_factory()
        try:
            row = conn.execute("SELECT 1 FROM anos WHERE ano=? LIMIT 1", (ano,)).fetchone()
            return row is not None
        finally:
            conn.close()

    def delete_year(self, ano: int) -> None:
        """Remove o ano e TODOS os dados vinculados via ON DELETE CASCADE."""
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM anos WHERE ano=?", (ano,))
        conn.commit()
        conn.close()
