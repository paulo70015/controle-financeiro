from financeiro.domain.planejamento.entities import Fixa, Meta, PagamentoStatus


class SQLitePlanejamentoRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def _is_fixa_expirada(self, dia_fixa, ano_status, mes_status) -> bool:
        from datetime import datetime
        hoje = datetime.now()
        ano_atual = hoje.year
        mes_atual = hoje.month + 1
        if mes_atual > 12:
            mes_atual = 1
            ano_atual += 1
        dia_atual = hoje.day

        if ano_status < ano_atual:
            return True
        if ano_status == ano_atual:
            if mes_status < mes_atual:
                return True
            if mes_status == mes_atual:
                try:
                    dia = int(dia_fixa) if dia_fixa else 0
                    if 0 < dia < dia_atual:
                        return True
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
        try:
            self._save_pagamento_status_conn(conn, status)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_pagamento_status_lote(self, statuses: list[PagamentoStatus]) -> None:
        conn = self.connection_factory(auto_sync=True)
        try:
            for status in statuses:
                self._save_pagamento_status_conn(conn, status)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _save_pagamento_status_conn(self, conn, status: PagamentoStatus) -> None:
        """Operacao atomica de dominio (planejamento).

        Persiste o status de pagamento de uma celula (ano, mes, categoria) e
        aplica em cascata, dentro da MESMA transacao SQLite, os efeitos
        derivados sobre `despesas`, `depositos_conta` e `fixas_excecoes`.

        Justificativa para manter a orquestracao no repositorio (e nao em
        `application/use_cases.py`): o conjunto de operacoes precisa ser
        atomico — qualquer falha intermediaria deve reverter tudo. O projeto
        ainda nao possui Unit-of-Work compartilhada entre repositorios,
        portanto extrair a orquestracao para o use case quebraria a
        atomicidade transacional. Quando uma UoW for introduzida, esta logica
        deve migrar para o use case correspondente.
        """
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
                        total_fixas = 0
                        for f in fixas:
                            if not self._is_fixa_expirada(f["dia"], status.ano, status.mes):
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
