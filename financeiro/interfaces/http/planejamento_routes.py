from flask import Blueprint, jsonify, request

from financeiro.application.planejamento.use_cases import PlanejamentoUseCases
from financeiro.infrastructure.repository_factory import get_planejamento_repository


def create_planejamento_blueprint(client_factory=None):
    bp = Blueprint("planejamento", __name__)
    use_cases = PlanejamentoUseCases(get_planejamento_repository())

    @bp.route("/api/fixa", methods=["POST"])
    def add_fixa():
        use_cases.criar_fixa(request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/fixa/<int:fixa_id>", methods=["PUT"])
    def edit_fixa(fixa_id):
        use_cases.editar_fixa(fixa_id, request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/fixa/<int:fixa_id>", methods=["DELETE"])
    def del_fixa(fixa_id):
        use_cases.excluir_fixa(fixa_id)
        return jsonify({"ok": True})

    @bp.route("/api/meta", methods=["POST"])
    def add_meta():
        use_cases.criar_meta(request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/meta/<int:meta_id>", methods=["PUT", "DELETE"])
    def edit_meta(meta_id):
        use_cases.atualizar_meta(meta_id=meta_id, payload=request.get_json(silent=True) or {}, method=request.method)
        return jsonify({"ok": True})

    @bp.route("/api/fixa_excecao", methods=["POST", "DELETE"])
    def fixa_excecao():
        use_cases.fixa_excecao(payload=request.get_json(silent=True) or {}, method=request.method)
        return jsonify({"ok": True})

    @bp.route("/api/fixa_aplicada_manual", methods=["POST", "DELETE"])
    def fixa_aplicada_manual():
        """Marca/desmarca uma fixa como aplicada manualmente"""
        use_cases.toggle_fixa_aplicada_manual(payload=request.get_json(silent=True) or {}, method=request.method)
        return jsonify({"ok": True})

    @bp.route("/api/pagamento_status", methods=["POST"])
    def salvar_pagamento_status():
        use_cases.salvar_pagamento_status(request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/pagamento_status/lote", methods=["POST"])
    def salvar_pagamento_status_lote():
        use_cases.salvar_pagamento_status_lote(request.get_json() or {})
        return jsonify({"ok": True})

    return bp
