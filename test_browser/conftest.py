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


# ── Constantes ─────────────────────────────────────────────────
PROJETO_RAIZ = Path(__file__).parent.parent
DB_REAL = PROJETO_RAIZ / "financeiro.db"
DB_BACKUP = PROJETO_RAIZ / "financeiro.db.bak_tests"
DB_TESTE = PROJETO_RAIZ / "test_financeiro.db"
DB_WAL = PROJETO_RAIZ / "financeiro.db-wal"
DB_SHM = PROJETO_RAIZ / "financeiro.db-shm"
ENV_REAL = PROJETO_RAIZ / ".env"
ENV_BACKUP = PROJETO_RAIZ / ".env.bak_tests"
ENV_TESTE = PROJETO_RAIZ / ".env.sqlite"
PORTA = 8080
BASE_URL = f"http://127.0.0.1:{PORTA}"


def _limpar_wal_shm(db_path: Path):
    """Remove arquivos WAL/SHM associados a um banco SQLite."""
    for suffix in ("-wal", "-shm"):
        aux = Path(str(db_path) + suffix)
        if aux.exists():
            aux.unlink()


def _backup_db():
    """Renomeia o DB real e .env para backup, configura ambiente SQLite."""
    # Remove DB de teste residual de execucoes anteriores
    if DB_TESTE.exists():
        DB_TESTE.unlink()
        _limpar_wal_shm(DB_TESTE)

    # Se ja existe backup do .env, restaura primeiro (caso de crash anterior)
    if ENV_BACKUP.exists():
        if ENV_REAL.exists():
            ENV_REAL.unlink()
        shutil.move(str(ENV_BACKUP), str(ENV_REAL))

    # Backup do .env real
    if ENV_REAL.exists():
        shutil.copy2(str(ENV_REAL), str(ENV_BACKUP))

    # Cria .env de teste com SQLite
    ENV_TESTE.write_text("DB_MODE=sqlite\n", encoding="utf-8")
    if ENV_REAL.exists():
        ENV_REAL.unlink()
    shutil.copy2(str(ENV_TESTE), str(ENV_REAL))

    # Se ja existe backup do DB, restaura primeiro (caso de crash anterior)
    if DB_BACKUP.exists():
        _limpar_wal_shm(DB_REAL)
        if DB_REAL.exists():
            DB_REAL.unlink()
        shutil.move(str(DB_BACKUP), str(DB_REAL))

    # Agora faz backup do DB real
    if DB_REAL.exists():
        _limpar_wal_shm(DB_REAL)
        shutil.move(str(DB_REAL), str(DB_BACKUP))


def _restore_db():
    """Restaura o DB real e .env, limpa arquivos de teste."""
    # Remove o DB de teste criado pelo servidor
    _limpar_wal_shm(DB_REAL)
    if DB_REAL.exists():
        DB_REAL.unlink()

    # Restaura backup do DB
    if DB_BACKUP.exists():
        shutil.move(str(DB_BACKUP), str(DB_REAL))

    # Limpa DB de teste se existir
    if DB_TESTE.exists():
        _limpar_wal_shm(DB_TESTE)
        DB_TESTE.unlink()

    # Restaura .env original
    if ENV_REAL.exists():
        ENV_REAL.unlink()
    if ENV_BACKUP.exists():
        shutil.move(str(ENV_BACKUP), str(ENV_REAL))

    # Limpa .env de teste
    if ENV_TESTE.exists():
        ENV_TESTE.unlink()


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

    # Sem --show-console: o servidor usa loop infinito (tray falha -> while True)
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


@pytest.fixture(scope="function")
def page(flask_server):
    """Abre navegador Chromium e retorna uma Page pronta para teste."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="pt-BR",
        )
        page_obj = context.new_page()
        page_obj.goto(flask_server)

        # Aguardar a SPA carregar completamente
        page_obj.wait_for_function(
            "() => window.CF_BOOT && "
            "(document.querySelector('#tw table') || document.querySelector('.view-tab'))"
        )
        page_obj.wait_for_timeout(100)

        yield page_obj

        context.close()
        browser.close()
