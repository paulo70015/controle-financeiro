from flask import Blueprint, jsonify, request

from financeiro.application.rendimentos.use_cases import RendimentosUseCases
from financeiro.infrastructure.repository_factory import get_rendimentos_repository


def create_rendimentos_blueprint(client_factory=None):
    bp = Blueprint("rendimentos", __name__)
    use_cases = RendimentosUseCases(get_rendimentos_repository())

    @bp.route("/api/rendimentos/locais/<int:ano>")
    def listar_locais(ano):
        return jsonify(use_cases.listar_locais(ano=ano))

    @bp.route("/api/rendimento/local", methods=["POST"])
    def criar_local():
        try:
            local_id = use_cases.criar_local(request.get_json() or {})
            return jsonify({"ok": True, "id": local_id})
        except ValueError as e:
            return jsonify({"ok": False, "erro": str(e)}), 400

    @bp.route("/api/rendimento/local/<int:local_id>", methods=["PUT"])
    def editar_local(local_id):
        try:
            use_cases.editar_local(local_id=local_id, payload=request.get_json() or {})
            return jsonify({"ok": True})
        except ValueError as e:
            return jsonify({"ok": False, "erro": str(e)}), 400

    @bp.route("/api/rendimento/local/<int:local_id>", methods=["DELETE"])
    def excluir_local(local_id):
        use_cases.excluir_local(local_id)
        return jsonify({"ok": True})

    @bp.route("/api/rendimentos/<int:ano>/<int:local_id>", methods=["DELETE"])
    def excluir_lancamentos_local_ano(ano, local_id):
        use_cases.excluir_lancamentos_local_ano(ano=ano, local_id=local_id)
        return jsonify({"ok": True})

    @bp.route("/api/rendimentos_detalhe/<int:ano>/<int:mes>/<int:local_id>")
    def detalhar(ano, mes, local_id):
        return jsonify(use_cases.detalhar(ano=ano, mes=mes, local_id=local_id))

    @bp.route("/api/rendimento/lancamento", methods=["POST"])
    def lancar():
        try:
            lancamento_id = use_cases.lancar(request.get_json() or {})
            return jsonify({"ok": True, "id": lancamento_id})
        except ValueError as e:
            return jsonify({"ok": False, "erro": str(e)}), 400

    @bp.route("/api/rendimento/lancamento/lote", methods=["POST"])
    def lancar_lote():
        try:
            use_cases.lancar_lote(request.get_json() or {})
            return jsonify({"ok": True}), 201
        except ValueError as e:
            return jsonify({"ok": False, "erro": str(e)}), 400

    @bp.route("/api/rendimento/lancamento/<int:lancamento_id>", methods=["PUT"])
    def edit_lancamento(lancamento_id):
        try:
            use_cases.editar_lancamento(lancamento_id, request.get_json() or {})
            return jsonify({"ok": True})
        except ValueError as e:
            return jsonify({"ok": False, "erro": str(e)}), 400

    @bp.route("/api/rendimento/lancamento/<int:lancamento_id>", methods=["DELETE"])
    def excluir_lancamento(lancamento_id):
        use_cases.excluir_lancamento(lancamento_id)
        return jsonify({"ok": True})

    @bp.route("/api/rendimento/projecao", methods=["POST"])
    def definir_projecao():
        try:
            use_cases.definir_projecao(request.get_json() or {})
            return jsonify({"ok": True})
        except ValueError as e:
            return jsonify({"ok": False, "erro": str(e)}), 400

    @bp.route("/api/rendimentos/locais/reordenar", methods=["POST"])
    def reordenar_locais():
        try:
            use_cases.reordenar_locais(request.get_json() or {})
            return jsonify({"ok": True})
        except ValueError as e:
            return jsonify({"ok": False, "erro": str(e)}), 400

    return bp
