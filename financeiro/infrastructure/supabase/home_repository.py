"""
Repositório de Home - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

from financeiro.infrastructure.supabase.client import Client


class SupabaseHomeRepository:
    def __init__(self, client_factory):
        self.client_factory = client_factory

    def get_anos(self) -> set:
        """Retorna conjunto de anos registrados na tabela `anos` (fonte da verdade)."""
        client: Client = self.client_factory()
        resp = client.table("anos").select("ano").execute()
        return {int(r["ano"]) for r in (resp.data or []) if r.get("ano") is not None}

    def ensure_year_exists(self, ano: int) -> None:
        """Garante que o ano existe na tabela `anos` (idempotente)."""
        client: Client = self.client_factory()
        client.table("anos").upsert({"ano": ano}).execute()
