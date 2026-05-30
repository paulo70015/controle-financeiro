"""
Teste do status persistido de meses realizados na visão de rendimentos.
"""

import datetime
import sqlite3
from pathlib import Path

from postgrest.exceptions import APIError

from test_browser.verificar_ambiente import verificar as _verificar_supabase

from financeiro.infrastructure.sqlite.dashboard_repository import SQLiteDashboardRepository
from financeiro.infrastructure.sqlite.schema import init_db
from financeiro.infrastructure.supabase.dashboard_repository import SupabaseDashboardRepository

_verificar_supabase()


def _build_connection_factory(db_path: Path):
    def _connection_factory(**kwargs):
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    return _connection_factory


def test_dashboard_sincroniza_rendimentos_realizados(tmp_path):
    db_path = tmp_path / "rendimentos-realizados.db"
    connection_factory = _build_connection_factory(db_path)
    init_db(connection_factory)

    repo = SQLiteDashboardRepository(connection_factory, [])
    hoje = datetime.datetime.now()

    dados_ano_passado = repo.get_dados_ano(hoje.year - 1)
    assert dados_ano_passado["rendimentos_realizados"] == {mes: 1 for mes in range(1, 13)}

    dados_ano_atual = repo.get_dados_ano(hoje.year)
    assert dados_ano_atual["rendimentos_realizados"] == {mes: 1 for mes in range(1, hoje.month)}

    dados_ano_futuro = repo.get_dados_ano(hoje.year + 1)
    assert dados_ano_futuro["rendimentos_realizados"] == {}

    conn = connection_factory()
    try:
        rows = conn.execute(
            "SELECT ano, mes, status FROM rendimentos_realizados ORDER BY ano, mes"
        ).fetchall()
    finally:
        conn.close()

    esperado = (
        [(hoje.year - 1, mes, 1) for mes in range(1, 13)]
        + [(hoje.year, mes, 1) for mes in range(1, hoje.month)]
    )
    assert [(row["ano"], row["mes"], row["status"]) for row in rows] == esperado


class _QueryRlsNegado:
    def upsert(self, *args, **kwargs):
        return self

    def execute(self):
        raise APIError({
            "message": "new row violates row-level security policy",
            "code": "42501",
            "hint": None,
            "details": None,
        })


class _ClientRlsNegado:
    def table(self, table_name):
        return _QueryRlsNegado()


def test_dashboard_supabase_usa_calendario_em_memoria_quando_rls_bloqueia_sync():
    repo = SupabaseDashboardRepository(lambda: _ClientRlsNegado(), [])
    ano_passado = datetime.datetime.now().year - 1

    assert repo._sync_rendimentos_realizados(_ClientRlsNegado(), ano_passado) is False
    assert repo._rendimentos_realizados_calendario(ano_passado) == {
        mes: 1 for mes in range(1, 13)
    }
