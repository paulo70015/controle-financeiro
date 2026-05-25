from financeiro.domain.planejamento.entities import Fixa, Meta, PagamentoStatus


class SQLitePlanejamentoRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def _is_fixa_expirada(self, dia_fixa, ano_status, mes_status, dia_inicio=25) -> bool:
        """
        Mesma lógica do JS isFixaExpirada:
        - O mês fiscal (competência) começa no dia dia_inicio
        - Antes do fechamento: mesFiscal = mesAtual + 1
        - Depois do fechamento: mesFiscal = mesAtual + 2
        """
        from datetime import datetime
        hoje = datetime.now()
        dia_atual = hoje.day
        mes_atual = hoje.month
        ano_atual = hoje.year

        mes_fiscal = mes_atual + 1
        ano_fiscal = ano_atual

        if dia_atual >= dia_inicio:
            mes_fiscal = mes_atual + 2

        if mes_fiscal > 12:
            mes_fiscal -= 12
            ano_fiscal += 1

        if ano_status < ano_fiscal:
            return True
        if ano_status > ano_fiscal:
            return False
        if mes_status < mes_fiscal:
            return True
        if mes_status > mes_fiscal:
            return False

        # Estamos no mês fiscal atual — verificar dia da fixa
        try:
            dia = int(dia_fixa) if dia_fixa else 0
            if dia <= 0:
                return False

            if dia_atual < dia_inicio:
                if dia >= dia_inicio:
                    return True  # Aconteceu no mês passado
                if dia <= dia_atual:
                    return True  # Aconteceu neste mês até hoje
            else:
                if dia >= dia_inicio and dia <= dia_atual:
                    return True  # Aconteceu neste ciclo fiscal
        except Exception:
            pass

        return False

    def _normalizar_cat_id(self, conn, cat_id, ano):
        if not cat_id:
            return None
        try:
            cat_id = int(cat_id)
        except Exception:
            return None

        cat = conn.execute(
            "SELECT id, nome, ano FROM categorias WHERE id=?",
            (cat_id,),
        ).fetchone()
        if not cat:
            return None
        if cat["ano"] == ano:
            return cat["id"]

        # Corrige IDs de categoria vindos de outro ano (mesmo nome).
        cat_dest = conn.execute(
            "SELECT id FROM categorias WHERE ano=? AND nome=?",
            (ano, cat["nome"]),
        ).fetchone()
        return cat_dest["id"] if cat_dest else None

    def add_fixa(self, fixa: Fixa) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (fixa.ano,))
        cat_id = self._normalizar_cat_id(conn, fixa.cat_id, fixa.ano)
        conn.execute(
            "INSERT INTO despesas_fixas_cartao(descricao,valor,dia,cat_id,ano) VALUES(?,?,?,?,?)",
            (fixa.descricao, fixa.valor, fixa.dia, cat_id, fixa.ano),
        )
        conn.commit()
        conn.close()

    def update_fixa(self, fixa_id: int, payload: dict) -> None:
        conn = self.connection_factory(auto_sync=True)
        fixa = conn.execute("SELECT ano FROM despesas_fixas_cartao WHERE id=?", (fixa_id,)).fetchone()
        ano_fixa = fixa["ano"] if fixa else None
        cat_id = self._normalizar_cat_id(conn, payload.get("cat_id"), ano_fixa) if ano_fixa else None
        conn.execute(
            "UPDATE despesas_fixas_cartao SET descricao=?, dia=?, valor=?, cat_id=? WHERE id=?",
            (
                payload["descricao"],
                payload.get("dia", 0),
                payload["valor"],
                cat_id,
                fixa_id,
            ),
        )
        conn.commit()
        conn.close()

    def delete_fixa(self, fixa_id: int) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM despesas_fixas_cartao WHERE id=?", (fixa_id,))
        conn.commit()
        conn.close()

    def add_meta(self, meta: Meta) -> None:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (meta.ano_meta,))
        if meta.ano_criacao != meta.ano_meta:
            conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (meta.ano_criacao,))
        conn.execute(
            "INSERT INTO metas(descricao,valor,ano_meta,ano_criacao) VALUES(?,?,?,?)",
            (meta.descricao, meta.valor, meta.ano_meta, meta.ano_criacao),
        )
        conn.commit()
        conn.close()

    def update_meta(self, meta_id: int, payload: dict, method: str) -> None:
        conn = self.connection_factory(auto_sync=True)
        if method == "DELETE":
            conn.execute("DELETE FROM metas WHERE id=?", (meta_id,))
        else:
            if "concluida" in payload:
                conn.execute("UPDATE metas SET concluida=? WHERE id=?", (payload["concluida"], meta_id))
            else:
                conn.execute(
                    "UPDATE metas SET descricao=?, valor=?, ano_meta=? WHERE id=?",
                    (payload["descricao"], payload["valor"], payload["ano_meta"], meta_id),
                )
        conn.commit()
        conn.close()

    def toggle_fixa_excecao(self, payload: dict, method: str) -> None:
        conn = self.connection_factory(auto_sync=True)
        if method == "POST":
            conn.execute(
                "INSERT OR IGNORE INTO fixas_excecoes(ano,mes,cat_id) VALUES(?,?,?)",
                (payload["ano"], payload["mes"], payload["cat_id"]),
            )
        else:
            conn.execute(
                "DELETE FROM fixas_excecoes WHERE ano=? AND mes=? AND cat_id=?",
                (payload["ano"], payload["mes"], payload["cat_id"]),
            )
            cat = conn.execute("SELECT nome FROM categorias WHERE id=?", (payload["cat_id"],)).fetchone()
            if cat:
                ids = [
                    r["id"]
                    for r in conn.execute(
                        "SELECT id FROM despesas WHERE ano=? AND mes=? AND categoria=? AND nota='Soma das Despesas Fixas\u200b'",
                        (payload["ano"], payload["mes"], cat["nome"]),
                    ).fetchall()
                ]
                for did in ids:
                    conn.execute("DELETE FROM depositos_conta WHERE despesa_id=?", (did,))
                    conn.execute("DELETE FROM despesas WHERE id=?", (did,))
        conn.commit()
        conn.close()

    def save_pagamento_status(self, status: PagamentoStatus) -> None:
        conn = self.connection_factory(auto_sync=True)
        row_status = conn.execute(
            "SELECT status FROM pagamento_status WHERE ano=? AND mes=? AND categoria=?",
            (status.ano, status.mes, status.categoria),
        ).fetchone()
        status_atual = row_status["status"] if row_status else 0

        if status.status == 0:
            conn.execute(
                "DELETE FROM pagamento_status WHERE ano=? AND mes=? AND categoria=?",
                (status.ano, status.mes, status.categoria),
            )
            cat = conn.execute(
                "SELECT id FROM categorias WHERE nome=? AND ano=?",
                (status.categoria, status.ano),
            ).fetchone()
            if cat:
                conn.execute(
                    "DELETE FROM fixas_excecoes WHERE ano=? AND mes=? AND cat_id=?",
                    (status.ano, status.mes, cat["id"]),
                )
            ids = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM despesas WHERE ano=? AND mes=? AND categoria=? AND nota='Soma das Despesas Fixas\u200b'",
                    (status.ano, status.mes, status.categoria),
                ).fetchall()
            ]
            for did in ids:
                conn.execute("DELETE FROM depositos_conta WHERE despesa_id=?", (did,))
                conn.execute("DELETE FROM despesas WHERE id=?", (did,))
        else:
            conn.execute(
                "INSERT INTO pagamento_status(ano,mes,categoria,status) VALUES(?,?,?,?) "
                "ON CONFLICT(ano,mes,categoria) DO UPDATE SET status=excluded.status",
                (status.ano, status.mes, status.categoria, status.status),
            )

        if status_atual == 0 and status.status > 0:
            cat = conn.execute(
                "SELECT id, inclui_fixas, conta_vinculada_id FROM categorias WHERE nome=? AND ano=?",
                (status.categoria, status.ano),
            ).fetchone()
            if cat:
                cat_id = cat["id"]
                exc = conn.execute(
                    "SELECT 1 FROM fixas_excecoes WHERE ano=? AND mes=? AND cat_id=?",
                    (status.ano, status.mes, cat_id),
                ).fetchone()
                if not exc:
                    if cat["inclui_fixas"]:
                        fixas = conn.execute(
                            "SELECT * FROM despesas_fixas_cartao WHERE ativa=1 AND ano=? AND (cat_id=? OR cat_id IS NULL)",
                            (status.ano, cat_id),
                        ).fetchall()
                    else:
                        fixas = conn.execute(
                            "SELECT * FROM despesas_fixas_cartao WHERE ativa=1 AND ano=? AND cat_id=?",
                            (status.ano, cat_id),
                        ).fetchall()
                    if fixas:
                        # Ler dia_inicio_mes_fiscal da config
                        cfg_row = conn.execute(
                            "SELECT valor FROM config WHERE chave='dia_inicio_mes_fiscal'"
                        ).fetchone()
                        dia_inicio = int(cfg_row["valor"]) if cfg_row else 25

                        total_fixas = 0
                        for f in fixas:
                            if not self._is_fixa_expirada(f["dia"], status.ano, status.mes, dia_inicio):
                                total_fixas += f["valor"]
                                
                        total_fixas = round(total_fixas, 2)
                        if total_fixas != 0:
                            nota_fixa = "Soma das Despesas Fixas\u200b"
                            cur_desp = conn.execute(
                                "INSERT INTO despesas(ano,mes,categoria,valor,nota) VALUES(?,?,?,?,?)",
                                (status.ano, status.mes, status.categoria, total_fixas, nota_fixa),
                            )
                            if cat["conta_vinculada_id"]:
                                conn.execute(
                                    "INSERT INTO depositos_conta(ano,mes,conta_id,valor,nota,despesa_id) VALUES(?,?,?,?,?,?)",
                                    (
                                        status.ano,
                                        status.mes,
                                        cat["conta_vinculada_id"],
                                        -total_fixas,
                                        nota_fixa,
                                        cur_desp.lastrowid,
                                    ),
                                )
                        conn.execute(
                            "INSERT INTO fixas_excecoes(ano,mes,cat_id) VALUES(?,?,?)",
                            (status.ano, status.mes, cat_id),
                        )

        conn.commit()
        conn.close()

    def toggle_fixa_aplicada_manual(self, payload: dict, method: str) -> None:
        conn = self.connection_factory(auto_sync=True)
        if method == "POST":
            conn.execute(
                "INSERT OR IGNORE INTO fixas_aplicadas_manual(ano,mes,fixa_id) VALUES(?,?,?)",
                (payload["ano"], payload["mes"], payload["fixa_id"]),
            )
        else:
            conn.execute(
                "DELETE FROM fixas_aplicadas_manual WHERE ano=? AND mes=? AND fixa_id=?",
                (payload["ano"], payload["mes"], payload["fixa_id"]),
            )
        conn.commit()
        conn.close()
