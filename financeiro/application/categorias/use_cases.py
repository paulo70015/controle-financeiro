from financeiro.domain.categorias.entities import Categoria


class CategoriasUseCases:
    def __init__(self, repository):
        self.repository = repository

    def _validar_conta_vinculada(self, conta_vinculada_id):
        """Valida conta vinculada informada (BUG-12): id deve existir ou ser vazio."""
        if conta_vinculada_id in (None, "", 0, "0"):
            return None
        if not self.repository.conta_existe(conta_vinculada_id):
            raise ValueError("conta_vinculada_id não existe")
        return int(conta_vinculada_id)

    def criar(self, payload: dict) -> None:
        categoria = Categoria(
            ano=int(payload["ano"]),
            nome=payload["nome"],
            inclui_fixas=int(payload.get("inclui_fixas", 0)),
            conta_vinculada_id=self._validar_conta_vinculada(
                payload.get("conta_vinculada_id")
            ),
            is_cartao=int(payload.get("is_cartao", 0)),
            tooltip=payload.get("tooltip")
        )
        self.repository.add_categoria(categoria)

    def atualizar(self, categoria_id: int, payload: dict) -> bool:
        if "conta_vinculada_id" in payload:
            payload = dict(payload)
            payload["conta_vinculada_id"] = self._validar_conta_vinculada(
                payload.get("conta_vinculada_id")
            )
        return self.repository.update_categoria(categoria_id=categoria_id, payload=payload)

    def excluir(self, categoria_id: int) -> None:
        self.repository.delete_categoria(categoria_id)

    def mover(self, categoria_id: int, direcao: str) -> bool:
        return self.repository.move_categoria(categoria_id=categoria_id, direcao=direcao)

    def reordenar(self, ordem_ids: list[int]) -> None:
        self.repository.reorder_categorias(ordem_ids)

