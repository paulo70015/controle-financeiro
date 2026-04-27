from financeiro.domain.planejamento.entities import Fixa, Meta, PagamentoStatus


class PlanejamentoUseCases:
    def __init__(self, repository):
        self.repository = repository

    def criar_fixa(self, payload: dict) -> None:
        fixa = Fixa(
            descricao=payload["descricao"],
            valor=float(payload["valor"]),
            dia=int(payload.get("dia", 0)),
            cat_id=payload.get("cat_id"),
            ano=int(payload["ano"]),
        )
        self.repository.add_fixa(fixa)

    def editar_fixa(self, fixa_id: int, payload: dict) -> None:
        self.repository.update_fixa(fixa_id=fixa_id, payload=payload)

    def excluir_fixa(self, fixa_id: int) -> None:
        self.repository.delete_fixa(fixa_id)

    def criar_meta(self, payload: dict) -> None:
        meta = Meta(
            descricao=payload["descricao"],
            valor=float(payload.get("valor", 0)),
            ano_meta=payload.get("ano_meta"),
            ano_criacao=int(payload.get("ano_criacao")),
        )
        self.repository.add_meta(meta)

    def atualizar_meta(self, meta_id: int, payload: dict, method: str) -> None:
        self.repository.update_meta(meta_id=meta_id, payload=payload, method=method)

    def fixa_excecao(self, payload: dict, method: str) -> None:
        self.repository.toggle_fixa_excecao(payload=payload, method=method)

    def toggle_fixa_aplicada_manual(self, payload: dict, method: str) -> None:
        """Marca/desmarca uma fixa como aplicada manualmente"""
        self.repository.toggle_fixa_aplicada_manual(payload=payload, method=method)

    def salvar_pagamento_status(self, payload: dict) -> None:
        status = PagamentoStatus(
            ano=int(payload["ano"]),
            mes=int(payload["mes"]),
            categoria=payload["categoria"],
            status=int(payload["status"]),
        )
        self.repository.save_pagamento_status(status)

