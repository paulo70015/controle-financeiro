from datetime import datetime

from flask import Blueprint, render_template, request

from version import get_version_full
from financeiro.application.home.use_cases import HomeUseCases
from financeiro.infrastructure.constantes import MESES, MESES_EXTENSO
from financeiro.infrastructure.repository_factory import get_db_mode, get_home_repository


def create_home_blueprint(client_factory=None):
    bp = Blueprint("home", __name__)
    use_cases = HomeUseCases(get_home_repository())

    @bp.route("/")
    def index():
        ano = request.args.get("ano", datetime.now().year, type=int)
        # Garante que o ano fique registrado na tabela `anos` (best-effort)
        use_cases.garantir_ano_existe(ano)
        anos = use_cases.listar_anos(ano)
        return render_template("index.html", ano=ano, anos=anos, 
                             meses=MESES_EXTENSO, meses_abrev=MESES, db_mode=get_db_mode(),
                             versao=get_version_full())

    return bp

