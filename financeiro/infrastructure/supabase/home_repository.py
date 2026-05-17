"""
Repositório de Home - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

from financeiro.infrastructure.supabase.client import Client


class SupabaseHomeRepository:
    def __init__(self, client_factory):
        self.client_factory = client_factory

    def get_anos(self) -> set:
        """Retorna conjunto de anos com dados — fonte única: tabela `anos`."""
        client: Client = self.client_factory()
        response = client.table("anos").select("ano").order("ano", desc=True).execute()
        return {r["ano"] for r in response.data}

    def ensure_year_exists(self, ano: int) -> None:
        """Garante que o ano existe na tabela `anos` (idempotente)."""
        client: Client = self.client_factory()
        client.table("anos").upsert({"ano": ano}).execute()
