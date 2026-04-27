from flask import Blueprint, jsonify, request

from financeiro.application.csv.use_cases import CSVUseCases
from financeiro.infrastructure.repository_factory import get_csv_repository


def create_csv_blueprint(client_factory=None, meses=None):
    bp = Blueprint("csv", __name__)
    use_cases = CSVUseCases(get_csv_repository())

    @bp.route("/api/importar_csv", methods=["POST"])
    def importar_csv():
        file_storage = request.files.get("arquivo")
        body, status = use_cases.importar(file_storage)
        return jsonify(body), status

    @bp.route("/api/csv/undo", methods=["POST"])
    def desfazer_importacao():
        body, status = use_cases.desfazer_importacao()
        return jsonify(body), status

    @bp.route("/api/exportar/<int:ano>")
    def exportar_csv(ano):
        return use_cases.exportar(ano)

    return bp
