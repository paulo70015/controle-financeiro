from flask import Flask
import os
import sys
import atexit
import threading
import json

from version import get_version_full

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Correção para lidar adequadamente com PyInstaller (Arquivos embutidos vs Diretório local)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS  # Pasta temporária do PyInstaller com HTML e Estilos
    DATA_DIR = os.path.dirname(sys.executable)  # Pasta real de onde o .exe está rodando
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = BASE_DIR

# Carregar variáveis de ambiente ANTES de importar os módulos da aplicação
from dotenv import load_dotenv

env_path = os.path.join(DATA_DIR, ".env")
if not os.path.exists(env_path) and getattr(sys, 'frozen', False):
    env_path = os.path.join(BASE_DIR, ".env_embutido")

# Proteger DB_MODE definido externamente (ex: testes forcam sqlite)
_db_mode_before_dotenv = os.environ.get("DB_MODE")
load_dotenv(env_path, override=True)
if _db_mode_before_dotenv:
    os.environ["DB_MODE"] = _db_mode_before_dotenv

# Permite forcar SQLite via --sqlite na linha de comando (antes dos imports)
if "--sqlite" in sys.argv:
    os.environ["DB_MODE"] = "sqlite"

from financeiro.interfaces.http.despesas_routes import create_despesas_blueprint
from financeiro.interfaces.http.receitas_routes import create_receitas_blueprint
from financeiro.interfaces.http.categorias_routes import create_categorias_blueprint
from financeiro.interfaces.http.contas_routes import create_contas_blueprint
from financeiro.interfaces.http.planejamento_routes import create_planejamento_blueprint
from financeiro.interfaces.http.admin_routes import create_admin_blueprint
from financeiro.interfaces.http.csv_routes import create_csv_blueprint
from financeiro.interfaces.http.db_backup_routes import create_db_backup_blueprint
from financeiro.interfaces.http.dashboard_routes import create_dashboard_blueprint
from financeiro.interfaces.http.home_routes import create_home_blueprint
from financeiro.interfaces.http.rendimentos_routes import create_rendimentos_blueprint
from financeiro.infrastructure.repository_factory import get_db_mode
from financeiro.infrastructure.runtime.tray import run_windows_tray

# Forcar uso de IPv4 no Mac (Resolve problemas de Timeout no IPv6)
if sys.platform == 'darwin':
    import socket
    old_getaddrinfo = socket.getaddrinfo
    def new_getaddrinfo(*args, **kwargs):
        res = old_getaddrinfo(*args, **kwargs)
        return [r for r in res if r[0] == socket.AF_INET]
    socket.getaddrinfo = new_getaddrinfo

MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
"Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

def register_blueprints(flask_app):
    flask_app.register_blueprint(create_despesas_blueprint())
    flask_app.register_blueprint(create_receitas_blueprint())
    flask_app.register_blueprint(create_categorias_blueprint())
    flask_app.register_blueprint(create_contas_blueprint())
    flask_app.register_blueprint(create_planejamento_blueprint())
    flask_app.register_blueprint(create_admin_blueprint())
    flask_app.register_blueprint(create_csv_blueprint(meses=MESES))
    flask_app.register_blueprint(create_db_backup_blueprint())
    flask_app.register_blueprint(create_dashboard_blueprint(meses=MESES))
    flask_app.register_blueprint(create_home_blueprint(meses=MESES))
    flask_app.register_blueprint(create_rendimentos_blueprint())


def create_app():
    flask_app = Flask(__name__, template_folder=BASE_DIR)
    register_blueprints(flask_app)
    return flask_app


app = create_app()

if __name__ == "__main__":
    import argparse, webbrowser
    parser=argparse.ArgumentParser()
    parser.add_argument("--show-console",action="store_true",help="Exibe logs no console")
    parser.add_argument("--sqlite",action="store_true",help="Usa banco SQLite local em vez de Supabase")
    args=parser.parse_args()

    if args.sqlite:
        os.environ["DB_MODE"] = "sqlite"

    db_mode = get_db_mode()

    if db_mode == 'sqlite':
        try:
            from financeiro.infrastructure.sqlite.database import setup_database
            setup_database()
        except ImportError:
            pass

    port = int(os.environ.get("PORT", 8080))

    if not args.show_console:
        import logging; logging.getLogger("werkzeug").setLevel(logging.ERROR)
        
        null_file = open(os.devnull, "w", encoding="utf-8")
        sys.stdout = null_file
        sys.stderr = null_file
        atexit.register(lambda: null_file.close())
    else:
        print(f"\n Controle de Financas {get_version_full()} ({db_mode.upper()}) em: http://localhost:{port}\n")
    threading.Thread(target=lambda:app.run(debug=False,port=port,use_reloader=False),daemon=True).start()
    if not os.getenv("FLASK_SKIP_BROWSER"):
        threading.Timer(1.2,lambda:webbrowser.open(f"http://localhost:{port}")).start()
    try:
        if args.show_console:
            input()
        else:
            import time
            start_time = time.time()
            try:
                run_windows_tray(lambda: None, app_url=f"http://localhost:{port}")  # Tenta iniciar o ícone
            except Exception as e:
                print(f"Erro no tray: {e}")
            
            # Se o tray ignorar o Mac ou der erro, ele retorna em menos de 2 segundos.
            # Nesse caso, ativamos o loop para manter o servidor vivo.
            # Se demorou mais que isso, o usuário usou o app e clicou em "Sair", então podemos fechar limpo!
            if time.time() - start_time < 2:
                while True:
                    time.sleep(1)
    except (KeyboardInterrupt, SystemExit, EOFError):
        if args.show_console: print("\nEncerrando...")
