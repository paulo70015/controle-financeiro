"""
Verificação de ambiente anti-Supabase para testes.

Garante que nenhum teste rode contra o Supabase real, verificando:
1. Se o .env tem DB_MODE=supabase e DB_MODE=sqlite não foi forçado no ambiente
2. Se já existe um servidor Flask rodando na porta 8080 em modo Supabase
3. Se o cliente Supabase está ativo e acessível

Uso como script standalone:
    python test_browser/verificar_ambiente.py
    → exit 0 = seguro prosseguir, exit 1 = bloqueado

Uso como módulo:
    from test_browser.verificar_ambiente import verificar
    verificar()  # levanta SystemExit(1) se bloqueado
"""

import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


PROJETO_RAIZ = Path(__file__).parent.parent
PORTA = 8085
BASE_URL = f"http://127.0.0.1:{PORTA}"

RED = "\033[91m"
RESET = "\033[0m"


def _ler_env_db_mode() -> str:
    """Le o DB_MODE do arquivo .env, retorna string vazia se nao encontrar."""
    env_path = PROJETO_RAIZ / ".env"
    if not env_path.exists():
        return ""
    for linha in env_path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha.startswith("DB_MODE="):
            _, valor = linha.split("=", 1)
            return valor.strip().strip('"').strip("'").lower()
    return ""


def _servidor_rodando_supabase() -> bool:
    """Verifica se ha um servidor rodando na porta 8080 em modo Supabase."""
    try:
        req = urllib.request.Request(BASE_URL)
        with urllib.request.urlopen(req, timeout=3) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            # Procura por db_mode: "supabase" no JS bootstrap
            import re
            if re.search(r'db_mode["\']?\s*:\s*["\'][^"\']*supabase[^"\']*["\']', html):
                return True
    except (urllib.error.URLError, OSError, ConnectionRefusedError, TimeoutError):
        pass
    return False


def _supabase_cliente_ativo() -> bool:
    """Tenta conectar ao Supabase com as credenciais do ambiente.
    Retorna True se a conexao for bem-sucedida (Supabase ativo e acessivel)."""
    try:
        from financeiro.infrastructure.supabase.client import get_supabase
        client = get_supabase()
        # Tenta uma consulta simples para confirmar conectividade
        result = client.table("config").select("*").limit(1).execute()
        return hasattr(result, "data") and result.data is not None
    except Exception:
        return False


def _bloquear(motivo: str) -> None:
    """Exibe mensagem de bloqueio e encerra."""
    print(f"\n{RED}{'='*70}{RESET}")
    print(f"{RED}  TESTES BLOQUEADOS{RESET}")
    print(f"{RED}{'='*70}{RESET}")
    for linha in motivo.strip().split("\n"):
        print(f"  {linha}")
    print(f"{RED}{'='*70}{RESET}\n")
    sys.exit(1)


def verificar() -> None:
    """
    Verifica se o ambiente esta seguro para testes.
    Levanta SystemExit(1) se detectar Supabase ativo.

    Ordem das verificacoes:
    1. Servidor Supabase rodando na porta 8080 (incondicional — mais critico)
    2. DB_MODE=sqlite forcado no ambiente (confia)
    3. .env configurado com DB_MODE=supabase
    4. Cliente Supabase ativo e respondendo
    """
    # ── 1. Servidor Flask rodando em modo Supabase na porta 8080? ──
    #     INCONDICIONAL: mesmo com DB_MODE=sqlite no ambiente, se ha um
    #     servidor Supabase na 8080 os testes rodariam contra ele.
    if _servidor_rodando_supabase():
        _bloquear(
            "Aplicacao rodando em modo SUPABASE na porta 8080.\n"
            "Pare a aplicacao antes de rodar os testes:\n"
            "  - Feche o navegador ou terminal onde ela esta rodando\n"
            "  - Ou encerre o processo na porta 8080"
        )

    # ── 2. DB_MODE=sqlite forcado no ambiente? Confia e segue ──
    if os.environ.get("DB_MODE", "").lower() == "sqlite":
        return

    # ── 3. .env configurado com DB_MODE=supabase? ──
    env_db_mode = _ler_env_db_mode()
    if env_db_mode == "supabase":
        _bloquear(
            "O arquivo .env esta configurado com DB_MODE=supabase.\n"
            "Os testes NAO podem executar contra o Supabase.\n"
            "Altere o .env para DB_MODE=sqlite ou defina a variavel\n"
            "de ambiente DB_MODE=sqlite antes de rodar os testes:\n"
            "  set DB_MODE=sqlite && python test_suite.py   (Windows)\n"
            "  DB_MODE=sqlite python test_suite.py           (Linux/Mac)"
        )

    # ── 4. Cliente Supabase ativo e respondendo? ──
    # (verificacao extra: mesmo sem .env, variaveis de ambiente podem ter credenciais)
    if _supabase_cliente_ativo():
        _bloquear(
            "Cliente Supabase ativo e respondendo!\n"
            "Os testes NAO podem executar contra o Supabase real.\n"
            "Defina DB_MODE=sqlite no ambiente ou verifique se ha\n"
            "variaveis SUPABASE_URL / SUPABASE_KEY definidas."
        )


if __name__ == "__main__":
    verificar()
    print("OK: Ambiente seguro para testes (SQLite).")
