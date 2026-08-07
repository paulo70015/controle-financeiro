from datetime import datetime

from financeiro.infrastructure.sqlite.anos_utils import descobrir_anos


class SQLiteDashboardRepository:
    def __init__(self, connection_factory, meses):
        self.connection_factory = connection_factory
        self.meses = meses

    def get_dados_ano(self, ano: int) -> dict:
        conn = self.connection_factory(auto_sync=True)
        conn.execute("PRAGMA group_concat_max_len = 1000000")
        self._sync_rendimentos_realizados(conn, ano)
        cats = [
            dict(r)
            for r in conn.execute(
                "SELECT id,nome,inclui_fixas,conta_vinculada_id,tooltip,is_cartao FROM categorias WHERE ano=? ORDER BY ordem",
                (ano,),
            ).fetchall()
        ]

        desp_rows = conn.execute(
            """SELECT mes,categoria,
               SUM(CASE WHEN ignorar_total = 1 THEN 0 ELSE valor END) as total, 
               SUM(CASE WHEN ignorar_total = 1 THEN valor ELSE 0 END) as total_ignorado,
               GROUP_CONCAT(
                   CASE 
                       WHEN ignorar_total = 1 THEN '💳 ' || COALESCE(NULLIF(TRIM(nota), ''), 'Cartão') || ' (R$ ' || REPLACE(printf('%.2f', valor), '.', ',') || ')'
                       ELSE NULLIF(TRIM(nota), '') 
                   END, 
               '\n') as notas, 
               MAX(COALESCE(data_alteracao, CURRENT_TIMESTAMP)) as last_modified 
               FROM despesas WHERE ano=? GROUP BY mes,categoria""",
            (ano,),
        ).fetchall()
        despesas = {}
        for r in desp_rows:
            despesas.setdefault(r["categoria"], {})[r["mes"]] = {"valor": r["total"], "valor_ignorado": r["total_ignorado"], "notas": r["notas"], "last_modified": r["last_modified"]}

        rec_rows = conn.execute("SELECT mes,SUM(valor) as total, MAX(COALESCE(data_alteracao, CURRENT_TIMESTAMP)) as last_modified, MAX(status) as max_status FROM receitas WHERE ano=? GROUP BY mes", (ano,)).fetchall()
        receitas = {r["mes"]: r["total"] for r in rec_rows}
        receitas_mod = {r["mes"]: r["last_modified"] for r in rec_rows}
        receitas_status = {r["mes"]: r["max_status"] for r in rec_rows}

        fixas = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM despesas_fixas_cartao WHERE ativa=1 AND ano=? ORDER BY dia",
                (ano,),
            ).fetchall()
        ]
        metas = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM metas WHERE ano_criacao <= ? AND (ano_meta >= ? OR ano_meta IS NULL) ORDER BY concluida,ano_meta",
                (ano, ano),
            ).fetchall()
        ]
        contas = [
            dict(r)
            for r in conn.execute("SELECT id,nome,ordem,saldo_inicial FROM contas_correntes ORDER BY ordem").fetchall()
        ]
        mov_rows = conn.execute(
            "SELECT id,mes,conta_id,valor,nota,tipo FROM movimentacoes_mensais WHERE ano=? ORDER BY id",
            (ano,),
        ).fetchall()
        movimentacoes = {}
        for r in mov_rows:
            mes = r["mes"]
            item = {
                "id": r["id"],
                "conta_id": r["conta_id"],
                "valor": float(r["valor"] or 0),
                "nota": r["nota"],
                "tipo": r["tipo"] or "",
            }
            bucket = movimentacoes.setdefault(mes, {"valor": 0.0, "items": []})
            bucket["valor"] += item["valor"]
            bucket["items"].append(item)

        dep_rows = conn.execute(
            "SELECT mes,conta_id,SUM(valor) as total FROM depositos_conta WHERE ano=? GROUP BY mes,conta_id",
            (ano,),
        ).fetchall()
        movimentos = {}
        for r in dep_rows:
            movimentos.setdefault(str(r["conta_id"]), {})[r["mes"]] = r["total"]
        for mes, mv in movimentacoes.items():
            for item in mv["items"]:
                cid = str(item["conta_id"])
                movimentos.setdefault(cid, {})
                movimentos[cid][mes] = movimentos[cid].get(mes, 0) + item["valor"]

        saldos = {}
        saldos_ini = self._saldos_iniciais(conn, contas, ano)
        for conta in contas:
            cid = str(conta["id"])
            si = saldos_ini[cid]
            mov = movimentos.get(cid, {})
            saldo = si
            saldos[cid] = {}
            for m in range(1, 13):
                saldo = round(saldo + mov.get(m, 0), 2)
                saldos[cid][m] = saldo

        cfg_rows = conn.execute("SELECT chave,valor FROM config").fetchall()
        config = {r["chave"]: r["valor"] for r in cfg_rows}
        exc_rows = conn.execute("SELECT mes, cat_id FROM fixas_excecoes WHERE ano=?", (ano,)).fetchall()
        fixas_excecoes = {f"{r['cat_id']}_{r['mes']}": True for r in exc_rows}
        fixas_manual_rows = conn.execute("SELECT mes, fixa_id FROM fixas_aplicadas_manual WHERE ano=?", (ano,)).fetchall()
        fixas_aplicadas_manual = {f"{r['fixa_id']}_{r['mes']}": True for r in fixas_manual_rows}
        pg_rows = conn.execute("SELECT mes, categoria, status FROM pagamento_status WHERE ano=?", (ano,)).fetchall()
        pagamentos = {}
        for r in pg_rows:
            pagamentos.setdefault(r["categoria"], {})[r["mes"]] = r["status"]
        rend_realizados_rows = conn.execute(
            "SELECT mes, status FROM rendimentos_realizados WHERE ano=?",
            (ano,),
        ).fetchall()
        rendimentos_realizados = {r["mes"]: int(r["status"] or 0) for r in rend_realizados_rows}
        rend_locais = [
            dict(r)
            for r in conn.execute(
                "SELECT id,ano,nome,ordem,projecao_taxa,conta_vinculada_id FROM rendimentos_locais WHERE ano=? ORDER BY ordem,id",
                (ano,),
            ).fetchall()
        ]
        rend_rows = conn.execute(
            """
            SELECT mes,local_id,
                SUM(CASE WHEN tipo='aporte' THEN valor ELSE 0 END) as aporte,
                SUM(CASE WHEN tipo='rendimento' AND (nota IS NULL OR nota <> 'Projeção') THEN valor ELSE 0 END) as rendimento,
                SUM(CASE WHEN tipo='saque' THEN valor ELSE 0 END) as saque,
                SUM(CASE WHEN tipo='rendimento' AND nota = 'Projeção' THEN valor ELSE 0 END) as projecao,
                COUNT(CASE WHEN tipo='rendimento' AND (nota IS NULL OR nota <> 'Projeção') THEN 1 END) as qtd_rendimentos,
                MAX(COALESCE(data_alteracao, CURRENT_TIMESTAMP)) as last_modified
            FROM rendimentos_lancamentos
            WHERE ano=?
            GROUP BY mes,local_id
            """,
            (ano,),
        ).fetchall()
        rendimentos = {}
        for r in rend_rows:
            rendimentos.setdefault(str(r["local_id"]), {})[r["mes"]] = {
                "aporte": float(r["aporte"] or 0),
                "rendimento": float(r["rendimento"] or 0),
                "saque": float(r["saque"] or 0),
                "projecao": float(r["projecao"] or 0),
                "qtd_rendimentos": int(r["qtd_rendimentos"] or 0),
                "last_modified": r["last_modified"],
            }

        # Descobre todos os anos com dados de todas as tabelas (1 consulta UNION)
        anos_list = sorted(descobrir_anos(conn), reverse=True)

        conn.close()
        return {
            "anos": anos_list,
            "categorias": cats,
            "despesas": despesas,
            "receitas": receitas,
            "receitas_mod": receitas_mod,
            "receitas_status": receitas_status,
            "fixas": fixas,
            "metas": metas,
            "meses": self.meses,
            "contas": contas,
            "movimentos": movimentos,
            "saldos": saldos,
            "saldos_ini": saldos_ini,
            "movimentacoes": movimentacoes,
            "config": config,
            "fixas_excecoes": fixas_excecoes,
            "fixas_aplicadas_manual": fixas_aplicadas_manual,
            "pagamentos": pagamentos,
            "rendimentos_realizados": rendimentos_realizados,
            "rendimentos_locais": rend_locais,
            "rendimentos": rendimentos,
        }

    def _meses_rendimentos_realizados(self, ano: int) -> list[int]:
        hoje = datetime.now()
        if ano < hoje.year:
            return list(range(1, 13))
        if ano > hoje.year:
            return []
        return list(range(1, hoje.month))

    def _sync_rendimentos_realizados(self, conn, ano: int) -> None:
        meses_realizados = self._meses_rendimentos_realizados(ano)

        # Garante que o ano exista na tabela `anos` (evita escrita se já existe)
        existe_ano = conn.execute(
            "SELECT 1 FROM anos WHERE ano=?", (ano,)
        ).fetchone()
        if not existe_ano:
            conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (ano,))
            conn.commit()

        # Hot path: se já está sincronizado, não escreve nada no GET
        atuais = {
            int(r["mes"]): int(r["status"] or 0)
            for r in conn.execute(
                "SELECT mes, status FROM rendimentos_realizados WHERE ano=?", (ano,)
            ).fetchall()
        }
        esperados = {mes: 1 for mes in meses_realizados}
        if atuais == esperados:
            return

        if meses_realizados:
            conn.executemany(
                "INSERT INTO rendimentos_realizados(ano,mes,status,data_alteracao) VALUES(?,?,1,CURRENT_TIMESTAMP) "
                "ON CONFLICT(ano,mes) DO UPDATE SET status=excluded.status, data_alteracao=CURRENT_TIMESTAMP",
                [(ano, mes) for mes in meses_realizados],
            )
            placeholders = ",".join("?" for _ in meses_realizados)
            conn.execute(
                f"DELETE FROM rendimentos_realizados WHERE ano=? AND mes NOT IN ({placeholders})",
                (ano, *meses_realizados),
            )
        else:
            conn.execute("DELETE FROM rendimentos_realizados WHERE ano=?", (ano,))

        conn.commit()

    def _saldos_iniciais(self, conn, contas, ano_alvo):
        """Saldos iniciais de todas as contas em 2 consultas agrupadas.

        Antes: 4 consultas por conta (MIN/MIN/SUM/SUM) — N contas => 4N queries
        por carga do dashboard. Agora: 1 consulta GROUP BY por tabela.
        """
        dep_rows = conn.execute(
            "SELECT conta_id, MIN(ano) as primeiro, COALESCE(SUM(valor),0) as total "
            "FROM depositos_conta WHERE ano<? GROUP BY conta_id",
            (ano_alvo,),
        ).fetchall()
        mov_rows = conn.execute(
            "SELECT conta_id, MIN(ano) as primeiro, COALESCE(SUM(valor),0) as total "
            "FROM movimentacoes_mensais WHERE ano<? GROUP BY conta_id",
            (ano_alvo,),
        ).fetchall()
        dep = {r["conta_id"]: r for r in dep_rows}
        mov = {r["conta_id"]: r for r in mov_rows}

        saldos_ini = {}
        for conta in contas:
            cid = str(conta["id"])
            d = dep.get(conta["id"])
            m = mov.get(conta["id"])
            anos_ant = [
                x for x in (d["primeiro"] if d else None, m["primeiro"] if m else None)
                if x is not None
            ]
            saldo = conta["saldo_inicial"] or 0.0
            if anos_ant:
                saldo += (d["total"] if d else 0) + (m["total"] if m else 0)
            saldos_ini[cid] = round(saldo, 2)
        return saldos_ini

    def is_ano_bloqueado(self, ano: int) -> bool:
        conn = self.connection_factory()
        row = conn.execute(
            "SELECT valor FROM config WHERE chave=?",
            (f"ano_bloqueado_{ano}",)
        ).fetchone()
        conn.close()
        return row is not None and row["valor"] == "1"
