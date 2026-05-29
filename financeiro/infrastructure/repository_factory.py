"""
Factory de Repositórios - Suporta Supabase e SQLite
Detecta o modo baseado em variável de ambiente DB_MODE
"""

import os
import sqlite3
from pathlib import Path


# Constante de meses (usada por alguns repositórios)
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _load_local_env_if_needed():
    """Carrega variaveis simples do .env sem depender de python-dotenv."""
    if os.getenv("DB_MODE"):
        return

    from financeiro.infrastructure.runtime.paths import get_data_dir

    env_path = Path(get_data_dir()) / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_db_mode() -> str:
    """Retorna 'sqlite' ou 'supabase'. SQLite e o modo padrao local."""
    _load_local_env_if_needed()
    return os.getenv("DB_MODE", "sqlite").lower()


def _get_sqlite_connection(**kwargs):
    """Factory de conexão SQLite"""
    from financeiro.infrastructure.runtime.paths import get_data_dir
    
    db_path = Path(get_data_dir()) / "financeiro.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 5000')
    return conn


def _get_supabase_client():
    """Factory de cliente Supabase"""
    from financeiro.infrastructure.supabase.client import get_supabase
    return get_supabase()


def _ensure_sqlite_initialized():
    """Garante que o banco SQLite existe e está migrado"""
    from financeiro.infrastructure.sqlite.schema import init_db
    init_db(_get_sqlite_connection)


# ============================================
# Factories de Repositórios
# ============================================

def get_despesas_repository():
    mode = get_db_mode()
    
    if mode == 'sqlite':
        _ensure_sqlite_initialized()
        from financeiro.infrastructure.sqlite.despesas_repository import SQLiteDespesasRepository
        return SQLiteDespesasRepository(_get_sqlite_connection)
    else:
        from financeiro.infrastructure.supabase.despesas_repository import SupabaseDespesasRepository
        return SupabaseDespesasRepository(_get_supabase_client)


def get_receitas_repository():
    mode = get_db_mode()
    
    if mode == 'sqlite':
        _ensure_sqlite_initialized()
        from financeiro.infrastructure.sqlite.receitas_repository import SQLiteReceitasRepository
        return SQLiteReceitasRepository(_get_sqlite_connection)
    else:
        from financeiro.infrastructure.supabase.receitas_repository import SupabaseReceitasRepository
        return SupabaseReceitasRepository(_get_supabase_client)


def get_categorias_repository():
    mode = get_db_mode()
    
    if mode == 'sqlite':
        _ensure_sqlite_initialized()
        from financeiro.infrastructure.sqlite.categorias_repository import SQLiteCategoriasRepository
        return SQLiteCategoriasRepository(_get_sqlite_connection)
    else:
        from financeiro.infrastructure.supabase.categorias_repository import SupabaseCategoriasRepository
        return SupabaseCategoriasRepository(_get_supabase_client)


def get_contas_repository():
    mode = get_db_mode()
    
    if mode == 'sqlite':
        _ensure_sqlite_initialized()
        from financeiro.infrastructure.sqlite.contas_repository import SQLiteContasRepository
        return SQLiteContasRepository(_get_sqlite_connection)
    else:
        from financeiro.infrastructure.supabase.contas_repository import SupabaseContasRepository
        return SupabaseContasRepository(_get_supabase_client)


def get_planejamento_repository():
    mode = get_db_mode()
    
    if mode == 'sqlite':
        _ensure_sqlite_initialized()
        from financeiro.infrastructure.sqlite.planejamento_repository import SQLitePlanejamentoRepository
        return SQLitePlanejamentoRepository(_get_sqlite_connection)
    else:
        from financeiro.infrastructure.supabase.planejamento_repository import SupabasePlanejamentoRepository
        return SupabasePlanejamentoRepository(_get_supabase_client)


def get_rendimentos_repository():
    mode = get_db_mode()
    
    if mode == 'sqlite':
        _ensure_sqlite_initialized()
        from financeiro.infrastructure.sqlite.rendimentos_repository import SQLiteRendimentosRepository
        return SQLiteRendimentosRepository(_get_sqlite_connection)
    else:
        from financeiro.infrastructure.supabase.rendimentos_repository import SupabaseRendimentosRepository
        return SupabaseRendimentosRepository(_get_supabase_client)


def get_dashboard_repository():
    mode = get_db_mode()
    
    if mode == 'sqlite':
        _ensure_sqlite_initialized()
        from financeiro.infrastructure.sqlite.dashboard_repository import SQLiteDashboardRepository
        return SQLiteDashboardRepository(_get_sqlite_connection, MESES)
    else:
        from financeiro.infrastructure.supabase.dashboard_repository import SupabaseDashboardRepository
        return SupabaseDashboardRepository(_get_supabase_client, MESES)


def get_admin_repository():
    mode = get_db_mode()
    
    if mode == 'sqlite':
        _ensure_sqlite_initialized()
        from financeiro.infrastructure.sqlite.admin_repository import SQLiteAdminRepository
        return SQLiteAdminRepository(_get_sqlite_connection)
    else:
        from financeiro.infrastructure.supabase.admin_repository import SupabaseAdminRepository
        return SupabaseAdminRepository(_get_supabase_client)


def get_home_repository():
    mode = get_db_mode()
    
    if mode == 'sqlite':
        _ensure_sqlite_initialized()
        from financeiro.infrastructure.sqlite.home_repository import SQLiteHomeRepository
        return SQLiteHomeRepository(_get_sqlite_connection)
    else:
        from financeiro.infrastructure.supabase.home_repository import SupabaseHomeRepository
        return SupabaseHomeRepository(_get_supabase_client)


def get_csv_repository():
    mode = get_db_mode()
    
    if mode == 'sqlite':
        _ensure_sqlite_initialized()
        from financeiro.infrastructure.sqlite.csv_repository import SQLiteCSVRepository
        return SQLiteCSVRepository(_get_sqlite_connection, MESES)
    else:
        from financeiro.infrastructure.supabase.csv_repository import SupabaseCSVRepository
        return SupabaseCSVRepository(_get_supabase_client, MESES)


def get_db_backup_repository():
    mode = get_db_mode()

    if mode == 'sqlite':
        _ensure_sqlite_initialized()
        from financeiro.infrastructure.sqlite.db_backup_repository import SQLiteDBBackupRepository
        return SQLiteDBBackupRepository(_get_sqlite_connection)
    else:
        from financeiro.infrastructure.supabase.db_backup_repository import SupabaseDBBackupRepository
        return SupabaseDBBackupRepository(_get_supabase_client)
