"""
Teste de integridade do modo SQLite
Valida que todos os repositórios podem ser instanciados
"""

import os
import sys
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# VERIFICAR Supabase — aborta se Supabase estiver ativo/acessivel
# ═══════════════════════════════════════════════════════════════════
sys.path.insert(0, str(Path(__file__).parent))
from test_browser.verificar_ambiente import verificar as _verificar_supabase
_verificar_supabase()

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
        print("Você pode usar 'scripts\construir.bat --com-sqlite' para gerar o executável.")
        
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
