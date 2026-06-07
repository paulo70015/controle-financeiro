from flask import Blueprint, jsonify, request

from financeiro.application.contas.use_cases import ContasUseCases
from financeiro.infrastructure.repository_factory import get_contas_repository


def create_contas_blueprint(client_factory=None):
    bp = Blueprint("contas", __name__)
    use_cases = ContasUseCases(get_contas_repository())

    @bp.route("/api/conta", methods=["POST"])
    def add_conta():
        use_cases.criar_conta(request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/conta/<int:conta_id>", methods=["PUT", "DELETE"])
    def edit_conta(conta_id):
        if request.method == "DELETE":
            use_cases.excluir_conta(conta_id)
            return jsonify({"ok": True})
        use_cases.editar_conta(conta_id=conta_id, payload=request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/deposito", methods=["POST"])
    def add_deposito():
        deposito_id = use_cases.adicionar_deposito(request.get_json() or {})
        return jsonify({"ok": True, "id": deposito_id})

    @bp.route("/api/deposito/<int:deposito_id>", methods=["PUT"])
    def edit_deposito(deposito_id):
        use_cases.editar_deposito(deposito_id=deposito_id, payload=request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/deposito/<int:deposito_id>", methods=["DELETE"])
    def del_deposito(deposito_id):
        use_cases.excluir_deposito(deposito_id)
        return jsonify({"ok": True})

    @bp.route("/api/depositos_detalhe/<int:ano>/<int:mes>/<int:conta_id>")
    def depositos_detalhe(ano, mes, conta_id):
        return jsonify(use_cases.listar_depositos(ano=ano, mes=mes, conta_id=conta_id))

    @bp.route("/api/movimentacao", methods=["POST"])
    def salvar_movimentacao():
        ok, erro, movimentacao_id = use_cases.salvar_movimentacao(request.get_json() or {})
        if not ok:
            return jsonify({"ok": False, "erro": erro}), 400
        return jsonify({"ok": True, "id": movimentacao_id})

    @bp.route("/api/movimentacao/<int:movimentacao_id>", methods=["DELETE"])
    def del_movimentacao(movimentacao_id):
        use_cases.excluir_movimentacao(movimentacao_id)
        return jsonify({"ok": True})

    @bp.route("/api/movimentacao/<int:ano>/<int:mes>", methods=["DELETE"])
    def del_movimentacoes_mes(ano, mes):
        use_cases.excluir_movimentacoes_mes(ano=ano, mes=mes)
        return jsonify({"ok": True})

    return bp
