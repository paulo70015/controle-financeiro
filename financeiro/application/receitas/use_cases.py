from financeiro.domain.receitas.entities import Receita, ReceitaLote


class ReceitasUseCases:
    def __init__(self, repository):
        self.repository = repository

    def lancar(self, payload: dict) -> int:
        receita = Receita(
            ano=int(payload["ano"]),
            mes=int(payload["mes"]),
            descricao=payload.get("descricao", "Salario"),
            valor=float(payload["valor"]),
            nota=payload.get("nota", ""),
        )
        return self.repository.add_receita(receita)

    def listar_mes(self, ano: int, mes: int) -> list[dict]:
        return self.repository.get_receitas_mes(ano=ano, mes=mes)

    def excluir(self, receita_id: int) -> None:
        self.repository.delete_receita(receita_id)

    def lancar_lote(self, payload: dict) -> None:
        lote = ReceitaLote(
            ano=int(payload["ano"]),
            descricao=payload.get("descricao", "Receita"),
            valor_base=float(payload["valor"]),
            acrescimo=float(payload.get("acrescimo", 0)),
            nota=payload.get("nota", ""),
        )
        meses = payload.get("meses", list(range(1, 13)))
        self.repository.add_receita_lote(lote=lote, meses=meses)

    def excluir_ano(self, ano: int) -> None:
        self.repository.delete_receitas_ano(ano)

    def editar(self, receita_id: int, payload: dict) -> None:
        valor = float(payload.get("valor", 0))
        nota = payload.get("nota", "")
        descricao = payload.get("descricao", "Receita")
        mes = payload.get("mes")
        self.repository.update_receita(receita_id, valor, nota, descricao, int(mes) if mes is not None else None)
