"""
Repositório de Despesas - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

from financeiro.infrastructure.supabase.client import Client
from financeiro.domain.despesas.entities import Despesa, DespesaLote


class SupabaseDespesasRepository:
    def __init__(self, client_factory):
        self.client_factory = client_factory

    def add_despesa(self, despesa: Despesa) -> int:
        """Insere despesa e retorna o ID. Persistência pura."""
        client: Client = self.client_factory()
        
        response = client.table("despesas").insert({
            "ano": despesa.ano,
            "mes": despesa.mes,
            "categoria": despesa.categoria,
            "valor": despesa.valor,
            "nota": despesa.nota,
            "ignorar_total": getattr(despesa, "ignorar_total", False)
        }).execute()
        
        return response.data[0]["id"]

    def add_deposito_vinculado_simples(
        self,
        ano: int,
        mes: int,
        conta_id: int,
        valor: float,
        nota: str,
        despesa_id: int,
    ) -> None:
        """Insere depósito vinculado a uma despesa. Persistência pura."""
        client: Client = self.client_factory()
        
        client.table("depositos_conta").insert({
            "ano": ano,
            "mes": mes,
            "conta_id": conta_id,
            "valor": valor,
            "nota": nota,
            "despesa_id": despesa_id
        }).execute()

    def add_despesa_lote_com_depositos(
        self,
        despesas_data: list[dict],
        depositos_data: list[dict],
    ) -> list[int]:
        """Insere lote de despesas e depósitos em transação atômica. Retorna IDs."""
        client: Client = self.client_factory()
        
        # Inserir despesas em lote
        despesas_insert = [{
            "ano": d['ano'],
            "mes": d['mes'],
            "categoria": d['categoria'],
            "valor": d['valor'],
            "nota": d['nota'],
            "ignorar_total": d['ignorar_total']
        } for d in despesas_data]
        
        response = client.table("despesas").insert(despesas_insert).execute()
        despesa_ids = [d["id"] for d in response.data]
        
        # Inserir depósitos vinculados
        if depositos_data:
            depositos_insert = []
            for dep in depositos_data:
                idx = dep.get('despesa_idx')
                desp_id = despesa_ids[idx] if idx is not None else None
                depositos_insert.append({
                    "ano": dep['ano'],
                    "mes": dep['mes'],
                    "conta_id": dep['conta_id'],
                    "valor": dep['valor'],
                    "nota": dep['nota'],
                    "despesa_id": desp_id
                })
            
            client.table("depositos_conta").insert(depositos_insert).execute()
        
        return despesa_ids

    def get_despesa_by_id(self, despesa_id: int) -> dict | None:
        """Retorna dados da despesa por ID."""
        client: Client = self.client_factory()
        
        response = client.table("despesas") \
            .select("ano, mes, categoria, valor, nota, ignorar_total") \
            .eq("id", despesa_id) \
            .execute()
        
        return response.data[0] if response.data else None

    def update_despesa_com_deposito(
        self,
        despesa_id: int,
        valor: float,
        nota: str,
        ignorar_total: bool,
        conta_id: int | None,
        ano: int,
        mes: int,
        categoria: str,
    ) -> None:
        """Atualiza despesa e recria depósito vinculado se aplicável."""
        client: Client = self.client_factory()
        
        # Atualizar despesa
        client.table("despesas").update({
            "mes": mes,
            "valor": valor,
            "nota": nota,
            "ignorar_total": ignorar_total
        }).eq("id", despesa_id).execute()
        
        # Remover depósito antigo
        client.table("depositos_conta") \
            .delete() \
            .eq("despesa_id", despesa_id) \
            .execute()
        
        # Recriar depósito se aplicável
        if conta_id and not ignorar_total and valor > 0:
            client.table("depositos_conta").insert({
                "ano": ano,
                "mes": mes,
                "conta_id": conta_id,
                "valor": -valor,
                "nota": nota or categoria,
                "despesa_id": despesa_id
            }).execute()

    def delete_despesa(self, despesa_id: int) -> None:
        """Deleta despesa e depósitos vinculados (CASCADE automático)"""
        client: Client = self.client_factory()
        
        # Deletar depósitos vinculados primeiro
        client.table("depositos_conta") \
            .delete() \
            .eq("despesa_id", despesa_id) \
            .execute()
        
        # Deletar despesa
        client.table("despesas") \
            .delete() \
            .eq("id", despesa_id) \
            .execute()

    def get_despesas_detalhe(self, ano: int, mes: int, categoria: str) -> list[dict]:
        """Retorna todas as despesas de uma célula (ano × mes × categoria)"""
        client: Client = self.client_factory()
        
        response = client.table("despesas") \
            .select("*") \
            .eq("ano", ano) \
            .eq("mes", mes) \
            .eq("categoria", categoria) \
            .execute()
        
        return response.data

    def delete_despesas_da_categoria_no_ano(self, ano: int, categoria: str) -> None:
        """Deleta todas as despesas de uma categoria em um ano"""
        client: Client = self.client_factory()
        
        # Buscar IDs das despesas
        response = client.table("despesas") \
            .select("id") \
            .eq("ano", ano) \
            .eq("categoria", categoria) \
            .execute()
        
        ids = [d["id"] for d in response.data]
        
        # Deletar depósitos vinculados
        if ids:
            client.table("depositos_conta") \
                .delete() \
                .in_("despesa_id", ids) \
                .execute()
        
        # Deletar despesas
        client.table("despesas") \
            .delete() \
            .eq("ano", ano) \
            .eq("categoria", categoria) \
            .execute()
