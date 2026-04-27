from financeiro.domain.categorias.entities import Categoria


class CategoriasUseCases:
    def __init__(self, repository):
        self.repository = repository

    def criar(self, payload: dict) -> None:
        categoria = Categoria(
            ano=int(payload["ano"]),
            nome=payload["nome"],
            inclui_fixas=int(payload.get("inclui_fixas", 0)),
            conta_vinculada_id=payload.get("conta_vinculada_id"),
        )
        self.repository.add_categoria(categoria)

    def atualizar(self, categoria_id: int, payload: dict) -> bool:
        return self.repository.update_categoria(categoria_id=categoria_id, payload=payload)

    def excluir(self, categoria_id: int) -> None:
        self.repository.delete_categoria(categoria_id)

    def mover(self, categoria_id: int, direcao: str) -> bool:
        return self.repository.move_categoria(categoria_id=categoria_id, direcao=direcao)

    def reordenar(self, ordem_ids: list[int]) -> None:
        self.repository.reorder_categorias(ordem_ids)

