"""
Teste de integridade do modo SQLite
Valida que todos os repositórios podem ser instanciados
"""

import os
import sys
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# VERIFICAR Supabase — aborta se .env tem DB_MODE=supabase
# ═══════════════════════════════════════════════════════════════════
def _recusar_supabase():
    """Aborta com erro claro se o .env esta configurado para Supabase
    e DB_MODE=sqlite nao foi definido explicitamente no ambiente."""
    # Se DB_MODE=sqlite ja esta no ambiente, confia -- o usuario sabe o que faz
    if os.environ.get("DB_MODE", "").lower() == "sqlite":
        return
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    modo_env = None
    for linha in env_path.read_text(encoding="utf-8").splitlines():
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

# Forçar modo SQLite
os.environ['DB_MODE'] = 'sqlite'

def test_sqlite_repositories():
    """Testa se todos os repositórios SQLite podem ser criados"""
    
    print("=" * 60)
    print("TESTE DE INTEGRIDADE - MODO SQLITE")
    print("=" * 60)
    print()
    
    # Limpar banco de teste se existir
    db_path = Path("financeiro.db")
    if db_path.exists():
        db_path.unlink()
        print("✓ Banco de teste anterior removido")
    
    try:
        from financeiro.infrastructure.repository_factory import (
            get_despesas_repository,
            get_receitas_repository,
            get_categorias_repository,
            get_contas_repository,
            get_planejamento_repository,
            get_rendimentos_repository,
            get_dashboard_repository,
            get_admin_repository,
            get_home_repository,
            get_csv_repository,
            get_db_backup_repository,
            get_db_mode
        )
        
        print(f"✓ Modo detectado: {get_db_mode()}")
        print()
        
        repositories = [
            ("Despesas", get_despesas_repository),
            ("Receitas", get_receitas_repository),
            ("Categorias", get_categorias_repository),
            ("Contas", get_contas_repository),
            ("Planejamento", get_planejamento_repository),
            ("Rendimentos", get_rendimentos_repository),
            ("Dashboard", get_dashboard_repository),
            ("Admin", get_admin_repository),
            ("Home", get_home_repository),
            ("CSV", get_csv_repository),
            ("DB Backup", get_db_backup_repository),
        ]
        
        print("Testando criação de repositórios:")
        print("-" * 60)
        
        for name, factory in repositories:
            try:
                repo = factory()
                print(f"✓ {name:20} - OK")
            except Exception as e:
                print(f"✗ {name:20} - ERRO: {e}")
                return False
        
        print()
        print("-" * 60)
        
        # Verificar se o banco foi criado
        if db_path.exists():
            size = db_path.stat().st_size
            print(f"✓ Banco SQLite criado: {db_path.absolute()}")
            print(f"  Tamanho: {size:,} bytes")
        else:
            print("✗ Banco SQLite não foi criado")
            return False
        
        print()
        print("=" * 60)
        print("RESULTADO: TODOS OS TESTES PASSARAM ✓")
        print("=" * 60)
        print()
        print("O modo SQLite está funcionando corretamente!")
        print("Você pode usar 'construir.bat --com-sqlite' para gerar o executável.")
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"ERRO CRÍTICO: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_sqlite_repositories()
    sys.exit(0 if success else 1)
