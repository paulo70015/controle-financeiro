from flask import Blueprint, jsonify, request

from financeiro.application.receitas.use_cases import ReceitasUseCases
from financeiro.infrastructure.repository_factory import get_receitas_repository


def create_receitas_blueprint(client_factory=None):
    bp = Blueprint("receitas", __name__)
    use_cases = ReceitasUseCases(get_receitas_repository())

    @bp.route("/api/receita", methods=["POST"])
    def add_receita():
        receita_id = use_cases.lancar(request.get_json() or {})
        return jsonify({"ok": True, "id": receita_id})

    @bp.route("/api/receitas/<int:ano>/<int:mes>")
    def get_receitas_mes(ano, mes):
        return jsonify(use_cases.listar_mes(ano=ano, mes=mes))

    @bp.route("/api/receita/<int:receita_id>", methods=["PUT"])
    def edit_receita(receita_id):
        use_cases.editar(receita_id=receita_id, payload=request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/receita/<int:receita_id>", methods=["DELETE"])
    def del_receita(receita_id):
        use_cases.excluir(receita_id)
        return jsonify({"ok": True})

    @bp.route("/api/receita/lote", methods=["POST"])
    def add_receita_lote():
        use_cases.lancar_lote(request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/receitas/<int:ano>", methods=["DELETE"])
    def del_receitas_ano(ano):
        use_cases.excluir_ano(ano)
        return jsonify({"ok": True})

    return bp
