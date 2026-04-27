"""
Repositório de Receitas - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

from financeiro.infrastructure.supabase.client import Client
from financeiro.domain.receitas.entities import Receita, ReceitaLote


class SupabaseReceitasRepository:
    def __init__(self, client_factory):
        self.client_factory = client_factory

    def add_receita(self, receita: Receita) -> int:
        """Adiciona receita e retorna o ID"""
        client: Client = self.client_factory()
        
        response = client.table("receitas").insert({
            "ano": receita.ano,
            "mes": receita.mes,
            "descricao": receita.descricao,
            "valor": receita.valor,
            "nota": receita.nota
        }).execute()
        
        return response.data[0]["id"]

    def get_receitas_mes(self, ano: int, mes: int) -> list[dict]:
        """Retorna todas as receitas de um mês"""
        client: Client = self.client_factory()
        
        response = client.table("receitas") \
            .select("*") \
            .eq("ano", ano) \
            .eq("mes", mes) \
            .execute()
        
        return response.data

    def update_receita(self, receita_id: int, valor: float, nota: str, descricao: str, mes: int | None = None) -> None:
        """Atualiza receita"""
        client: Client = self.client_factory()

        payload = {
            "valor": valor,
            "nota": nota,
            "descricao": descricao
        }
        if mes is not None:
            payload["mes"] = mes

        client.table("receitas").update(payload).eq("id", receita_id).execute()

    def delete_receita(self, receita_id: int) -> None:
        """Deleta receita"""
        client: Client = self.client_factory()
        
        client.table("receitas") \
            .delete() \
            .eq("id", receita_id) \
            .execute()

    def add_receita_lote(self, lote: ReceitaLote, meses: list[int]) -> None:
        """Adiciona lote de receitas com incremento sucessivo"""
        client: Client = self.client_factory()
        
        receitas_insert = []
        for i, mes in enumerate(meses):
            valor = round(lote.valor_base + (lote.acrescimo * i), 2)
            receitas_insert.append({
                "ano": lote.ano,
                "mes": mes,
                "descricao": lote.descricao,
                "valor": valor,
                "nota": lote.nota
            })
        
        client.table("receitas").insert(receitas_insert).execute()

    def delete_receitas_ano(self, ano: int) -> None:
        """Deleta todas as receitas de um ano"""
        client: Client = self.client_factory()
        
        client.table("receitas") \
            .delete() \
            .eq("ano", ano) \
            .execute()
