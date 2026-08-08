"""
Teste de integridade do modo SQLite
Valida que todos os repositórios podem ser instanciados
"""

import os
import sys
import tempfile
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# VERIFICAR Supabase — aborta se Supabase estiver ativo/acessivel
# ═══════════════════════════════════════════════════════════════════
sys.path.insert(0, str(Path(__file__).parent))
from test_browser.processos_util import limpar_banco_teste
from test_browser.verificar_ambiente import verificar as _verificar_supabase
_verificar_supabase()

# Forçar modo SQLite
os.environ['DB_MODE'] = 'sqlite'

# Isolamento: banco de teste em TEMP (fora do OneDrive) — NUNCA toca/apaga o
# financeiro.db real do usuário.
DB_TESTE = Path(tempfile.gettempdir()) / "controle_financeiro_sqlite_mode" / "financeiro.db"
os.environ['SQLITE_DB_PATH'] = str(DB_TESTE)

def test_sqlite_repositories():
    """Testa se todos os repositórios SQLite podem ser criados"""
    
    print("=" * 60)
    print("TESTE DE INTEGRIDADE - MODO SQLITE")
    print("=" * 60)
    print()
    
    # Limpar banco de teste anterior (se existir), incluindo WAL/SHM
    DB_TESTE.parent.mkdir(parents=True, exist_ok=True)
    limpar_banco_teste(DB_TESTE)
    if not DB_TESTE.exists():
        print("✓ Banco de teste anterior removido")
    else:
        try:
            DB_TESTE.unlink()
            print("✓ Banco de teste anterior removido")
        except OSError:
            print("⚠ Não foi possível remover banco de teste anterior")
    
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
        
        # Verificar se o banco foi criado (em TEMP, nunca no financeiro.db real)
        if DB_TESTE.exists():
            size = DB_TESTE.stat().st_size
            print(f"✓ Banco SQLite criado: {DB_TESTE.absolute()}")
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
        print("Você pode usar 'scripts\construir.bat --com-sqlite' para gerar o executável.")

        # Limpar banco de teste do TEMP
        limpar_banco_teste(DB_TESTE)
        try:
            DB_TESTE.parent.rmdir()
        except OSError:
            pass

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
