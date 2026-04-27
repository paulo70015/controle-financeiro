from flask import Blueprint, jsonify, request

from financeiro.application.categorias.use_cases import CategoriasUseCases
from financeiro.infrastructure.repository_factory import get_categorias_repository


def create_categorias_blueprint(client_factory=None):
    bp = Blueprint("categorias", __name__)
    use_cases = CategoriasUseCases(get_categorias_repository())

    @bp.route("/api/categoria", methods=["POST"])
    def add_categoria():
        use_cases.criar(request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/categoria/<int:categoria_id>", methods=["PUT"])
    def rename_categoria(categoria_id):
        ok = use_cases.atualizar(categoria_id=categoria_id, payload=request.get_json() or {})
        if not ok:
            return jsonify({"ok": False}), 404
        return jsonify({"ok": True})

    @bp.route("/api/categoria/<int:categoria_id>", methods=["DELETE"])
    def del_categoria(categoria_id):
        use_cases.excluir(categoria_id)
        return jsonify({"ok": True})

    @bp.route("/api/categoria/<int:categoria_id>/mover", methods=["POST"])
    def mover_categoria(categoria_id):
        payload = request.get_json() or {}
        ok = use_cases.mover(categoria_id=categoria_id, direcao=payload.get("direcao", "cima"))
        if not ok:
            return jsonify({"ok": False}), 404
        return jsonify({"ok": True})

    @bp.route("/api/categorias/reordenar", methods=["POST"])
    def reordenar_categorias():
        payload = request.get_json() or {}
        use_cases.reordenar(payload.get("ordem", []))
        return jsonify({"ok": True})

    return bp

