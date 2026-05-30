"""
Repositório de Dashboard - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

import logging
from datetime import datetime

from postgrest.exceptions import APIError

from financeiro.infrastructure.supabase.client import Client

logger = logging.getLogger(__name__)


class SupabaseDashboardRepository:
    def __init__(self, client_factory, meses):
        self.client_factory = client_factory
        self.meses = meses

    def get_dados_ano(self, ano: int) -> dict:
        """Retorna todos os dados necessários para renderizar o dashboard de um ano"""
        client: Client = self.client_factory()
        rendimentos_realizados_sincronizados = self._sync_rendimentos_realizados(client, ano)
        
        # Categorias
        cats_response = client.table("categorias") \
            .select("id, nome, inclui_fixas, conta_vinculada_id, tooltip, is_cartao") \
            .eq("ano", ano) \
            .order("ordem") \
            .execute()
        cats = cats_response.data
        
        # Despesas agregadas por mês e categoria
        desp_response = client.table("despesas") \
            .select("mes, categoria, valor, ignorar_total, nota, data_alteracao") \
            .eq("ano", ano) \
            .execute()
        
        despesas = {}
        for r in desp_response.data:
            cat = r["categoria"]
            mes = r["mes"]
            valor = r["valor"] if not r["ignorar_total"] else 0
            valor_ignorado = r["valor"] if r["ignorar_total"] else 0
            
            if cat not in despesas:
                despesas[cat] = {}
            if mes not in despesas[cat]:
                despesas[cat][mes] = {"valor": 0, "valor_ignorado": 0, "notas": [], "last_modified": None}
            
            despesas[cat][mes]["valor"] += valor
            despesas[cat][mes]["valor_ignorado"] += valor_ignorado
            
            # Formatar nota
            if r["ignorar_total"]:
                nota_fmt = f"💳 {r['nota'].strip() or 'Cartão'} (R$ {r['valor']:.2f})"
                despesas[cat][mes]["notas"].append(nota_fmt)
            elif r["nota"] and r["nota"].strip():
                despesas[cat][mes]["notas"].append(r["nota"].strip())
            
            # Última modificação
            if r["data_alteracao"] and (not despesas[cat][mes]["last_modified"] or r["data_alteracao"] > despesas[cat][mes]["last_modified"]):
                despesas[cat][mes]["last_modified"] = r["data_alteracao"]
        
        # Converter notas de lista para string
        for cat in despesas:
            for mes in despesas[cat]:
                despesas[cat][mes]["notas"] = "\n".join(despesas[cat][mes]["notas"])
        
        # Receitas agregadas por mês
        rec_response = client.table("receitas") \
            .select("mes, valor, data_alteracao, status") \
            .eq("ano", ano) \
            .execute()
        
        receitas = {}
        receitas_mod = {}
        receitas_status = {}
        for r in rec_response.data:
            mes = r["mes"]
            receitas[mes] = receitas.get(mes, 0) + r["valor"]
            
            if r["data_alteracao"] and (mes not in receitas_mod or r["data_alteracao"] > receitas_mod[mes]):
                receitas_mod[mes] = r["data_alteracao"]
            
            if mes not in receitas_status or r["status"] > receitas_status[mes]:
                receitas_status[mes] = r["status"]
        
        # Fixas
        fixas_response = client.table("despesas_fixas_cartao") \
            .select("*") \
            .eq("ativa", 1) \
            .eq("ano", ano) \
            .order("dia") \
            .execute()
        fixas = fixas_response.data
        
        # Metas
        metas_response = client.table("metas") \
            .select("*") \
            .lte("ano_criacao", ano) \
            .gte("ano_meta", ano) \
            .order("concluida") \
            .order("ano_meta") \
            .execute()
        metas = metas_response.data
        
        # Contas
        contas_response = client.table("contas_correntes") \
            .select("id, nome, ordem, saldo_inicial") \
            .order("ordem") \
            .execute()
        contas = contas_response.data
        
        # Movimentações mensais
        mov_response = client.table("movimentacoes_mensais") \
            .select("mes, conta_id, valor, nota") \
            .eq("ano", ano) \
            .execute()
        movimentacoes = {
            r["mes"]: {"conta_id": r["conta_id"], "valor": r["valor"], "nota": r["nota"]}
            for r in mov_response.data
        }
        
        # Depósitos agregados por mês e conta
        dep_response = client.table("depositos_conta") \
            .select("mes, conta_id, valor") \
            .eq("ano", ano) \
            .execute()
        
        movimentos = {}
        for r in dep_response.data:
            cid = str(r["conta_id"])
            mes = r["mes"]
            if cid not in movimentos:
                movimentos[cid] = {}
            movimentos[cid][mes] = movimentos[cid].get(mes, 0) + r["valor"]
        
        # Adicionar movimentações mensais aos movimentos
        for mes, mv in movimentacoes.items():
            cid = str(mv["conta_id"])
            if cid not in movimentos:
                movimentos[cid] = {}
            movimentos[cid][mes] = movimentos[cid].get(mes, 0) + mv["valor"]
        
        # Calcular saldos acumulados
        saldos = {}
        saldos_ini = {}
        for conta in contas:
            cid = str(conta["id"])
            si = self._saldo_inicial_conta(client, conta["id"], conta["saldo_inicial"], ano)
            saldos_ini[cid] = si
            mov = movimentos.get(cid, {})
            saldo = si
            saldos[cid] = {}
            for m in range(1, 13):
                saldo = round(saldo + mov.get(m, 0), 2)
                saldos[cid][m] = saldo
        
        # Anos — fonte da verdade: tabela `anos`
        anos_resp = client.table("anos").select("ano").execute()
        anos_list = sorted(
            {int(r["ano"]) for r in (anos_resp.data or []) if r.get("ano") is not None},
            reverse=True
        )

        # Config
        cfg_response = client.table("config").select("chave, valor").execute()
        config = {r["chave"]: r["valor"] for r in cfg_response.data}
        
        # Adicionar dia_inicio_mes_fiscal padrão se não existir
        if "dia_inicio_mes_fiscal" not in config:
            config["dia_inicio_mes_fiscal"] = "25"
        
        # Exceções de fixas
        exc_response = client.table("fixas_excecoes") \
            .select("mes, cat_id") \
            .eq("ano", ano) \
            .execute()
        fixas_excecoes = {f"{r['cat_id']}_{r['mes']}": True for r in exc_response.data}
        
        # Fixas aplicadas manualmente
        fixas_manual_response = client.table("fixas_aplicadas_manual") \
            .select("mes, fixa_id") \
            .eq("ano", ano) \
            .execute()
        fixas_aplicadas_manual = {f"{r['fixa_id']}_{r['mes']}": True for r in fixas_manual_response.data}
        
        # Status de pagamento
        pg_response = client.table("pagamento_status") \
            .select("mes, categoria, status") \
            .eq("ano", ano) \
            .execute()
        pagamentos = {}
        for r in pg_response.data:
            if r["categoria"] not in pagamentos:
                pagamentos[r["categoria"]] = {}
            pagamentos[r["categoria"]][r["mes"]] = r["status"]

        rend_realizados_response = client.table("rendimentos_realizados") \
            .select("mes, status") \
            .eq("ano", ano) \
            .execute()
        rendimentos_realizados = {r["mes"]: int(r["status"] or 0) for r in rend_realizados_response.data}
        if not rendimentos_realizados_sincronizados:
            rendimentos_realizados = self._rendimentos_realizados_calendario(ano)
        
        # Rendimentos - locais
        rend_locais_response = client.table("rendimentos_locais") \
            .select("id, ano, nome, ordem, projecao_taxa") \
            .eq("ano", ano) \
            .order("ordem") \
            .order("id") \
            .execute()
        rend_locais = rend_locais_response.data
        
        # Rendimentos - lançamentos agregados
        rend_response = client.table("rendimentos_lancamentos") \
            .select("mes, local_id, tipo, valor, nota, data_alteracao") \
            .eq("ano", ano) \
            .execute()
        
        rendimentos = {}
        for r in rend_response.data:
            local_id = str(r["local_id"])
            mes = r["mes"]
            
            if local_id not in rendimentos:
                rendimentos[local_id] = {}
            if mes not in rendimentos[local_id]:
                rendimentos[local_id][mes] = {
                    "aporte": 0.0,
                    "rendimento": 0.0,
                    "projecao": 0.0,
                    "qtd_rendimentos": 0,
                    "last_modified": None
                }
            
            if r["tipo"] == "aporte":
                rendimentos[local_id][mes]["aporte"] += r["valor"]
            elif r["tipo"] == "rendimento":
                if r["nota"] == "Projeção":
                    rendimentos[local_id][mes]["projecao"] += r["valor"]
                else:
                    rendimentos[local_id][mes]["rendimento"] += r["valor"]
                    rendimentos[local_id][mes]["qtd_rendimentos"] += 1
            
            if r["data_alteracao"] and (not rendimentos[local_id][mes]["last_modified"] or r["data_alteracao"] > rendimentos[local_id][mes]["last_modified"]):
                rendimentos[local_id][mes]["last_modified"] = r["data_alteracao"]
        
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

    def _rendimentos_realizados_calendario(self, ano: int) -> dict[int, int]:
        return {mes: 1 for mes in self._meses_rendimentos_realizados(ano)}

    def _sync_rendimentos_realizados(self, client: Client, ano: int) -> bool:
        meses_realizados = self._meses_rendimentos_realizados(ano)
        data_alteracao = datetime.now().isoformat()
        try:
            client.table("anos").upsert({"ano": ano}).execute()
            existentes_response = client.table("rendimentos_realizados") \
                .select("mes") \
                .eq("ano", ano) \
                .execute()
            meses_existentes = {int(r["mes"]) for r in (existentes_response.data or []) if r.get("mes") is not None}

            if meses_realizados:
                client.table("rendimentos_realizados").upsert(
                    [
                        {
                            "ano": ano,
                            "mes": mes,
                            "status": 1,
                            "data_alteracao": data_alteracao,
                        }
                        for mes in meses_realizados
                    ],
                    on_conflict="ano,mes",
                ).execute()
                meses_para_remover = sorted(meses_existentes - set(meses_realizados))
                if meses_para_remover:
                    client.table("rendimentos_realizados") \
                        .delete() \
                        .eq("ano", ano) \
                        .in_("mes", meses_para_remover) \
                        .execute()
            else:
                client.table("rendimentos_realizados") \
                    .delete() \
                    .eq("ano", ano) \
                    .execute()
        except APIError as exc:
            if getattr(exc, "code", None) != "42501":
                raise
            logger.warning(
                "Sem permissao RLS para sincronizar rendimentos_realizados no Supabase; "
                "usando calendario calculado em memoria. Detalhe: %s",
                exc,
            )
            return False
        return True

    def _saldo_inicial_conta(self, client: Client, conta_id: int, saldo_inicial_config: float, ano_alvo: int) -> float:
        """Calcula saldo inicial da conta considerando anos anteriores"""
        # Buscar primeiro ano com depósitos
        dep_response = client.table("depositos_conta") \
            .select("ano") \
            .eq("conta_id", conta_id) \
            .lt("ano", ano_alvo) \
            .order("ano") \
            .limit(1) \
            .execute()
        primeiro = dep_response.data[0]["ano"] if dep_response.data else None
        
        # Buscar primeiro ano com movimentações
        mov_response = client.table("movimentacoes_mensais") \
            .select("ano") \
            .eq("conta_id", conta_id) \
            .lt("ano", ano_alvo) \
            .order("ano") \
            .limit(1) \
            .execute()
        primeiro_mov = mov_response.data[0]["ano"] if mov_response.data else None
        
        anos_ant = [x for x in [primeiro, primeiro_mov] if x is not None]
        if not anos_ant:
            return saldo_inicial_config or 0.0
        
        saldo = saldo_inicial_config or 0.0
        
        # Somar depósitos de anos anteriores
        dep_sum_response = client.table("depositos_conta") \
            .select("valor") \
            .eq("conta_id", conta_id) \
            .lt("ano", ano_alvo) \
            .execute()
        t_dep = sum(r["valor"] for r in dep_sum_response.data)
        
        # Somar movimentações de anos anteriores
        mov_sum_response = client.table("movimentacoes_mensais") \
            .select("valor") \
            .eq("conta_id", conta_id) \
            .lt("ano", ano_alvo) \
            .execute()
        t_mov = sum(r["valor"] for r in mov_sum_response.data)
        
        saldo += t_dep + t_mov
        return round(saldo, 2)

    def is_ano_bloqueado(self, ano: int) -> bool:
        """Verifica se o ano está bloqueado"""
        client: Client = self.client_factory()
        
        chave = f"ano_bloqueado_{ano}"
        response = client.table("config") \
            .select("valor") \
            .eq("chave", chave) \
            .execute()
        
        if response.data:
            valor = response.data[0]["valor"]
            return str(valor) == "1"
        return False
