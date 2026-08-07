"""
Repositório de CSV - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

import csv
import io
from financeiro.infrastructure.csv_utils import (
    detectar_cabecalho_csv,
    montar_csv_exportacao,
    parse_valor_csv,
)
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

        linha_cabecalho, col_to_mes = detectar_cabecalho_csv(rows)

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
                            val = parse_valor_csv(val_lat)
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
                            val = parse_valor_csv(val_lat)
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
                val = parse_valor_csv(val_str)
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
                val = parse_valor_csv(val_str)
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
                    client.table("rendimentos_locais").update({"conta_vinculada_id": conta_id}).eq("id", local_id).execute()

                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor_csv(row[col])
                        if val is not None and val != 0:
                            if tipo_forcado:
                                tipo = tipo_forcado
                            else:
                                tipo = 'saque' if val < 0 else 'aporte'
                            valor_abs = abs(val)
                            try:
                                client.table("rendimentos_lancamentos").delete().eq("ano", ano).eq("mes", mes).eq("local_id", local_id).eq("tipo", tipo).execute()
                                client.table("rendimentos_lancamentos").insert({
                                    "ano": ano,
                                    "mes": mes,
                                    "local_id": local_id,
                                    "tipo": tipo,
                                    "valor": valor_abs,
                                    "nota": "Importado CSV"
                                }).execute()
                                importados["rendimentos"] += 1
                            except Exception:
                                pass
                continue

            if modo_vertical == "receitas":
                # Label é ignorado — usamos "Receitas" como descrição
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor_csv(row[col])
                        if val is not None and val != 0:
                            try:
                                client.table("receitas").insert({
                                    "ano": ano,
                                    "mes": mes,
                                    "descricao": "Receitas",
                                    "valor": val,
                                    "nota": "Importado CSV"
                                }).execute()
                            except Exception as e:
                                erros.append(f"Receita mes {mes}: {str(e)}")
                continue

            if modo_vertical == "movimentacoes":
                conta_id = get_or_create_conta(label)
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor_csv(row[col])
                        if val is not None and val != 0:
                            try:
                                client.table("movimentacoes_mensais").insert({
                                    "ano": ano,
                                    "mes": mes,
                                    "conta_id": conta_id,
                                    "valor": val,
                                    "nota": "Importado CSV",
                                    "tipo": ""
                                }).execute()
                                importados["movimentacoes"] += 1
                            except Exception as e:
                                erros.append(f"Mov mes {mes}: {str(e)}")
                continue

            if modo_vertical == "contas":
                conta_id = get_or_create_conta(label)
                saldos_mes = {}
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor_csv(row[col])
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
                            erros.append(f"Conta {label} mes {mes}: {str(e)}")
                continue

            # -- Fallbacks para CSVs não-exportados (formato legado) --
            if not is_exported and label.lower() == "rendimento":
                local_id = get_or_create_local_rendimento("Rendimento")
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor_csv(row[col])
                        if val is not None and val != 0:
                            tipo = 'saque' if val < 0 else 'aporte'
                            valor_abs = abs(val)
                            try:
                                client.table("rendimentos_lancamentos").delete().eq("ano", ano).eq("mes", mes).eq("local_id", local_id).eq("tipo", tipo).execute()
                                client.table("rendimentos_lancamentos").insert({
                                    "ano": ano,
                                    "mes": mes,
                                    "local_id": local_id,
                                    "tipo": tipo,
                                    "valor": valor_abs,
                                    "nota": "Importado CSV"
                                }).execute()
                                importados["rendimentos"] += 1
                            except Exception:
                                pass
                continue

            if not is_exported and label.lower() in ("nubank", "movimentacao"):
                conta_id = get_or_create_conta("NuConta")
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor_csv(row[col])
                        if val is not None and val != 0:
                            try:
                                client.table("movimentacoes_mensais").insert({
                                    "ano": ano,
                                    "mes": mes,
                                    "conta_id": conta_id,
                                    "valor": val,
                                    "nota": "Importado CSV",
                                    "tipo": ""
                                }).execute()
                                importados["movimentacoes"] += 1
                            except Exception as e:
                                erros.append(f"Mov mes {mes}: {str(e)}")
                continue

            if not is_exported and label.lower() in ("nuconta", "nu conta", "conta", "contas saldo acumulado"):
                conta_id = get_or_create_conta("NuConta")
                saldos_mes = {}
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor_csv(row[col])
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

            if not is_exported and ("receitas" in label.lower() or "salario" in label.lower()):
                for col, mes in col_to_mes.items():
                    if col < len(row):
                        val = parse_valor_csv(row[col])
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
                    val = parse_valor_csv(row[col])
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
        
        # Rendimentos - locais (com conta vinculada)
        rend_locais_response = client.table("rendimentos_locais").select("id, nome, ordem, conta_vinculada_id").eq("ano", ano).order("ordem").order("id").execute()
        rend_locais = rend_locais_response.data
        # Resolver nomes das contas vinculadas
        for rl in rend_locais:
            if rl.get("conta_vinculada_id"):
                cc_response = client.table("contas_correntes").select("nome").eq("id", rl["conta_vinculada_id"]).execute()
                rl["conta_vinculada_nome"] = cc_response.data[0]["nome"] if cc_response.data else ""
            else:
                rl["conta_vinculada_nome"] = ""
        
        # Rendimentos - lançamentos agregados por tipo
        rend_response = client.table("rendimentos_lancamentos").select("mes, local_id, tipo, valor").eq("ano", ano).execute()
        rendimentos = {}  # chave: (local_id, tipo) -> {mes: total}
        rend_tipos_por_local = {}  # chave: local_id -> set de tipos
        for r in rend_response.data:
            local_id = r["local_id"]
            tipo = r.get("tipo", "aporte")
            key = (local_id, tipo)
            if key not in rendimentos:
                rendimentos[key] = {}
            rendimentos[key][r["mes"]] = rendimentos[key].get(r["mes"], 0) + r["valor"]
            if local_id not in rend_tipos_por_local:
                rend_tipos_por_local[local_id] = set()
            rend_tipos_por_local[local_id].add(tipo)
        
        # Movimentações mensais
        mov_response = client.table("movimentacoes_mensais").select("mes, conta_id, valor").eq("ano", ano).execute()
        movimentacoes = {}  # chave: conta_id -> {mes: total}
        contas_mov = {}  # cache conta_id -> nome
        for r in mov_response.data:
            cid = r["conta_id"]
            if cid not in contas_mov:
                cc = client.table("contas_correntes").select("nome").eq("id", cid).execute()
                contas_mov[cid] = cc.data[0]["nome"] if cc.data else f"Conta {cid}"
            nome = contas_mov[cid]
            if nome not in movimentacoes:
                movimentacoes[nome] = {}
            movimentacoes[nome][r["mes"]] = movimentacoes[nome].get(r["mes"], 0) + r["valor"]
        
        # Depósitos / saldo acumulado por conta
        dep_response = client.table("depositos_conta").select("mes, conta_id, valor").eq("ano", ano).execute()
        depositos = {}  # chave: conta_nome -> {mes: delta}
        for r in dep_response.data:
            cid = r["conta_id"]
            if cid not in contas_mov:
                cc = client.table("contas_correntes").select("nome").eq("id", cid).execute()
                contas_mov[cid] = cc.data[0]["nome"] if cc.data else f"Conta {cid}"
            nome = contas_mov[cid]
            if nome not in depositos:
                depositos[nome] = {}
            depositos[nome][r["mes"]] = depositos[nome].get(r["mes"], 0) + r["valor"]
        
        # Exceções de fixas
        fixas_excecoes_response = client.table("fixas_excecoes").select("mes, cat_id").eq("ano", ano).execute()
        fixas_excecoes = {f"{r['cat_id']}_{r['mes']}": True for r in fixas_excecoes_response.data}
        
        csv_bytes = montar_csv_exportacao(
            ano, self.meses, cats, despesas, receitas, fixas, metas,
            rend_locais, rendimentos, rend_tipos_por_local,
            movimentacoes, depositos, fixas_excecoes,
        )
        headers = {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename={nome_arquivo_exportacao(f'despesas-{ano}', 'csv')}",
        }
        return (csv_bytes, 200, headers)
