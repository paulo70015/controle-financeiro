"""
Helper de paths para runtime - Suporta modo dev e PyInstaller
"""

import os
import sys


def get_base_dir() -> str:
    """
    Retorna o diretório base da aplicação.
    - PyInstaller: sys._MEIPASS (arquivos embutidos temporários)
    - Dev: diretório raiz do projeto
    """
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def get_data_dir() -> str:
    """
    Retorna o diretório de dados persistentes.
    - PyInstaller: pasta onde o .exe está rodando
    - Dev: diretório raiz do projeto
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def get_db_path() -> str:
    """
    Retorna o caminho do banco SQLite.

    Respeita a variável de ambiente SQLITE_DB_PATH (usada pelos testes E2E para
    isolar o banco em um diretório temporário fora do OneDrive). Sem a variável,
    o comportamento é o padrão: <get_data_dir()>/financeiro.db.
    """
    override = os.environ.get("SQLITE_DB_PATH")
    if override:
        return os.path.abspath(override)
    return os.path.join(get_data_dir(), "financeiro.db")


def get_db_backup_path() -> str:
    """Caminho do backup temporário do banco (import CSV / restore de DB)."""
    return get_db_path() + ".bak"
