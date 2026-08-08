"""
Fixtures globais para testes E2E com Playwright.

- flask_server (session): Sobe o servidor Flask com SQLite e banco em diretório
  temporário FORA do OneDrive (isolamento físico — ver docs/plano-infra-e2e-timeout.md).
- page (function): Abre navegador Chromium, navega para a URL base com retry.
- server_url (session): Retorna a URL base do servidor.
"""

import os
import sys
import time
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


# ═══════════════════════════════════════════════════════════════════
# VERIFICAR Supabase — aborta se Supabase estiver ativo/acessivel
# ═══════════════════════════════════════════════════════════════════
from test_browser.processos_util import kill_arvore as _kill_arvore
from test_browser.processos_util import limpar_banco_teste as _limpar_db_teste
from test_browser.processos_util import matar_servidores_na_porta as _matar_servidores_na_porta
from test_browser.verificar_ambiente import verificar as _verificar_supabase
_verificar_supabase()


# ── Constantes ─────────────────────────────────────────────────
PROJETO_RAIZ = Path(__file__).parent.parent

# Suporte a execução paralela (pytest-xdist): cada worker usa porta e banco
# próprios. Sem xdist (worker "master") o comportamento é o histórico: porta 8085.
_worker = os.environ.get("PYTEST_XDIST_WORKER", "master")
_worker_idx = 0 if _worker == "master" else int(_worker.replace("gw", "") or 0)
PORTA = 8085 + _worker_idx
BASE_URL = f"http://127.0.0.1:{PORTA}"

# Banco de teste em TEMP (fora do OneDrive) — isolamento físico: o app recebe
# SQLITE_DB_PATH via env e NUNCA toca no financeiro.db real do usuário.
# Cada worker tem diretório próprio para não limpar o banco dos demais.
TMP_E2E = Path(tempfile.gettempdir()) / ("controle_financeiro_e2e" if _worker_idx == 0 else f"controle_financeiro_e2e_{_worker}")
DB_TESTE = TMP_E2E / "financeiro.db"

# Diagnóstico do goto da fixture (critério de aceite: tempo registrado em log)
LOG_GOTO = PROJETO_RAIZ / "test_browser" / "artefatos" / "e2e-goto.log"
GOTO_TIMEOUT_MS = 60_000
GOTO_TENTATIVAS = 2


def _log_goto(msg: str):
    """Registra tempo/evento do goto em arquivo de log (persiste mesmo sem -s)."""
    try:
        LOG_GOTO.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_GOTO, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")
    except OSError:
        pass


def _salvar_diagnostico(page_obj, url: str):
    """Salva screenshot + HTML truncado quando o load da página estoura o timeout."""
    artefatos = LOG_GOTO.parent
    artefatos.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    try:
        page_obj.screenshot(path=str(artefatos / f"timeout-{ts}.png"), full_page=True)
    except Exception:
        pass
    try:
        content = page_obj.content()
        (artefatos / f"timeout-{ts}.html").write_text(content[:200_000], encoding="utf-8")
    except Exception:
        pass
    _log_goto(f"DIAGNOSTICO salvo em test_browser/artefatos/timeout-{ts}.{{png,html}} (url={url})")


@pytest.fixture(scope="session")
def server_url():
    """Retorna a URL base do servidor."""
    return BASE_URL


@pytest.fixture(scope="session")
def flask_server():
    """Sobe o servidor Flask em background com SQLite e banco em TEMP (fora do OneDrive)."""
    _matar_servidores_na_porta(PORTA)
    _limpar_db_teste(DB_TESTE)
    TMP_E2E.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["DB_MODE"] = "sqlite"
    env["PORT"] = str(PORTA)
    env["SQLITE_DB_PATH"] = str(DB_TESTE)
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
            _limpar_db_teste(DB_TESTE)
            raise RuntimeError("Servidor morreu ao iniciar (processo encerrado)")

        try:
            import urllib.request

            urllib.request.urlopen(BASE_URL, timeout=2)
            ready = True
            break
        except Exception:
            time.sleep(0.25)

    if not ready:
        _kill_arvore(proc)
        _limpar_db_teste(DB_TESTE)
        raise RuntimeError(f"Servidor nao iniciou em {timeout}s")

    yield BASE_URL

    # Teardown
    _kill_arvore(proc)
    _limpar_db_teste(DB_TESTE)
    try:
        TMP_E2E.rmdir()
    except OSError:
        pass


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


def _abrir_pagina_com_retry(page_obj, url: str):
    """Abre a página com retry e registra o tempo do goto em log.

    Mitiga lentidão de primeiro load (OneDrive/antivírus) sem mudar a semântica
    dos testes: apenas o setup da fixture ganha robustez. Em falha final, salva
    screenshot + HTML para diagnóstico.
    """
    for tentativa in range(1, GOTO_TENTATIVAS + 1):
        inicio = time.monotonic()
        try:
            page_obj.goto(url, timeout=GOTO_TIMEOUT_MS, wait_until="load")
            page_obj.wait_for_function(
                "() => window.CF_BOOT && "
                "(document.querySelector('#tw table') || document.querySelector('.view-tab'))",
                timeout=GOTO_TIMEOUT_MS,
            )
            duracao = time.monotonic() - inicio
            _log_goto(f"goto OK ({duracao:.1f}s, tentativa {tentativa}) {url}")
            print(f"[e2e] goto OK ({duracao:.1f}s, tentativa {tentativa}) {url}")
            page_obj.wait_for_timeout(100)
            return
        except Exception as exc:
            duracao = time.monotonic() - inicio
            _log_goto(f"goto FALHOU ({duracao:.1f}s, tentativa {tentativa}) {url} -> {type(exc).__name__}")
            print(f"[e2e] goto FALHOU ({duracao:.1f}s, tentativa {tentativa}) {url} -> {type(exc).__name__}")
            if tentativa == GOTO_TENTATIVAS:
                _salvar_diagnostico(page_obj, url)
                raise
            page_obj.wait_for_timeout(1500)


@pytest.fixture(scope="function")
def page(context, flask_server):
    """Nova aba no navegador compartilhado, com contexto limpo a cada teste.

    Navega para ANO_TESTE (ano atual + 10) para isolar dos dados reais.
    """
    from test_browser.helpers import ANO_TESTE

    page_obj = context.new_page()
    page_obj.add_init_script("sessionStorage.removeItem('cfViewAtiva');")
    _abrir_pagina_com_retry(page_obj, f"{flask_server}/?ano={ANO_TESTE}")

    yield page_obj

    page_obj.close()


# ═══════════════════════════════════════════════════════════════════
# PROGRESSO NO TÍTULO DO CONSOLE
# ═══════════════════════════════════════════════════════════════════
_total_testes = 0
_testes_concluidos = 0


def pytest_collection_modifyitems(session, config, items):
    global _total_testes
    _total_testes = len(items)


def pytest_runtest_logreport(report):
    global _testes_concluidos
    if report.when == "call" or (report.when == "setup" and report.skipped):
        _testes_concluidos += 1
        if _total_testes > 0:
            pct = int((_testes_concluidos / _total_testes) * 100)
            sys.stdout.write(f"\x1b]0;Controle Financeiro E2E: {pct}% ({_testes_concluidos}/{_total_testes})\x07")
            sys.stdout.flush()
