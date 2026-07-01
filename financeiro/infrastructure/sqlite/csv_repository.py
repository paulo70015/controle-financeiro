import csv
import io
import re
import os
import shutil

from financeiro.infrastructure.csv_utils import linha_tem_mes_csv, mes_por_cabecalho_csv
from financeiro.infrastructure.export_files import nome_arquivo_exportacao


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
        if not col_to_mes:
            for i, r in enumerate(rows[:5]):
                if linha_tem_mes_csv(r):
                    linha_cabecalho = i
                    break
            for i, h in enumerate(rows[linha_cabecalho]):
                mes = mes_por_cabecalho_csv(h)
                if mes:
                    col_to_mes[i] = mes

        valores_invalidos = []

        def parse_valor(s):
            raw = s.strip()
            if not raw:
                return None
            neg = "-" in raw
            limpo = re.sub(r"[^\d,.]", "", raw)
            if not limpo:
                if raw:
                    valores_invalidos.append(raw)
                return None
            limpo = limpo.replace(".", "").replace(",", ".")
            try:
                v = float(limpo)
                return -v if neg else v
            except ValueError:
                valores_invalidos.append(raw)
                return None

        conn = self.connection_factory(auto_sync=True)
        # Garante que o ano fique registrado na tabela `anos`
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (ano,))
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
                elif label == "Receitas":
                    modo_vertical = "receitas"
                    continue
                elif label == "Movimentações":
                    modo_vertical = "movimentacoes"
                    continue
                elif label == "Contas Saldo Acumulado":
                    modo_vertical = "contas"
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
                # Linhas podem ter formato "Local - tipo" (export com tipos separados)
                nome_local = label
                tipo_forcado = None
                if " - " in label:
                    partes = label.rsplit(" - ", 1)
                    if partes[1] in ("aporte", "saque"):
                        nome_local = partes[0]
                        tipo_forcado = partes[1]

                # Coluna extra após o Total pode conter nome da conta vinculada
                conta_vinculada_nome = None
                if len(row) > 14 and row[14].strip():
                    conta_vinculada_nome = row[14].strip()

                local_id = get_or_create_local_rendimento(nome_local)
                if conta_vinculada_nome:
                    conta_id = get_or_create_conta(conta_vinculada_nome)
                    conn.execute("UPDATE rendimentos_locais SET conta_vinculada_id=? WHERE id=?", (conta_id, local_id))

                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            if tipo_forcado:
                                tipo = tipo_forcado
                            else:
                                tipo = 'saque' if val < 0 else 'aporte'
                            valor_abs = abs(val)
                            try:
                                conn.execute("DELETE FROM rendimentos_lancamentos WHERE ano=? AND mes=? AND local_id=? AND tipo=?", (ano, mes, local_id, tipo))
                                conn.execute("INSERT INTO rendimentos_lancamentos (ano, mes, local_id, tipo, valor, nota) VALUES (?,?,?,?,?,?)", (ano, mes, local_id, tipo, valor_abs, "Importado CSV"))
                                importados["rendimentos"] += 1
                            except Exception as e: pass
                continue

            if modo_vertical == "receitas":
                # Label é ignorado — usamos "Receitas" como descrição
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            try:
                                conn.execute(
                                    "INSERT INTO receitas (ano, mes, descricao, valor, nota) VALUES (?,?,?,?,?)",
                                    (ano, mes, "Receitas", val, "Importado CSV"),
                                )
                            except Exception as e:
                                erros.append("Receita mes %d: %s" % (mes, str(e)))
                continue

            if modo_vertical == "movimentacoes":
                conta_id = get_or_create_conta(label)
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            try:
                                conn.execute(
                                    "INSERT INTO movimentacoes_mensais (ano, mes, conta_id, valor, nota, tipo) VALUES (?,?,?,?,?,?)",
                                    (ano, mes, conta_id, val, "Importado CSV", ""),
                                )
                                importados["movimentacoes"] += 1
                            except Exception as e:
                                erros.append("Mov mes %d: %s" % (mes, str(e)))
                continue

            if modo_vertical == "contas":
                conta_id = get_or_create_conta(label)
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
                            erros.append("Conta %s mes %d: %s" % (label, mes, str(e)))
                continue

            # -- Fallbacks para CSVs não-exportados (formato legado) --
            if not is_exported and label.lower() == "rendimento":
                local_id = get_or_create_local_rendimento("Rendimento")
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            tipo = 'saque' if val < 0 else 'aporte'
                            valor_abs = abs(val)
                            try:
                                conn.execute("DELETE FROM rendimentos_lancamentos WHERE ano=? AND mes=? AND local_id=? AND tipo=?", (ano, mes, local_id, tipo))
                                conn.execute("INSERT INTO rendimentos_lancamentos (ano, mes, local_id, tipo, valor, nota) VALUES (?,?,?,?,?,?)", (ano, mes, local_id, tipo, valor_abs, "Importado CSV"))
                                importados["rendimentos"] += 1
                            except Exception as e: pass
                continue

            if not is_exported and (label.lower() == "nubank" or label.lower() == "movimentacao"):
                conta_id = get_or_create_conta("NuConta")
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            try:
                                conn.execute(
                                    "INSERT INTO movimentacoes_mensais (ano, mes, conta_id, valor, nota, tipo) VALUES (?,?,?,?,?,?)",
                                    (ano, mes, conta_id, val, "Importado CSV", ""),
                                )
                                importados["movimentacoes"] += 1
                            except Exception as e:
                                erros.append("Mov mes %d: %s" % (mes, str(e)))
                continue
            if not is_exported and label.lower() in ("nuconta", "nu conta", "conta", "contas saldo acumulado"):
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

            if not is_exported and ("receitas" in label.lower() or "salario" in label.lower()):
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

        try:
            conn.commit()
        except Exception as e:
            conn.rollback()
            return ({"erro": f"Falha ao gravar dados importados: {str(e)}"}, 500)
        finally:
            conn.close()
        return ({"ok": True, "ano": ano, "importados": importados, "erros": erros[:10], "valores_invalidos": valores_invalidos[:20], "undo_available": True}, 200)

    def exportar_csv(self, ano: int):
        conn = self.connection_factory()
        conn.execute("PRAGMA group_concat_max_len = 1000000")
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
                """SELECT rl.id, rl.nome, rl.ordem, rl.conta_vinculada_id,
                   cc.nome as conta_vinculada_nome
                FROM rendimentos_locais rl
                LEFT JOIN contas_correntes cc ON cc.id = rl.conta_vinculada_id
                WHERE rl.ano=? ORDER BY rl.ordem, rl.id""",
                (ano,),
            ).fetchall()
        ]
        rend_rows = conn.execute(
            """
            SELECT mes,local_id,tipo,SUM(valor) as total
            FROM rendimentos_lancamentos
            WHERE ano=?
            GROUP BY mes,local_id,tipo
            """,
            (ano,),
        ).fetchall()
        rendimentos = {}  # chave: (local_id, tipo) -> {mes: total}
        rend_tipos_por_local = {}  # chave: local_id -> set de tipos
        for r in rend_rows:
            key = (r["local_id"], r["tipo"])
            rendimentos.setdefault(key, {})[r["mes"]] = float(r["total"] or 0)
            rend_tipos_por_local.setdefault(r["local_id"], set()).add(r["tipo"])
        # Movimentações mensais (agrupadas por conta e mês)
        mov_rows = conn.execute(
            """
            SELECT m.mes, m.conta_id, cc.nome as conta_nome, SUM(m.valor) as total
            FROM movimentacoes_mensais m
            JOIN contas_correntes cc ON cc.id = m.conta_id
            WHERE m.ano=?
            GROUP BY m.mes, m.conta_id
            ORDER BY cc.nome, m.mes
            """,
            (ano,),
        ).fetchall()
        movimentacoes = {}  # chave: conta_nome -> {mes: total}
        for r in mov_rows:
            movimentacoes.setdefault(r["conta_nome"], {})[r["mes"]] = float(r["total"] or 0)
        # Depósitos / saldo acumulado por conta
        dep_rows = conn.execute(
            """
            SELECT d.mes, d.conta_id, cc.nome as conta_nome, SUM(d.valor) as total
            FROM depositos_conta d
            JOIN contas_correntes cc ON cc.id = d.conta_id
            WHERE d.ano=?
            GROUP BY d.mes, d.conta_id
            ORDER BY cc.nome, d.mes
            """,
            (ano,),
        ).fetchall()
        depositos = {}  # chave: conta_nome -> {mes: delta}
        for r in dep_rows:
            depositos.setdefault(r["conta_nome"], {})[r["mes"]] = float(r["total"] or 0)
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
        writer.writerow(["Receitas", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez", "Total"])
        row_rec = ["Receitas"]
        total_rec = 0
        for m in range(1, 13):
            v = receitas.get(m, 0) or 0
            total_rec += v
            row_rec.append(_brl(v) if v else "")
        row_rec.append(_brl(total_rec))
        writer.writerow(row_rec)

        writer.writerow([""] * 14)
        writer.writerow(["Rendimentos", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez", "Total", "Conta Vinculada"])
        for rl in rend_locais:
            conta_vinculada_nome = rl.get("conta_vinculada_nome") or ""
            tipos = sorted(rend_tipos_por_local.get(rl["id"], set()))
            if not tipos:
                # Local sem lançamentos: exporta linha vazia com nome
                row = [rl["nome"]] + [""] * 13 + [conta_vinculada_nome]
                writer.writerow(row)
            elif len(tipos) == 1:
                # Um único tipo: exporta sem sufixo (compatível com versões anteriores)
                tipo_unico = tipos[0]
                row = [rl["nome"]]
                total_linha = 0.0
                for m in range(1, 13):
                    v = float((rendimentos.get((rl["id"], tipo_unico), {}) or {}).get(m, 0) or 0)
                    total_linha += v
                    row.append(_brl(v) if v != 0 else "")
                row.append(_brl(total_linha))
                row.append(conta_vinculada_nome)
                writer.writerow(row)
            else:
                # Múltiplos tipos: uma linha por tipo com sufixo " - tipo"
                for tipo in tipos:
                    sub_row = [f"{rl['nome']} - {tipo}"]
                    sub_total = 0.0
                    for m in range(1, 13):
                        v = float((rendimentos.get((rl["id"], tipo), {}) or {}).get(m, 0) or 0)
                        sub_total += v
                        sub_row.append(_brl(v) if v != 0 else "")
                    sub_row.append(_brl(sub_total))
                    # Conta vinculada só na primeira linha do grupo
                    sub_row.append(conta_vinculada_nome if tipo == tipos[0] else "")
                    writer.writerow(sub_row)

        # Movimentações Mensais (por conta)
        if movimentacoes:
            writer.writerow([""] * 14)
            writer.writerow(["Movimentações", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez", "Total"])
            for conta_nome in sorted(movimentacoes.keys()):
                row = [conta_nome]
                total_linha = 0
                for m in range(1, 13):
                    v = movimentacoes[conta_nome].get(m, 0) or 0
                    total_linha += v
                    row.append(_brl(v) if v != 0 else "")
                row.append(_brl(total_linha))
                writer.writerow(row)

        # Depósitos / Contas — Saldo Acumulado
        if depositos:
            writer.writerow([""] * 14)
            writer.writerow(["Contas Saldo Acumulado", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez", "Total"])
            for conta_nome in sorted(depositos.keys()):
                row = [conta_nome]
                saldo_acumulado = 0.0
                for m in range(1, 13):
                    delta = depositos[conta_nome].get(m, 0) or 0
                    saldo_acumulado += delta
                    row.append(_brl(saldo_acumulado))
                row.append("")
                writer.writerow(row)

        csv_bytes = ("\ufeff" + out.getvalue()).encode("utf-8")
        headers = {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename={nome_arquivo_exportacao(f'despesas-{ano}', 'csv')}",
        }
        return (csv_bytes, 200, headers)
