"""
conftest.py raiz — força DB_MODE=sqlite antes de QUALQUER import da aplicação.

Este arquivo é carregado pelo pytest na fase de coleta, antes dos módulos de teste.
Garante que nenhum teste toque acidentalmente no Supabase.
"""

import os
import sys


# ═══════════════════════════════════════════════════════════════════
# VERIFICAR Supabase — aborta se .env tem DB_MODE=supabase
# (protecao extra: o DB_MODE=sqlite abaixo ja deveria bastar,
#  mas esta guarda da um erro claro se algo estiver errado)
# ═══════════════════════════════════════════════════════════════════
def _recusar_supabase():
    """Aborta com erro claro se o .env esta configurado para Supabase
    e DB_MODE=sqlite nao foi definido explicitamente no ambiente."""
    # Se DB_MODE=sqlite ja esta no ambiente, confia -- o usuario sabe o que faz
    if os.environ.get("DB_MODE", "").lower() == "sqlite":
        return
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    modo_env = None
    for linha in open(env_path, encoding="utf-8"):
        linha = linha.strip()
        if linha.startswith("DB_MODE="):
            _, valor = linha.split("=", 1)
            modo_env = valor.strip().strip('"').strip("'").lower()
            break
    if modo_env == "supabase":
        RED = '\033[91m'
        RESET = '\033[0m'
        print(f"\n{RED}{'='*70}{RESET}")
        print(f"{RED}  TESTES BLOQUEADOS{RESET}")
        print(f"{RED}{'='*70}{RESET}")
        print(f"  O arquivo .env esta configurado com DB_MODE=supabase.")
        print(f"  Os testes NAO podem executar contra o Supabase.")
        print(f"  Altere o .env para DB_MODE=sqlite ou defina a variavel")
        print(f"  de ambiente DB_MODE=sqlite antes de rodar os testes.")
        print(f"{RED}{'='*70}{RESET}\n")
        sys.exit(1)

_recusar_supabase()

# ═══════════════════════════════════════════════════════════════════
# FORÇAR SQLite — executa antes de qualquer import do projeto
# ═══════════════════════════════════════════════════════════════════
os.environ["DB_MODE"] = "sqlite"
