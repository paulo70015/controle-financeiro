"""
Repositório de CSV - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

import csv
import io
import re
from financeiro.infrastructure.csv_utils import linha_tem_mes_csv, mes_por_cabecalho_csv
from financeiro.infrastructure.export_files import nome_arquivo_exportacao
from financeiro.infrastructure.supabase.client import Client


class SupabaseCSVRepository:
    def __init__(self, client_factory, meses):
        self.client_factory = client_factory
        self.meses = meses

    def desfazer_importacao(self):
        """
        Backup/restore não aplicável no Supabase (backups automáticos via dashboard)
        """
        return ({"erro": "Funcionalidade de desfazer não disponível no Supabase. Use o dashboard para restaurar backups."}, 400)

    def importar_csv(self, file_storage):
        """Importa CSV e sobrescreve dados do ano"""
        client: Client = self.client_factory()
        
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

        # Garante que o ano fique registrado na tabela `anos`
        client.table("anos").upsert({"ano": ano}).execute()

        nomes_m = [
            "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
        ]

        header = []
        linha_cabecalho = 1
        for i, r in enumerate(rows[:5]):
            if any(h.lower().strip().replace("ç", "c") in nomes_m for h in r):
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

        # Deletar dados do ano
        client.table("despesas").delete().eq("ano", ano).execute()
        client.table("receitas").delete().eq("ano", ano).execute()
        client.table("movimentacoes_mensais").delete().eq("ano", ano).execute()
        client.table("depositos_conta").delete().eq("ano", ano).execute()

        importados = {"despesas": 0, "movimentacoes": 0, "depositos": 0, "fixas": 0, "metas": 0, "rendimentos": 0}
        erros = []

        def get_or_create_categoria(nome):
            response = client.table("categorias").select("id").eq("nome", nome).eq("ano", ano).execute()
            if response.data:
                return response.data[0]["id"]
            insert_response = client.table("categorias").insert({
                "nome": nome,
                "ordem": 9999,
                "inclui_fixas": 0,  # INTEGER: 0=false, 1=true
                "ano": ano
            }).execute()
            return insert_response.data[0]["id"]

        def get_or_create_conta(nome):
            response = client.table("contas_correntes").select("id").eq("nome", nome).execute()
            if response.data:
                return response.data[0]["id"]
            insert_response = client.table("contas_correntes").insert({
                "nome": nome,
                "ordem": 9999,
                "saldo_inicial": 0
            }).execute()
            return insert_response.data[0]["id"]

        def get_or_create_local_rendimento(nome):
            response = client.table("rendimentos_locais").select("id").eq("nome", nome).eq("ano", ano).execute()
            if response.data:
                return response.data[0]["id"]
            ordem_response = client.table("rendimentos_locais").select("ordem").eq("ano", ano).order("ordem", desc=True).limit(1).execute()
            prox = (ordem_response.data[0]["ordem"] + 1) if ordem_response.data else 1
            insert_response = client.table("rendimentos_locais").insert({
                "ano": ano,
                "nome": nome,
                "ordem": prox
            }).execute()
            return insert_response.data[0]["id"]

        col_nome = 14
        col_valor = 15
        col_ano = 16
        modo_lateral = None
        modo_vertical = "despesas"

        for row in rows[linha_cabecalho + 1:]:
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
                                    client.table("despesas_fixas_cartao").delete().eq("descricao", nome_lat).eq("ano", ano).execute()
                                    client.table("despesas_fixas_cartao").insert({
                                        "descricao": nome_lat,
                                        "dia": 1,
                                        "valor": val,
                                        "ano": ano
                                    }).execute()
                                    importados["fixas"] += 1
                                except Exception as e:
                                    erros.append(f"Fixa {nome_lat}: {str(e)}")
                        elif modo_lateral == "metas":
                            val = parse_valor(val_lat)
                            ano_meta = None
                            try:
                                ano_meta = int(ano_lat) if ano_lat else None
                            except ValueError:
                                pass
                            if val is not None and val != 0:
                                try:
                                    client.table("metas").delete().eq("descricao", nome_lat).execute()
                                    client.table("metas").insert({
                                        "descricao": nome_lat,
                                        "valor": val,
                                        "ano_meta": ano_meta,
                                        "ano_criacao": ano,
                                        "concluida": 0  # INTEGER: 0=false, 1=true
                                    }).execute()
                                    importados["metas"] += 1
                                except Exception as e:
                                    erros.append(f"Meta {nome_lat}: {str(e)}")

            label = row[0].strip()
            if not label or label.lower().startswith("total"):
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
                        client.table("despesas_fixas_cartao").insert({
                            "descricao": label,
                            "dia": dia,
                            "valor": val,
                            "ano": ano
                        }).execute()
                        importados["fixas"] += 1
                    except Exception:
                        pass
                continue

            if modo_vertical == "metas":
                val_str = row[1].strip() if len(row) > 1 else ""
                ano_str = row[2].strip() if len(row) > 2 else ""
                status_str = row[3].strip().lower() if len(row) > 3 else ""
                val = parse_valor(val_str)
                ano_meta = int(ano_str) if ano_str.isdigit() else None
                concluida = 1 if status_str == "concluida" else 0  # INTEGER: 0=false, 1=true
                if val is not None and val != 0:
                    try:
                        client.table("metas").insert({
                            "descricao": label,
                            "valor": val,
                            "ano_meta": ano_meta,
                            "ano_criacao": ano,
                            "concluida": concluida
                        }).execute()
                        importados["metas"] += 1
                    except Exception:
                        pass
                continue

            if modo_vertical == "rendimentos":
                local_id = get_or_create_local_rendimento(label)
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            try:
                                client.table("rendimentos_lancamentos").delete().eq("ano", ano).eq("mes", mes).eq("local_id", local_id).eq("tipo", "aporte").execute()
                                client.table("rendimentos_lancamentos").insert({
                                    "ano": ano,
                                    "mes": mes,
                                    "local_id": local_id,
                                    "tipo": "aporte",
                                    "valor": val,
                                    "nota": "Importado CSV"
                                }).execute()
                                importados["rendimentos"] += 1
                            except Exception:
                                pass
                continue

            if not is_exported and label.lower() == "rendimento":
                local_id = get_or_create_local_rendimento("Rendimento")
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            try:
                                client.table("rendimentos_lancamentos").delete().eq("ano", ano).eq("mes", mes).eq("local_id", local_id).eq("tipo", "aporte").execute()
                                client.table("rendimentos_lancamentos").insert({
                                    "ano": ano,
                                    "mes": mes,
                                    "local_id": local_id,
                                    "tipo": "aporte",
                                    "valor": val,
                                    "nota": "Importado CSV"
                                }).execute()
                                importados["rendimentos"] += 1
                            except Exception:
                                pass
                continue

            if label.lower() in ("nubank", "movimentacao"):
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            try:
                                client.table("movimentacoes_mensais").insert({
                                    "ano": ano,
                                    "mes": mes,
                                    "valor": val,
                                    "nota": "Importado CSV"
                                }).execute()
                                importados["movimentacoes"] += 1
                            except Exception as e:
                                erros.append(f"Mov mes {mes}: {str(e)}")
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
                            client.table("depositos_conta").insert({
                                "ano": ano,
                                "mes": mes,
                                "conta_id": conta_id,
                                "valor": delta,
                                "nota": "Importado CSV"
                            }).execute()
                            importados["depositos"] += 1
                        except Exception as e:
                            erros.append(f"NuConta mes {mes}: {str(e)}")
                continue

            if "receitas" in label.lower() or "salario" in label.lower():
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor(row[col])
                        if val is not None and val != 0:
                            try:
                                client.table("receitas").insert({
                                    "ano": ano,
                                    "mes": mes,
                                    "descricao": label,
                                    "valor": val,
                                    "nota": "Importado CSV"
                                }).execute()
                            except Exception as e:
                                erros.append(f"Receita mes {mes}: {str(e)}")
                continue

            cat_id = get_or_create_categoria(label)
            if label.strip().lower() == "cartao":
                client.table("categorias").update({"inclui_fixas": 1}).eq("id", cat_id).execute()  # INTEGER: 1=true

            for col, mes in col_to_mes.items():
                if col < len(row):
                    val = parse_valor(row[col])
                    if val is not None and val != 0:
                        try:
                            client.table("despesas").insert({
                                "ano": ano,
                                "mes": mes,
                                "categoria": label,
                                "valor": val,
                                "nota": "Importado CSV"
                            }).execute()
                            importados["despesas"] += 1
                        except Exception as e:
                            erros.append(f"{label} mes {mes}: {str(e)}")

        return ({"ok": True, "ano": ano, "importados": importados, "erros": erros[:10], "undo_available": False}, 200)

    def exportar_csv(self, ano: int):
        """Exporta dados do ano para CSV"""
        client: Client = self.client_factory()
        
        # Categorias
        cats_response = client.table("categorias").select("id, nome, inclui_fixas").eq("ano", ano).order("ordem").execute()
        cats = cats_response.data
        
        # Despesas agregadas
        despesas_response = client.table("despesas").select("mes, categoria, valor, nota").eq("ano", ano).execute()
        despesas = {}
        for r in despesas_response.data:
            cat = r["categoria"]
            mes = r["mes"]
            if cat not in despesas:
                despesas[cat] = {}
            if mes not in despesas[cat]:
                despesas[cat][mes] = {"v": 0, "notas": []}
            despesas[cat][mes]["v"] += r["valor"]
            if r["nota"] and r["nota"].strip():
                despesas[cat][mes]["notas"].append(r["nota"].strip())
        
        # Converter notas para string
        for cat in despesas:
            for mes in despesas[cat]:
                despesas[cat][mes]["notas"] = " | ".join(despesas[cat][mes]["notas"])
        
        # Receitas agregadas
        receitas_response = client.table("receitas").select("mes, valor").eq("ano", ano).execute()
        receitas = {}
        for r in receitas_response.data:
            receitas[r["mes"]] = receitas.get(r["mes"], 0) + r["valor"]
        
        # Fixas
        fixas_response = client.table("despesas_fixas_cartao").select("*").eq("ativa", 1).eq("ano", ano).order("dia").execute()
        fixas = fixas_response.data
        
        # Metas
        metas_response = client.table("metas").select("*").lte("ano_criacao", ano).gte("ano_meta", ano).order("concluida").order("ano_meta").execute()
        metas = metas_response.data
        
        # Rendimentos - locais
        rend_locais_response = client.table("rendimentos_locais").select("id, nome, ordem").eq("ano", ano).order("ordem").order("id").execute()
        rend_locais = rend_locais_response.data
        
        # Rendimentos - lançamentos agregados
        rend_response = client.table("rendimentos_lancamentos").select("mes, local_id, valor").eq("ano", ano).execute()
        rendimentos = {}
        for r in rend_response.data:
            local_id = r["local_id"]
            mes = r["mes"]
            if local_id not in rendimentos:
                rendimentos[local_id] = {}
            rendimentos[local_id][mes] = rendimentos[local_id].get(mes, 0) + r["valor"]
        
        # Exceções de fixas
        fixas_excecoes_response = client.table("fixas_excecoes").select("mes, cat_id").eq("ano", ano).execute()
        fixas_excecoes = {f"{r['cat_id']}_{r['mes']}": True for r in fixas_excecoes_response.data}
        
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
                soma = float(rendimentos.get(rl["id"], {}).get(m, 0) or 0)
                total_linha += soma
                row.append(_brl(soma) if soma else "")
            row.append(_brl(total_linha))
            writer.writerow(row)

        csv_bytes = ("\ufeff" + out.getvalue()).encode("utf-8")
        headers = {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename={nome_arquivo_exportacao(f'despesas-{ano}', 'csv')}",
        }
        return (csv_bytes, 200, headers)
