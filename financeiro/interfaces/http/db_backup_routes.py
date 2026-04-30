from flask import Blueprint, jsonify, request

from financeiro.application.db_backup.use_cases import DBBackupUseCases
from financeiro.infrastructure.repository_factory import get_db_backup_repository


def create_db_backup_blueprint():
    bp = Blueprint("db_backup", __name__)
    use_cases = DBBackupUseCases(get_db_backup_repository())

    @bp.route("/api/db/exportar")
    def exportar_db():
        return use_cases.exportar()

    @bp.route("/api/db/importar", methods=["POST"])
    def importar_db():
        file_storage = request.files.get("arquivo")
        body, status = use_cases.importar(file_storage)
        return jsonify(body), status

    return bp
