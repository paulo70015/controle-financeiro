"""
Repositório de Home - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

from financeiro.infrastructure.supabase.client import Client


class SupabaseHomeRepository:
    def __init__(self, client_factory):
        self.client_factory = client_factory

    def get_anos(self) -> set:
        """Retorna conjunto de anos com dados"""
        client: Client = self.client_factory()
        
        anos = set()
        
        # Anos de despesas
        desp_response = client.table("despesas").select("ano").execute()
        anos.update(r["ano"] for r in desp_response.data)
        
        # Anos de receitas
        rec_response = client.table("receitas").select("ano").execute()
        anos.update(r["ano"] for r in rec_response.data)
        
        # Anos de categorias
        cat_response = client.table("categorias").select("ano").execute()
        anos.update(r["ano"] for r in cat_response.data)
        
        return anos
