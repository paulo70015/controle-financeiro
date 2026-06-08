"""
Repositório de Rendimentos - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

from typing import Optional
from financeiro.infrastructure.supabase.client import Client
from financeiro.domain.rendimentos.entities import RendimentoLancamento, RendimentoLocal


class SupabaseRendimentosRepository:
    def __init__(self, client_factory):
        self.client_factory = client_factory

    def get_locais(self, ano: int) -> list[dict]:
        """Retorna todos os locais de rendimento de um ano"""
        client: Client = self.client_factory()
        
        response = client.table("rendimentos_locais") \
            .select("id, ano, nome, ordem, projecao_taxa, conta_vinculada_id") \
            .eq("ano", ano) \
            .order("ordem") \
            .order("id") \
            .execute()
        
        return response.data

    def add_local(self, local: RendimentoLocal) -> int:
        """Adiciona local de rendimento com ordem sequencial"""
        client: Client = self.client_factory()
        
        # Obter próxima ordem
        response = client.table("rendimentos_locais") \
            .select("ordem") \
            .eq("ano", local.ano) \
            .order("ordem", desc=True) \
            .limit(1) \
            .execute()
        
        prox_ordem = (response.data[0]["ordem"] + 1) if response.data else 1
        
        # Inserir local
        local_response = client.table("rendimentos_locais").insert({
            "ano": local.ano,
            "nome": local.nome,
            "ordem": prox_ordem,
            "conta_vinculada_id": local.conta_vinculada_id,
        }).execute()
        
        return local_response.data[0]["id"]

    def update_local(self, local_id: int, nome: str, conta_vinculada_id: Optional[int] = None) -> None:
        """Atualiza nome e conta vinculada do local"""
        client: Client = self.client_factory()
        
        client.table("rendimentos_locais").update({
            "nome": nome,
            "conta_vinculada_id": conta_vinculada_id,
        }).eq("id", local_id).execute()

    def get_local_by_id(self, local_id: int) -> Optional[dict]:
        """Retorna o local por id ou None."""
        client: Client = self.client_factory()
        response = client.table("rendimentos_locais") \
            .select("id, ano, nome, ordem, projecao_taxa, conta_vinculada_id") \
            .eq("id", local_id) \
            .limit(1) \
            .execute()
        return response.data[0] if response.data else None

    def update_projecao_taxa(self, local_id: int, taxa: Optional[float]) -> None:
        """Atualiza taxa de projeção do local"""
        client: Client = self.client_factory()
        
        client.table("rendimentos_locais").update({
            "projecao_taxa": taxa
        }).eq("id", local_id).execute()

    def delete_local(self, local_id: int) -> None:
        """Deleta local e lançamentos vinculados (CASCADE automático)"""
        client: Client = self.client_factory()
        
        # Deletar lançamentos (CASCADE já faz isso, mas explícito para clareza)
        client.table("rendimentos_lancamentos") \
            .delete() \
            .eq("local_id", local_id) \
            .execute()
        
        # Deletar local
        client.table("rendimentos_locais") \
            .delete() \
            .eq("id", local_id) \
            .execute()

    def delete_lancamentos_local_ano(self, ano: int, local_id: int) -> None:
        """Deleta todos os lançamentos de um local em um ano"""
        client: Client = self.client_factory()
        
        # Deletar lançamentos
        client.table("rendimentos_lancamentos") \
            .delete() \
            .eq("ano", ano) \
            .eq("local_id", local_id) \
            .execute()
        
        # Limpar taxa de projeção
        client.table("rendimentos_locais").update({
            "projecao_taxa": None
        }).eq("id", local_id).execute()

    def get_lancamentos_detalhe(self, ano: int, mes: int, local_id: int) -> list[dict]:
        """Retorna lançamentos de um local em um mês"""
        client: Client = self.client_factory()
        
        response = client.table("rendimentos_lancamentos") \
            .select("id, ano, mes, local_id, tipo, valor, nota, data_alteracao") \
            .eq("ano", ano) \
            .eq("mes", mes) \
            .eq("local_id", local_id) \
            .order("id", desc=True) \
            .execute()
        
        return response.data

    def get_lancamento_by_id(self, lancamento_id: int) -> Optional[dict]:
        """Retorna o lançamento por id ou None."""
        client: Client = self.client_factory()
        response = client.table("rendimentos_lancamentos") \
            .select("id, ano, mes, local_id, tipo, valor, nota") \
            .eq("id", lancamento_id) \
            .limit(1) \
            .execute()
        return response.data[0] if response.data else None

    def add_lancamento(self, lanc: RendimentoLancamento) -> int:
        """Adiciona lançamento de rendimento"""
        client: Client = self.client_factory()
        
        response = client.table("rendimentos_lancamentos").insert({
            "ano": lanc.ano,
            "mes": lanc.mes,
            "local_id": lanc.local_id,
            "tipo": lanc.tipo,
            "valor": lanc.valor,
            "nota": lanc.nota
        }).execute()
        
        return response.data[0]["id"]

    def update_lancamento(self, lancamento_id: int, tipo: str, valor: float, nota: str) -> None:
        """Atualiza lançamento de rendimento"""
        client: Client = self.client_factory()
        
        client.table("rendimentos_lancamentos").update({
            "tipo": tipo,
            "valor": valor,
            "nota": nota
        }).eq("id", lancamento_id).execute()

    def delete_lancamento(self, lancamento_id: int) -> None:
        """Deleta lançamento de rendimento"""
        client: Client = self.client_factory()
        
        client.table("rendimentos_lancamentos") \
            .delete() \
            .eq("id", lancamento_id) \
            .execute()

    def reorder_locais(self, ordem_ids: list[int]) -> None:
        """Reordena locais conforme lista de IDs"""
        client: Client = self.client_factory()
        
        for i, local_id in enumerate(ordem_ids):
            client.table("rendimentos_locais").update({
                "ordem": i
            }).eq("id", local_id).execute()
