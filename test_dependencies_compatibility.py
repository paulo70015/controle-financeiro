"""
Teste de Compatibilidade de Dependências
Valida se as versões atuais funcionam com Python 3.14+
"""

import sys
import os

def test_python_version():
    """Verifica versão do Python"""
    print("=" * 70)
    print("TESTE DE COMPATIBILIDADE DE DEPENDÊNCIAS")
    print("=" * 70)
    print()
    print(f"Python: {sys.version}")
    print(f"Versão: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print()
    
    if sys.version_info >= (3, 14):
        print("⚠️  Python 3.14+ detectado - testando compatibilidade...")
    else:
        print("✓ Python < 3.14 - compatibilidade esperada")
    print()


def test_imports():
    """Testa imports críticos"""
    print("-" * 70)
    print("TESTANDO IMPORTS CRÍTICOS")
    print("-" * 70)
    
    tests = []
    
    # Flask
    try:
        import flask
        tests.append(("Flask", flask.__version__, "✓"))
    except Exception as e:
        tests.append(("Flask", str(e), "✗"))
    
    # PostgREST (o que realmente usamos)
    try:
        from postgrest import SyncPostgrestClient
        import postgrest
        tests.append(("postgrest", postgrest.__version__, "✓"))
    except Exception as e:
        tests.append(("postgrest", str(e), "✗"))
    
    # Supabase (wrapper, menos crítico)
    try:
        import supabase
        tests.append(("supabase", supabase.__version__, "✓"))
    except Exception as e:
        tests.append(("supabase", str(e), "✗"))
    
    # psycopg2 (para SQLite não é necessário, mas está no requirements)
    try:
        import psycopg2
        tests.append(("psycopg2", psycopg2.__version__, "✓"))
    except Exception as e:
        tests.append(("psycopg2", str(e), "✗"))
    
    # Pillow
    try:
        import PIL
        tests.append(("Pillow", PIL.__version__, "✓"))
    except Exception as e:
        tests.append(("Pillow", str(e), "✗"))
    
    # pystray
    try:
        import pystray
        # pystray não tem __version__, mas se importou está OK
        tests.append(("pystray", "OK (sem __version__)", "✓"))
    except Exception as e:
        tests.append(("pystray", str(e), "✗"))
    
    # PyInstaller
    try:
        import PyInstaller
        tests.append(("PyInstaller", PyInstaller.__version__, "✓"))
    except Exception as e:
        tests.append(("PyInstaller", str(e), "✗"))
    
    # Exibir resultados
    for name, version, status in tests:
        print(f"{status} {name:20} {version}")
    
    print()
    failed = [t for t in tests if t[2] == "✗"]
    return len(failed) == 0


def test_supabase_client():
    """Testa se o cliente Supabase funciona"""
    print("-" * 70)
    print("TESTANDO CLIENTE SUPABASE")
    print("-" * 70)
    
    # Salvar env original
    original_url = os.environ.get("SUPABASE_URL")
    original_key = os.environ.get("SUPABASE_KEY")
    
    try:
        # Configurar env fake para teste
        os.environ["SUPABASE_URL"] = "https://test.supabase.co"
        os.environ["SUPABASE_KEY"] = "test_key_123"
        
        from financeiro.infrastructure.supabase.client import Client
        
        client = Client(
            "https://test.supabase.co",
            "test_key_123"
        )
        
        # Verificar se o método table() funciona
        table = client.table("test_table")
        
        print("✓ Cliente Supabase instanciado com sucesso")
        print(f"  URL: {client.rest_url}")
        print(f"  Método table() funciona: {table is not None}")
        print()
        return True
        
    except Exception as e:
        print(f"✗ Erro ao instanciar cliente: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restaurar env original
        if original_url:
            os.environ["SUPABASE_URL"] = original_url
        else:
            os.environ.pop("SUPABASE_URL", None)
        
        if original_key:
            os.environ["SUPABASE_KEY"] = original_key
        else:
            os.environ.pop("SUPABASE_KEY", None)


def test_sqlite_mode():
    """Testa modo SQLite"""
    print("-" * 70)
    print("TESTANDO MODO SQLITE")
    print("-" * 70)
    
    os.environ["DB_MODE"] = "sqlite"
    
    try:
        from financeiro.infrastructure.repository_factory import get_db_mode, get_despesas_repository
        
        mode = get_db_mode()
        print(f"✓ Modo detectado: {mode}")
        
        repo = get_despesas_repository()
        print(f"✓ Repository SQLite criado: {type(repo).__name__}")
        print()
        return True
        
    except Exception as e:
        print(f"✗ Erro no modo SQLite: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    test_python_version()
    
    imports_ok = test_imports()
    client_ok = test_supabase_client()
    sqlite_ok = test_sqlite_mode()
    
    print("=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"Imports:         {'✓ OK' if imports_ok else '✗ FALHOU'}")
    print(f"Cliente Supabase: {'✓ OK' if client_ok else '✗ FALHOU'}")
    print(f"Modo SQLite:     {'✓ OK' if sqlite_ok else '✗ FALHOU'}")
    print()
    
    if imports_ok and client_ok and sqlite_ok:
        print("✓ TODAS AS DEPENDÊNCIAS ESTÃO FUNCIONANDO")
        print()
        print("RECOMENDAÇÃO:")
        print("As versões atuais estão funcionando com Python 3.14+")
        print("Você pode manter as versões fixadas ou atualizar com cautela.")
        print()
        print("Para atualizar (OPCIONAL):")
        print("  pip install --upgrade postgrest")
        print("  pip install --upgrade Flask")
        print("  pip install --upgrade Pillow")
        print()
        return True
    else:
        print("✗ ALGUMAS DEPENDÊNCIAS FALHARAM")
        print()
        print("AÇÃO NECESSÁRIA:")
        print("Atualize as dependências que falharam:")
        if not imports_ok:
            print("  pip install --upgrade -r requirements.txt")
        print()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
