from datetime import datetime

from flask import Blueprint, render_template, request

from version import get_version_full
from financeiro.application.home.use_cases import HomeUseCases
from financeiro.infrastructure.repository_factory import get_db_mode, get_home_repository

# Nomes completos dos meses para modais
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# Nomes abreviados dos meses para colunas da tabela
MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def create_home_blueprint(client_factory=None, meses=None):
    bp = Blueprint("home", __name__)
    use_cases = HomeUseCases(get_home_repository())

    @bp.route("/")
    def index():
        ano = request.args.get("ano", datetime.now().year, type=int)
        # Garante que o ano fique registrado na tabela `anos` (best-effort)
        use_cases.garantir_ano_existe(ano)
        anos = use_cases.listar_anos(ano)
        return render_template("index.html", ano=ano, anos=anos, 
                             meses=MESES, meses_abrev=MESES_ABREV, db_mode=get_db_mode(),
                             versao=get_version_full())

    return bp

