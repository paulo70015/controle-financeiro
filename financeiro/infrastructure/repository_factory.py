"""
Factory de Repositórios - Suporta Supabase e SQLite
Detecta o modo baseado em variável de ambiente DB_MODE
"""

import importlib
import os
import sqlite3
import threading
from pathlib import Path

from financeiro.infrastructure.constantes import MESES

# Flag para evitar múltiplas inicializações do SQLite por processo
_sqlite_initialized = False
_sqlite_init_lock = threading.Lock()


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
    from financeiro.infrastructure.runtime.paths import get_db_path

    db_path = Path(get_db_path())
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
    """Garante que o banco SQLite existe e está migrado (executa apenas uma vez)."""
    global _sqlite_initialized
    if _sqlite_initialized:
        return
    with _sqlite_init_lock:
        if _sqlite_initialized:
            return
        from financeiro.infrastructure.sqlite.schema import init_db
        init_db(_get_sqlite_connection)
        _sqlite_initialized = True


# ============================================
# Factories de Repositórios
# ============================================

# Nome da classe -> módulo onde ela vive (convenção SQLite/Supabase<nome>Repository)
_MODULO_REPOSITORIO = {
    "Admin": "admin_repository",
    "Categorias": "categorias_repository",
    "Contas": "contas_repository",
    "CSV": "csv_repository",
    "Dashboard": "dashboard_repository",
    "DBBackup": "db_backup_repository",
    "Despesas": "despesas_repository",
    "Home": "home_repository",
    "Planejamento": "planejamento_repository",
    "Receitas": "receitas_repository",
    "Rendimentos": "rendimentos_repository",
}


def _get_repository(classe_nome: str, *args):
    """Instancia o repositório do modo ativo (sqlite/supabase) por convenção de nomes."""
    modo = get_db_mode()
    prefixo = "SQLite" if modo == "sqlite" else "Supabase"
    if modo == "sqlite":
        _ensure_sqlite_initialized()
        factory = _get_sqlite_connection
    else:
        factory = _get_supabase_client
    modulo = importlib.import_module(
        f"financeiro.infrastructure.{modo}.{_MODULO_REPOSITORIO[classe_nome]}"
    )
    return getattr(modulo, f"{prefixo}{classe_nome}Repository")(factory, *args)


def get_despesas_repository():
    return _get_repository("Despesas")


def get_receitas_repository():
    return _get_repository("Receitas")


def get_categorias_repository():
    return _get_repository("Categorias")


def get_contas_repository():
    return _get_repository("Contas")


def get_planejamento_repository():
    return _get_repository("Planejamento")


def get_rendimentos_repository():
    return _get_repository("Rendimentos")


def get_dashboard_repository():
    return _get_repository("Dashboard", MESES)


def get_admin_repository():
    return _get_repository("Admin")


def get_home_repository():
    return _get_repository("Home")


def get_csv_repository():
    return _get_repository("CSV", MESES)


def get_db_backup_repository():
    return _get_repository("DBBackup")
