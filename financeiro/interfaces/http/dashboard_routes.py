from flask import Blueprint, jsonify

from financeiro.application.dashboard.use_cases import DashboardUseCases
from financeiro.infrastructure.repository_factory import get_dashboard_repository


def create_dashboard_blueprint(client_factory=None, meses=None):
    bp = Blueprint("dashboard", __name__)
    use_cases = DashboardUseCases(get_dashboard_repository())

    @bp.route("/api/dados/<int:ano>")
    def api_dados(ano):
        data = use_cases.carregar_dados_ano(ano)
        return jsonify(data)

    return bp
