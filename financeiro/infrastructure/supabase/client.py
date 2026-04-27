"""
Cliente Singleton Supabase Data API
Usa PostgREST diretamente para compatibilidade com novas chaves sb_publishable_
"""

import os

from dotenv import load_dotenv
from postgrest import SyncPostgrestClient


load_dotenv()


class Client:
    """Adapter compativel com o uso atual de .table()."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.rest_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self.postgrest = SyncPostgrestClient(
            self.rest_url,
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
            },
        )

    def table(self, table_name: str):
        """Retorna cliente da tabela."""
        return self.postgrest.from_(table_name)


class SupabaseClient:
    """Singleton para gerenciar conexao com a Data API do Supabase."""

    _instance: Client = None
    _initialized = False

    @classmethod
    def get_client(cls) -> Client:
        if not cls._initialized:
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls) -> None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise ValueError(
                "SUPABASE_URL e SUPABASE_KEY devem estar definidos no .env ou variaveis de ambiente"
            )

        cls._instance = Client(url, key)
        cls._initialized = True

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        cls._initialized = False


def get_supabase() -> Client:
    """Factory function para obter cliente Supabase."""
    return SupabaseClient.get_client()
