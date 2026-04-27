from flask import Blueprint, jsonify, request

from financeiro.application.admin.use_cases import AdminUseCases
from financeiro.infrastructure.repository_factory import get_admin_repository


def create_admin_blueprint(client_factory=None):
    bp = Blueprint("admin", __name__)
    use_cases = AdminUseCases(get_admin_repository())

    @bp.route("/api/config", methods=["POST"])
    def salvar_config():
        use_cases.salvar_config(request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/duplicar_ano", methods=["POST"])
    def duplicar_ano():
        ok, erro = use_cases.duplicar_ano(request.get_json() or {})
        if not ok:
            return jsonify({"ok": False, "erro": erro}), 400
        return jsonify({"ok": True})

    @bp.route("/api/ano/<int:ano>", methods=["DELETE"])
    def remover_ano(ano):
        use_cases.remover_ano(ano)
        return jsonify({"ok": True})

    return bp

