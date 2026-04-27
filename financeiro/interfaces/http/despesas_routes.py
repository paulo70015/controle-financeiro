from flask import Blueprint, jsonify, request

from financeiro.application.despesas.use_cases import DespesasUseCases
from financeiro.infrastructure.repository_factory import (
    get_despesas_repository,
    get_categorias_repository
)


def create_despesas_blueprint(client_factory=None):
    bp = Blueprint("despesas", __name__)
    
    # Instanciar repositórios via factory (ignora client_factory)
    despesas_repo = get_despesas_repository()
    categorias_repo = get_categorias_repository()
    
    # Injetar ambos no use case
    use_cases = DespesasUseCases(
        repository=despesas_repo,
        categorias_repository=categorias_repo
    )

    @bp.route("/api/despesa", methods=["POST"])
    def add_despesa():
        despesa_id = use_cases.lancar(request.get_json() or {})
        return jsonify({"ok": True, "id": despesa_id})

    @bp.route("/api/despesa/lote", methods=["POST"])
    def add_despesa_lote():
        ids = use_cases.lancar_lote(request.get_json() or {})
        return jsonify({"ok": True, "ids": ids})

    @bp.route("/api/despesa/<int:despesa_id>", methods=["PUT"])
    def edit_despesa(despesa_id):
        use_cases.editar(despesa_id=despesa_id, payload=request.get_json() or {})
        return jsonify({"ok": True})

    @bp.route("/api/despesa/<int:despesa_id>", methods=["DELETE"])
    def del_despesa(despesa_id):
        use_cases.excluir(despesa_id)
        return jsonify({"ok": True})

    @bp.route("/api/despesas_detalhe/<int:ano>/<int:mes>/<path:categoria>")
    def despesas_detalhe(ano, mes, categoria):
        return jsonify(use_cases.detalhar(ano=ano, mes=mes, categoria=categoria))

    @bp.route("/api/despesas/<int:ano>/<path:categoria>", methods=["DELETE"])
    def del_despesas_categoria_ano(ano, categoria):
        use_cases.excluir_categoria_no_ano(ano=ano, categoria=categoria)
        return jsonify({"ok": True})

    return bp
