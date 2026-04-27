import csv
import io
import re
import os
import shutil


class SQLiteCSVRepository:
    def __init__(self, connection_factory, meses):
        from financeiro.infrastructure.runtime.paths import get_data_dir
        self.connection_factory = connection_factory
        self.meses = meses
        self.db_path = os.path.join(get_data_dir(), "financeiro.db")
        self.bak_path = os.path.join(get_data_dir(), "financeiro.db.bak")

    def desfazer_importacao(self):
        if not os.path.exists(self.bak_path):
            return ({"erro": "Nenhum backup disponível para restaurar."}, 400)
        try:
            shutil.copy2(self.bak_path, self.db_path)
            os.remove(self.bak_path)
            return ({"ok": True}, 200)
        except Exception as e:
            return ({"erro": f"Falha ao restaurar backup: {str(e)}"}, 500)

    def importar_csv(self, file_storage):
        try:
            shutil.copy2(self.db_path, self.bak_path)
        except Exception:
            pass

        content = file_storage.read().decode("utf-8-sig")

        is_exported = content.startswith("sep=;")
        
        if is_exported:
            reader = csv.reader(io.StringIO(content), delimiter=";")
            rows = list(reader)
            ano_raw = rows[1][0].strip() if len(rows) > 1 and rows[1] else ""
        else:
            reader = csv.reader(io.StringIO(content), delimiter=";")
            rows_test = list(reader)
            if rows_test and len(rows_test[0]) == 1 and "," in rows_test[0][0]:
                reader = csv.reader(io.StringIO(content), delimiter=",")
                rows = list(reader)
            else:
                rows = rows_test
            ano_raw = rows[0][0].replace("sep=", "").strip(" ;") if rows and rows[0] else ""
            if not ano_raw and len(rows) > 1 and rows[1][0].strip().isdigit():
                ano_raw = rows[1][0].strip()

        if not rows:
            return ({"erro": "Arquivo vazio"}, 400)

        try:
            ano = int(ano_raw)
        except (ValueError, IndexError):
            return ({"erro": "Primeira linha (ou cabecalho) deve conter o ano correspondente"}, 400)

        nomes_m = [
            "janeiro",
            "fevereiro",
            "marco",
            "abril",
            "maio",
            "junho",
            "julho",
            "agosto",
            "setembro",
            "outubro",
            "novembro",
            "dezembro",
        ]

        header = []
        linha_cabecalho = 1
        for i, r in enumerate(rows[:5]):
            if any(h.lower().strip().replace("ç", "c").replace("ç", "c") in nomes_m for h in r):
                linha_cabecalho = i
                break

        for c in rows[linha_cabecalho]:
            norm = c.strip().lower().replace("\u00e7", "c").replace("\u00e3", "a").replace("\u00e2", "a")
            header.append(norm)

        col_to_mes = {}
        for i, h in enumerate(header):
            if h in nomes_m:
                col_to_mes[i] = nomes_m.index(h) + 1

        def parse_valor(s):
            s = s.strip()
            if not s:
                return None
            neg = "-" in s
            s = re.sub(r"[^\d,.]", "", s)
            if not s:
                return None
            s = s.replace(".", "").replace(",", ".")
            try:
                v = float(s)
                return -v if neg else v
            except ValueError:
                return None

        conn = self.connection_factory(auto_sync=True)
        conn.execute("DELETE FROM despesas WHERE ano=?", (ano,))
        conn.execute("DELETE FROM receitas WHERE ano=?", (ano,))
        conn.execute("DELETE FROM movimentacoes_mensais WHERE ano=?", (ano,))
        conn.execute("DELETE FROM depositos_conta WHERE ano=?", (ano,))

        importados = {"despesas": 0, "movimentacoes": 0, "depositos": 0, "fixas": 0, "metas": 0, "rendimentos": 0}
        erros = []

        def get_or_create_categoria(nome):
            row = conn.execute("SELECT id FROM categorias WHERE nome=? AND ano=?", (nome, ano)).fetchone()
            if row:
                return row["id"]
            cur = conn.execute(
                "INSERT INTO categorias (nome, ordem, inclui_fixas, ano) VALUES (?,?,0,?)",
                (nome, 9999, ano),
            )
            return cur.lastrowid

        def get_or_create_conta(nome):
            row = conn.execute("SELECT id FROM contas_correntes WHERE nome=?", (nome,)).fetchone()
            if row:
                return row["id"]
            cur = conn.execute(
                "INSERT INTO contas_correntes (nome, ordem, saldo_inicial) VALUES (?,?,0)",
                (nome, 9999),
            )
            return cur.lastrowid

        def get_or_create_local_rendimento(nome):
            row = conn.execute("SELECT id FROM rendimentos_locais WHERE nome=? AND ano=?", (nome, ano)).fetchone()
            if row:
                return row["id"]
            prox = conn.execute("SELECT COALESCE(MAX(ordem), 0) + 1 AS prox FROM rendimentos_locais WHERE ano=?", (ano,)).fetchone()["prox"]
            cur = conn.execute("INSERT INTO rendimentos_locais(ano,nome,ordem) VALUES(?,?,?)", (ano, nome, prox))
            return cur.lastrowid

        col_nome = 14
        col_valor = 15
        col_ano = 16
        modo_lateral = None
        modo_vertical = "despesas"

        for row in rows[linha_cabecalho + 1 :]:
            if not row:
                continue

            if not is_exported and len(row) > col_nome:
                nome_lat = row[col_nome].strip()
                val_lat = row[col_valor].strip() if len(row) > col_valor else ""
                ano_lat = row[col_ano].strip() if len(row) > col_ano else ""
                
                if nome_lat:
                    nome_norm = nome_lat.lower().replace("\u00e7", "c").replace("\u00e3", "a")
                    if "fixas" in nome_norm or "despesas cartao" in nome_norm:
                        modo_lateral = "fixas"
                    elif nome_norm == "metas":
                        modo_lateral = "metas"
                    elif nome_norm.startswith("gis") or nome_norm.startswith("conclu"):
                        modo_lateral = None
                    else:
                        if modo_lateral == "fixas":
                            val = parse_valor(val_lat)
                            if val is not None and val != 0:
                                try:
                                    conn.execute("DELETE FROM despesas_fixas_cartao WHERE descricao=? AND ano=?", (nome_lat, ano))
                                    conn.execute("INSERT INTO despesas_fixas_cartao (descricao, dia, valor, ano) VALUES (?,?,?,?)", (nome_lat, 1, val, ano))
                                    importados["fixas"] += 1
                                except Exception as e:
                                    erros.append("Fixa %s: %s" % (nome_lat, str(e)))
                        elif modo_lateral == "metas":
                            val = parse_valor(val_lat)
                            ano_meta = None
                            try:
                                ano_meta = int(ano_lat) if ano_lat else None
                            except ValueError: pass
                            if val is not None and val != 0:
                                try:
                                    conn.execute("DELETE FROM metas WHERE descricao=?", (nome_lat,))
                                    conn.execute("INSERT INTO metas (descricao, valor, ano_meta, ano_criacao, concluida) VALUES (?,?,?,?,0)", (nome_lat, val, ano_meta, ano))
                                    importados["metas"] += 1
                                except Exception as e:
                                    erros.append("Meta %s: %s" % (nome_lat, str(e)))

            label = row[0].strip()
            if not label:
                continue
                
            if label.lower().startswith("total"):
                continue

            if is_exported:
                if label == "Despesas Fixas":
                    modo_vertical = "fixas"
                    continue
                elif label == "Metas":
                    modo_vertical = "metas"
                    continue
                elif label == "Rendimentos":
                    modo_vertical = "rendimentos"
                    continue

            if modo_vertical == "fixas":
                dia_str = row[1].strip() if len(row) > 1 else "1"
                val_str = row[2].strip() if len(row) > 2 else ""
                val = parse_valor(val_str)
                dia = int(dia_str) if dia_str.isdigit() else 1
                if val is not None and val != 0:
                    try:
                        conn.execute("INSERT INTO despesas_fixas_cartao (descricao, dia, valor, ano) VALUES (?,?,?,?)", (label, dia, val, ano))
                        importados["fixas"] += 1
                    except Exception as e: pass
                continue

            if modo_vertical == "metas":
                val_str = row[1].strip() if len(row) > 1 else ""
                ano_str = row[2].strip() if len(row) > 2 else ""
                status_str = row[3].strip().lower() if len(row) > 3 else ""
                val = parse_valor(val_str)
                ano_meta = int(ano_str) if ano_str.isdigit() else None
                concluida = 1 if status_str == "concluida" else 0
                if val is not None and val != 0:
                    try:
                        conn.execute("INSERT INTO metas (descricao, valor, ano_meta, ano_criacao, concluida) VALUES (?,?,?,?,?)", (label, val, ano_meta, ano, concluida))
                        importados["metas"] += 1
                    except Exception as e: pass
                continue

            if modo_vertical == "rendimentos":
                local_id = get_or_create_local_rendimento(label)
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            try:
                                conn.execute("DELETE FROM rendimentos_lancamentos WHERE ano=? AND mes=? AND local_id=? AND tipo=?", (ano, mes, local_id, 'aporte'))
                                conn.execute("INSERT INTO rendimentos_lancamentos (ano, mes, local_id, tipo, valor, nota) VALUES (?,?,?,?,?,?)", (ano, mes, local_id, 'aporte', val, "Importado CSV"))
                                importados["rendimentos"] += 1
                            except Exception as e: pass
                continue

            if not is_exported and label.lower() == "rendimento":
                local_id = get_or_create_local_rendimento("Rendimento")
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            try:
                                conn.execute("DELETE FROM rendimentos_lancamentos WHERE ano=? AND mes=? AND local_id=? AND tipo=?", (ano, mes, local_id, 'aporte'))
                                conn.execute("INSERT INTO rendimentos_lancamentos (ano, mes, local_id, tipo, valor, nota) VALUES (?,?,?,?,?,?)", (ano, mes, local_id, 'aporte', val, "Importado CSV"))
                                importados["rendimentos"] += 1
                            except Exception as e: pass
                continue

            if label.lower() == "nubank" or label.lower() == "movimentacao":
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            try:
                                conn.execute(
                                    "INSERT INTO movimentacoes_mensais (ano, mes, valor, nota) VALUES (?,?,?,?)",
                                    (ano, mes, val, "Importado CSV"),
                                )
                                importados["movimentacoes"] += 1
                            except Exception as e:
                                erros.append("Mov mes %d: %s" % (mes, str(e)))
                continue
            if label.lower() in ("nuconta", "nu conta", "conta", "contas saldo acumulado"):
                conta_id = get_or_create_conta("NuConta")
                saldos_mes = {}
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None:
                            saldos_mes[mes] = val
                meses_ord = sorted(saldos_mes.keys())
                for i, mes in enumerate(meses_ord):
                    saldo_atual = saldos_mes[mes]
                    saldo_anterior = saldos_mes[meses_ord[i - 1]] if i > 0 else 0
                    delta = round(saldo_atual - saldo_anterior, 2)
                    if delta != 0:
                        try:
                            conn.execute(
                                "INSERT INTO depositos_conta (ano, mes, conta_id, valor, nota) VALUES (?,?,?,?,?)",
                                (ano, mes, conta_id, delta, "Importado CSV"),
                            )
                            importados["depositos"] += 1
                        except Exception as e:
                            erros.append("NuConta mes %d: %s" % (mes, str(e)))
                continue

            if "receitas" in label.lower() or "salario" in label.lower():
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            try:
                                conn.execute(
                                    "INSERT INTO receitas (ano, mes, descricao, valor, nota) VALUES (?,?,?,?,?)",
                                    (ano, mes, label, val, "Importado CSV"),
                                )
                            except Exception as e:
                                erros.append("Receita mes %d: %s" % (mes, str(e)))
                continue

            cat_id = get_or_create_categoria(label)
            if label.strip().lower() in ("cartao", "cartao"):
                conn.execute("UPDATE categorias SET inclui_fixas=1 WHERE id=?", (cat_id,))

            for col, mes in col_to_mes.items():
                if col < len(row):
                    val = parse_valor(row[col])
                    if val is not None and val != 0:
                        try:
                            conn.execute(
                                "INSERT INTO despesas (ano, mes, categoria, valor, nota) VALUES (?,?,?,?,?)",
                                (ano, mes, label, val, "Importado CSV"),
                            )
                            importados["despesas"] += 1
                        except Exception as e:
                            erros.append("%s mes %d: %s" % (label, mes, str(e)))

        conn.commit()
        conn.close()
        return ({"ok": True, "ano": ano, "importados": importados, "erros": erros[:10], "undo_available": True}, 200)

    def exportar_csv(self, ano: int):
        conn = self.connection_factory()
        cats = [
            dict(r)
            for r in conn.execute(
                "SELECT id,nome,inclui_fixas FROM categorias WHERE ano=? ORDER BY ordem",
                (ano,),
            ).fetchall()
        ]
        despesas_raw = conn.execute(
            "SELECT mes,categoria,SUM(valor) as v, GROUP_CONCAT(NULLIF(TRIM(nota), ''), ' | ') as notas FROM despesas WHERE ano=? GROUP BY mes,categoria",
            (ano,),
        ).fetchall()
        despesas = {}
        for r in despesas_raw:
            despesas.setdefault(r["categoria"], {})[r["mes"]] = {"v": r["v"], "notas": r["notas"]}
        receitas_raw = conn.execute("SELECT mes,SUM(valor) as v FROM receitas WHERE ano=? GROUP BY mes", (ano,)).fetchall()
        receitas = {r["mes"]: r["v"] for r in receitas_raw}
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
        rend_locais = [
            dict(r)
            for r in conn.execute(
                "SELECT id,nome,ordem FROM rendimentos_locais WHERE ano=? ORDER BY ordem,id",
                (ano,),
            ).fetchall()
        ]
        rend_rows = conn.execute(
            """
            SELECT mes,local_id,SUM(valor) as total
            FROM rendimentos_lancamentos
            WHERE ano=?
            GROUP BY mes,local_id
            """,
            (ano,),
        ).fetchall()
        rendimentos = {}
        for r in rend_rows:
            rendimentos.setdefault(r["local_id"], {})[r["mes"]] = float(r["total"] or 0)
        fixas_excecoes = {
            f"{r['cat_id']}_{r['mes']}": True
            for r in conn.execute("SELECT mes, cat_id FROM fixas_excecoes WHERE ano=?", (ano,)).fetchall()
        }
        conn.close()

        total_fixas = sum(f["valor"] for f in fixas)

        def _brl(val):
            return str(val).replace(".", ",")

        out = io.StringIO()
        writer = csv.writer(out, delimiter=";", quoting=csv.QUOTE_ALL)
        out.write("sep=;\r\n")
        writer.writerow([ano] + [""] * 13)
        writer.writerow([""] + self.meses + ["Total"])

        for cat in cats:
            row = [cat["nome"]]
            tot = 0
            for m in range(1, 13):
                d_info = despesas.get(cat["nome"], {}).get(m, {})
                vlanc = d_info.get("v", 0) or 0
                notas = d_info.get("notas", "")
                vfixas = 0
                if f"{cat['id']}_{m}" not in fixas_excecoes:
                    vfixas += sum(f["valor"] for f in fixas if f.get("cat_id") == cat["id"])
                    if cat["inclui_fixas"]:
                        vfixas += sum(f["valor"] for f in fixas if not f.get("cat_id"))
                v = vlanc + vfixas
                if v == 0 and notas:
                    row.append(notas)
                else:
                    row.append(_brl(v))
                tot += v
            row.append(_brl(tot))
            writer.writerow(row)

        writer.writerow([""] * 14)
        writer.writerow(["Despesas Fixas", "Dia", "Valor"] + [""] * 11)
        for f in fixas:
            writer.writerow([f["descricao"], f.get("dia", ""), _brl(f["valor"])] + [""] * 11)
        writer.writerow(["Total Fixas", "", _brl(total_fixas)] + [""] * 11)

        writer.writerow([""] * 14)
        writer.writerow(["Metas", "Valor Alvo", "Ano", "Status"] + [""] * 10)
        for mt in metas:
            status = "Concluida" if mt.get("concluida") else "Em andamento"
            writer.writerow([mt["descricao"], _brl(mt.get("valor", 0)), mt.get("ano_meta", ""), status] + [""] * 10)

        writer.writerow([""] * 14)
        writer.writerow(["Rendimentos", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez", "Total"])
        for rl in rend_locais:
            row = [rl["nome"]]
            total_linha = 0
            for m in range(1, 13):
                soma = float((rendimentos.get(rl["id"], {}) or {}).get(m, 0) or 0)
                total_linha += soma
                if soma:
                    row.append(_brl(soma))
                else:
                    row.append("")
            row.append(_brl(total_linha))
            writer.writerow(row)

        csv_bytes = ("\ufeff" + out.getvalue()).encode("utf-8")
        headers = {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename=despesas-{ano}.csv",
        }
        return (csv_bytes, 200, headers)
