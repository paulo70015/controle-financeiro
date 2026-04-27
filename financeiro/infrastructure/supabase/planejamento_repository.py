"""
Repositório de Planejamento (Fixas, Metas, Status) - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

from financeiro.infrastructure.supabase.client import Client
from financeiro.domain.planejamento.entities import Fixa, Meta, PagamentoStatus


class SupabasePlanejamentoRepository:
    def __init__(self, client_factory):
        self.client_factory = client_factory



    def _normalizar_cat_id(self, client: Client, cat_id, ano):
        """Normaliza cat_id para o ano correto (remapeia se necessário)"""
        if not cat_id:
            return None
        try:
            cat_id = int(cat_id)
        except Exception:
            return None

        response = client.table("categorias") \
            .select("id, nome, ano") \
            .eq("id", cat_id) \
            .execute()
        
        if not response.data:
            return None
        
        cat = response.data[0]
        if cat["ano"] == ano:
            return cat["id"]

        # Corrige IDs de categoria vindos de outro ano (mesmo nome)
        cat_dest_response = client.table("categorias") \
            .select("id") \
            .eq("ano", ano) \
            .eq("nome", cat["nome"]) \
            .execute()
        
        return cat_dest_response.data[0]["id"] if cat_dest_response.data else None

    def add_fixa(self, fixa: Fixa) -> None:
        """Adiciona despesa fixa"""
        client: Client = self.client_factory()
        cat_id = self._normalizar_cat_id(client, fixa.cat_id, fixa.ano)
        
        client.table("despesas_fixas_cartao").insert({
            "descricao": fixa.descricao,
            "valor": fixa.valor,
            "dia": fixa.dia,
            "cat_id": cat_id,
            "ano": fixa.ano
        }).execute()

    def update_fixa(self, fixa_id: int, payload: dict) -> None:
        """Atualiza despesa fixa"""
        client: Client = self.client_factory()
        
        # Buscar ano da fixa
        fixa_response = client.table("despesas_fixas_cartao") \
            .select("ano") \
            .eq("id", fixa_id) \
            .execute()
        
        ano_fixa = fixa_response.data[0]["ano"] if fixa_response.data else None
        cat_id = self._normalizar_cat_id(client, payload.get("cat_id"), ano_fixa) if ano_fixa else None
        
        client.table("despesas_fixas_cartao").update({
            "descricao": payload["descricao"],
            "dia": payload.get("dia", 0),
            "valor": payload["valor"],
            "cat_id": cat_id
        }).eq("id", fixa_id).execute()

    def delete_fixa(self, fixa_id: int) -> None:
        """Deleta despesa fixa"""
        client: Client = self.client_factory()
        
        client.table("despesas_fixas_cartao") \
            .delete() \
            .eq("id", fixa_id) \
            .execute()

    def add_meta(self, meta: Meta) -> None:
        """Adiciona meta"""
        client: Client = self.client_factory()
        
        client.table("metas").insert({
            "descricao": meta.descricao,
            "valor": meta.valor,
            "ano_meta": meta.ano_meta,
            "ano_criacao": meta.ano_criacao
        }).execute()

    def update_meta(self, meta_id: int, payload: dict, method: str) -> None:
        """Atualiza ou deleta meta"""
        client: Client = self.client_factory()
        
        if method == "DELETE":
            client.table("metas") \
                .delete() \
                .eq("id", meta_id) \
                .execute()
        else:
            if "concluida" in payload:
                # Converter boolean para INTEGER (0/1)
                concluida_int = 1 if payload["concluida"] else 0
                client.table("metas").update({
                    "concluida": concluida_int
                }).eq("id", meta_id).execute()
            else:
                client.table("metas").update({
                    "descricao": payload["descricao"],
                    "valor": payload["valor"],
                    "ano_meta": payload["ano_meta"]
                }).eq("id", meta_id).execute()

    def toggle_fixa_excecao(self, payload: dict, method: str) -> None:
        """Adiciona ou remove exceção de fixa"""
        client: Client = self.client_factory()
        
        if method == "POST":
            # Inserir exceção (ON CONFLICT DO NOTHING via upsert)
            try:
                client.table("fixas_excecoes").insert({
                    "ano": payload["ano"],
                    "mes": payload["mes"],
                    "cat_id": payload["cat_id"]
                }).execute()
            except Exception:
                pass  # Ignorar se já existe
        else:
            # Remover exceção
            client.table("fixas_excecoes") \
                .delete() \
                .eq("ano", payload["ano"]) \
                .eq("mes", payload["mes"]) \
                .eq("cat_id", payload["cat_id"]) \
                .execute()
            
            # Buscar nome da categoria
            cat_response = client.table("categorias") \
                .select("nome") \
                .eq("id", payload["cat_id"]) \
                .execute()
            
            if cat_response.data:
                cat_nome = cat_response.data[0]["nome"]
                
                # Buscar despesas fixas geradas
                despesas_response = client.table("despesas") \
                    .select("id") \
                    .eq("ano", payload["ano"]) \
                    .eq("mes", payload["mes"]) \
                    .eq("categoria", cat_nome) \
                    .eq("nota", "Soma das Despesas Fixas\u200b") \
                    .execute()
                
                ids = [d["id"] for d in despesas_response.data]
                
                # Deletar depósitos e despesas vinculadas
                if ids:
                    client.table("depositos_conta") \
                        .delete() \
                        .in_("despesa_id", ids) \
                        .execute()
                    
                    client.table("despesas") \
                        .delete() \
                        .in_("id", ids) \
                        .execute()

    def save_pagamento_status(self, status: PagamentoStatus) -> None:
        """Salva status de pagamento e gera despesa fixa se necessário"""
        client: Client = self.client_factory()
        
        # Buscar status atual
        status_response = client.table("pagamento_status") \
            .select("status") \
            .eq("ano", status.ano) \
            .eq("mes", status.mes) \
            .eq("categoria", status.categoria) \
            .execute()
        
        status_atual = status_response.data[0]["status"] if status_response.data else 0

        if status.status == 0:
            # Deletar status
            client.table("pagamento_status") \
                .delete() \
                .eq("ano", status.ano) \
                .eq("mes", status.mes) \
                .eq("categoria", status.categoria) \
                .execute()
            
            # Buscar categoria
            cat_response = client.table("categorias") \
                .select("id") \
                .eq("nome", status.categoria) \
                .eq("ano", status.ano) \
                .execute()
            
            if cat_response.data:
                cat_id = cat_response.data[0]["id"]
                
                # Deletar exceção
                client.table("fixas_excecoes") \
                    .delete() \
                    .eq("ano", status.ano) \
                    .eq("mes", status.mes) \
                    .eq("cat_id", cat_id) \
                    .execute()
            
            # Deletar despesas fixas geradas
            despesas_response = client.table("despesas") \
                .select("id") \
                .eq("ano", status.ano) \
                .eq("mes", status.mes) \
                .eq("categoria", status.categoria) \
                .eq("nota", "Soma das Despesas Fixas\u200b") \
                .execute()
            
            ids = [d["id"] for d in despesas_response.data]
            
            if ids:
                client.table("depositos_conta") \
                    .delete() \
                    .in_("despesa_id", ids) \
                    .execute()
                
                client.table("despesas") \
                    .delete() \
                    .in_("id", ids) \
                    .execute()
        else:
            # Upsert status
            client.table("pagamento_status").upsert({
                "ano": status.ano,
                "mes": status.mes,
                "categoria": status.categoria,
                "status": status.status
            }, on_conflict="ano,mes,categoria").execute()

        # Gerar despesa fixa se status mudou de 0 para > 0
        if status_atual == 0 and status.status > 0:
            cat_response = client.table("categorias") \
                .select("id, inclui_fixas, conta_vinculada_id") \
                .eq("nome", status.categoria) \
                .eq("ano", status.ano) \
                .execute()
            
            if cat_response.data:
                cat = cat_response.data[0]
                cat_id = cat["id"]
                
                # Verificar se não há exceção
                exc_response = client.table("fixas_excecoes") \
                    .select("id") \
                    .eq("ano", status.ano) \
                    .eq("mes", status.mes) \
                    .eq("cat_id", cat_id) \
                    .execute()
                
                if not exc_response.data:
                    # Buscar fixas aplicáveis
                    if cat["inclui_fixas"]:
                        fixas_response = client.table("despesas_fixas_cartao") \
                            .select("*") \
                            .eq("ativa", 1) \
                            .eq("ano", status.ano) \
                            .or_(f"cat_id.eq.{cat_id},cat_id.is.null") \
                            .execute()
                    else:
                        fixas_response = client.table("despesas_fixas_cartao") \
                            .select("*") \
                            .eq("ativa", 1) \
                            .eq("ano", status.ano) \
                            .eq("cat_id", cat_id) \
                            .execute()
                    
                    fixas = fixas_response.data
                    
                    if fixas:
                        total_fixas = sum(f["valor"] for f in fixas)
                        total_fixas = round(total_fixas, 2)
                        
                        if total_fixas != 0:
                            nota_fixa = "Soma das Despesas Fixas\u200b"
                            
                            # Inserir despesa
                            desp_response = client.table("despesas").insert({
                                "ano": status.ano,
                                "mes": status.mes,
                                "categoria": status.categoria,
                                "valor": total_fixas,
                                "nota": nota_fixa
                            }).execute()
                            
                            despesa_id = desp_response.data[0]["id"]
                            
                            # Inserir depósito se conta vinculada
                            if cat["conta_vinculada_id"]:
                                client.table("depositos_conta").insert({
                                    "ano": status.ano,
                                    "mes": status.mes,
                                    "conta_id": cat["conta_vinculada_id"],
                                    "valor": -total_fixas,
                                    "nota": nota_fixa,
                                    "despesa_id": despesa_id
                                }).execute()
                        
                        # Inserir exceção para evitar duplicação
                        try:
                            client.table("fixas_excecoes").insert({
                                "ano": status.ano,
                                "mes": status.mes,
                                "cat_id": cat_id
                            }).execute()
                        except Exception:
                            pass  # Ignorar se já existe

    def toggle_fixa_aplicada_manual(self, payload: dict, method: str) -> None:
        """Marca/desmarca uma fixa como aplicada manualmente"""
        client: Client = self.client_factory()
        
        if method == "POST":
            # Marcar como aplicada
            try:
                client.table("fixas_aplicadas_manual").insert({
                    "ano": payload["ano"],
                    "mes": payload["mes"],
                    "fixa_id": payload["fixa_id"]
                }).execute()
            except Exception:
                pass  # Ignorar se já existe
        else:
            # Desmarcar
            client.table("fixas_aplicadas_manual") \
                .delete() \
                .eq("ano", payload["ano"]) \
                .eq("mes", payload["mes"]) \
                .eq("fixa_id", payload["fixa_id"]) \
                .execute()
