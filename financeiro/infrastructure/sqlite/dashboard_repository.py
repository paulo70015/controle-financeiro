class SQLiteDashboardRepository:
    def __init__(self, connection_factory, meses):
        self.connection_factory = connection_factory
        self.meses = meses

    def get_dados_ano(self, ano: int) -> dict:
        conn = self.connection_factory()
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
        mov_rows = conn.execute("SELECT mes,conta_id,valor,nota FROM movimentacoes_mensais WHERE ano=?", (ano,)).fetchall()
        movimentacoes = {
            r["mes"]: {"conta_id": r["conta_id"], "valor": r["valor"], "nota": r["nota"]}
            for r in mov_rows
        }

        dep_rows = conn.execute(
            "SELECT mes,conta_id,SUM(valor) as total FROM depositos_conta WHERE ano=? GROUP BY mes,conta_id",
            (ano,),
        ).fetchall()
        movimentos = {}
        for r in dep_rows:
            movimentos.setdefault(str(r["conta_id"]), {})[r["mes"]] = r["total"]
        for mes, mv in movimentacoes.items():
            cid = str(mv["conta_id"])
            movimentos.setdefault(cid, {})
            movimentos[cid][mes] = movimentos[cid].get(mes, 0) + mv["valor"]

        saldos = {}
        saldos_ini = {}
        for conta in contas:
            cid = str(conta["id"])
            si = self._saldo_inicial_conta(conn, conta["id"], conta["saldo_inicial"], ano)
            saldos_ini[cid] = si
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
        rend_locais = [
            dict(r)
            for r in conn.execute(
                "SELECT id,ano,nome,ordem,projecao_taxa FROM rendimentos_locais WHERE ano=? ORDER BY ordem,id",
                (ano,),
            ).fetchall()
        ]
        rend_rows = conn.execute(
            """
            SELECT mes,local_id,
                SUM(CASE WHEN tipo='aporte' THEN valor ELSE 0 END) as aporte,
                SUM(CASE WHEN tipo='rendimento' AND (nota IS NULL OR nota <> 'Projeção') THEN valor ELSE 0 END) as rendimento,
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
                "projecao": float(r["projecao"] or 0),
                "qtd_rendimentos": int(r["qtd_rendimentos"] or 0),
                "last_modified": r["last_modified"],
            }

        # Descobre todos os anos com dados de todas as tabelas
        anos_set = set()
        tabelas = [
            "anos", "categorias", "despesas", "receitas",
            "despesas_fixas_cartao", "fixas_excecoes", "fixas_aplicadas_manual",
            "pagamento_status", "depositos_conta", "movimentacoes_mensais",
            "rendimentos_locais", "rendimentos_lancamentos",
        ]
        for tabela in tabelas:
            try:
                for r in conn.execute(f"SELECT DISTINCT ano FROM {tabela}"):
                    if r[0] is not None:
                        anos_set.add(int(r[0]))
            except Exception:
                pass
        # Metas: ano_criacao e ano_meta
        try:
            for r in conn.execute("SELECT DISTINCT ano_criacao, ano_meta FROM metas"):
                for val in (r[0], r[1]):
                    if val is not None:
                        anos_set.add(int(val))
        except Exception:
            pass
        anos_list = sorted(anos_set, reverse=True)

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
            "rendimentos_locais": rend_locais,
            "rendimentos": rendimentos,
        }

    def _saldo_inicial_conta(self, conn, conta_id, saldo_inicial_config, ano_alvo):
        primeiro = conn.execute(
            "SELECT MIN(ano) as a FROM depositos_conta WHERE conta_id=? AND ano<?",
            (conta_id, ano_alvo),
        ).fetchone()["a"]
        primeiro_mov = conn.execute(
            "SELECT MIN(ano) as a FROM movimentacoes_mensais WHERE conta_id=? AND ano<?",
            (conta_id, ano_alvo),
        ).fetchone()["a"]
        anos_ant = [x for x in [primeiro, primeiro_mov] if x is not None]
        if not anos_ant:
            return saldo_inicial_config or 0.0
        saldo = saldo_inicial_config or 0.0
        
        t_dep = conn.execute("SELECT COALESCE(SUM(valor),0) as t FROM depositos_conta WHERE conta_id=? AND ano<?", (conta_id, ano_alvo)).fetchone()["t"]
        t_mov = conn.execute("SELECT COALESCE(SUM(valor),0) as t FROM movimentacoes_mensais WHERE conta_id=? AND ano<?", (conta_id, ano_alvo)).fetchone()["t"]
        
        saldo += t_dep + t_mov
        return round(saldo, 2)

    def is_ano_bloqueado(self, ano: int) -> bool:
        conn = self.connection_factory()
        row = conn.execute(
            "SELECT valor FROM config WHERE chave=?",
            (f"ano_bloqueado_{ano}",)
        ).fetchone()
        conn.close()
        return row is not None and row["valor"] == "1"

