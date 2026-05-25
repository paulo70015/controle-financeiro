"""
Fixtures globais para testes E2E com Playwright.

- flask_server (session): Sobe o servidor Flask com SQLite temporário.
- page (function): Abre navegador Chromium, navega para a URL base.
- server_url (session): Retorna a URL base do servidor.
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


# ═══════════════════════════════════════════════════════════════════
# FORÇAR SQLite — testes NUNCA usam Supabase
# O DB_MODE é hardcoded aqui. O app.py respeita a env var:
#   _db_mode_before_dotenv é restaurado após load_dotenv (override=True)
# ═══════════════════════════════════════════════════════════════════
os.environ["DB_MODE"] = "sqlite"


# ── Constantes ─────────────────────────────────────────────────
PROJETO_RAIZ = Path(__file__).parent.parent
DB_REAL = PROJETO_RAIZ / "financeiro.db"
DB_BACKUP = PROJETO_RAIZ / "financeiro.db.bak_tests"
DB_TESTE = PROJETO_RAIZ / "test_financeiro.db"
DB_WAL = PROJETO_RAIZ / "financeiro.db-wal"
DB_SHM = PROJETO_RAIZ / "financeiro.db-shm"
PORTA = 8080
BASE_URL = f"http://127.0.0.1:{PORTA}"


def _safe_action(action, *args, **kwargs):
    """Executa uma ação de arquivo com retentativas caso ocorra PermissionError (comum no Windows)."""
    for idx in range(30):
        try:
            return action(*args, **kwargs)
        except PermissionError:
            if idx == 29:
                raise
            time.sleep(0.1)


def _limpar_wal_shm(db_path: Path):
    """Remove arquivos WAL/SHM associados a um banco SQLite."""
    for suffix in ("-wal", "-shm"):
        aux = Path(str(db_path) + suffix)
        if aux.exists():
            _safe_action(aux.unlink)


def _backup_db():
    """Renomeia o DB real para backup (NUNCA mexe no .env)."""
    # Remove DB de teste residual de execucoes anteriores
    if DB_TESTE.exists():
        _safe_action(DB_TESTE.unlink)
        _limpar_wal_shm(DB_TESTE)

    # Se ja existe backup do DB, restaura primeiro (caso de crash anterior)
    if DB_BACKUP.exists():
        _limpar_wal_shm(DB_REAL)
        if DB_REAL.exists():
            _safe_action(DB_REAL.unlink)
        _safe_action(shutil.move, str(DB_BACKUP), str(DB_REAL))

    # Agora faz backup do DB real
    if DB_REAL.exists():
        _limpar_wal_shm(DB_REAL)
        _safe_action(shutil.move, str(DB_REAL), str(DB_BACKUP))


def _restore_db():
    """Restaura o DB real e limpa arquivos de teste (NUNCA mexe no .env)."""
    # Remove o DB de teste criado pelo servidor
    _limpar_wal_shm(DB_REAL)
    if DB_REAL.exists():
        _safe_action(DB_REAL.unlink)

    # Restaura backup do DB
    if DB_BACKUP.exists():
        _safe_action(shutil.move, str(DB_BACKUP), str(DB_REAL))

    # Limpa DB de teste se existir
    if DB_TESTE.exists():
        _limpar_wal_shm(DB_TESTE)
        _safe_action(DB_TESTE.unlink)


@pytest.fixture(scope="session")
def server_url():
    """Retorna a URL base do servidor."""
    return BASE_URL


@pytest.fixture(scope="session")
def flask_server():
    """Sobe o servidor Flask em background com SQLite e banco temporario."""
    _backup_db()

    env = os.environ.copy()
    env["DB_MODE"] = "sqlite"
    env["PYTHONPATH"] = str(PROJETO_RAIZ)

    # FLASK_SKIP_BROWSER evita que o app.py abra o navegador padrão
    env["FLASK_SKIP_BROWSER"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        env=env,
        cwd=str(PROJETO_RAIZ),
    )

    # Aguardar servidor ficar pronto
    timeout = 15
    ready = False
    for _ in range(timeout * 4):
        if proc.poll() is not None:
            _restore_db()
            raise RuntimeError("Servidor morreu ao iniciar (processo encerrado)")

        try:
            import urllib.request

            urllib.request.urlopen(BASE_URL, timeout=2)
            ready = True
            break
        except Exception:
            time.sleep(0.25)

    if not ready:
        proc.kill()
        _restore_db()
        raise RuntimeError(f"Servidor nao iniciou em {timeout}s")

    yield BASE_URL

    # Teardown
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    _restore_db()


@pytest.fixture(scope="session")
def playwright_instance():
    """Instância do Playwright (uma por sessão)."""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance, flask_server):
    """Navegador Chromium headless (compartilhado por todos os testes)."""
    brw = playwright_instance.chromium.launch(headless=True)
    yield brw
    brw.close()


@pytest.fixture(scope="function")
def context(browser):
    """Contexto isolado por teste (cookies/localStorage separados)."""
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 900},
        locale="pt-BR",
    )
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def page(context, flask_server):
    """Nova aba no navegador compartilhado, com contexto limpo a cada teste."""
    page_obj = context.new_page()
    page_obj.goto(flask_server)

    # Aguardar a SPA carregar completamente
    page_obj.wait_for_function(
        "() => window.CF_BOOT && "
        "(document.querySelector('#tw table') || document.querySelector('.view-tab'))"
    )
    page_obj.wait_for_timeout(100)

    yield page_obj

    page_obj.close()
