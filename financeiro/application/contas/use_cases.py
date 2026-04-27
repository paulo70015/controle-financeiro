from financeiro.domain.contas.entities import Conta, DepositoConta, MovimentacaoMensal


class ContasUseCases:
    def __init__(self, repository):
        self.repository = repository

    def criar_conta(self, payload: dict) -> None:
        conta = Conta(
            nome=payload["nome"],
            saldo_inicial=float(payload.get("saldo_inicial", 0)),
        )
        self.repository.add_conta(conta)

    def editar_conta(self, conta_id: int, payload: dict) -> None:
        self.repository.update_conta(conta_id=conta_id, payload=payload)

    def excluir_conta(self, conta_id: int) -> None:
        self.repository.delete_conta(conta_id)

    def adicionar_deposito(self, payload: dict) -> int:
        deposito = DepositoConta(
            ano=int(payload["ano"]),
            mes=int(payload["mes"]),
            conta_id=int(payload["conta_id"]),
            valor=float(payload["valor"]),
            nota=payload.get("nota", ""),
        )
        return self.repository.add_deposito(deposito)

    def excluir_deposito(self, deposito_id: int) -> None:
        self.repository.delete_deposito(deposito_id)

    def editar_deposito(self, deposito_id: int, payload: dict) -> None:
        valor = float(payload.get("valor", 0))
        nota = payload.get("nota", "")
        self.repository.update_deposito(deposito_id, valor, nota)

    def listar_depositos(self, ano: int, mes: int, conta_id: int) -> list[dict]:
        return self.repository.get_depositos_detalhe(ano=ano, mes=mes, conta_id=conta_id)

    def salvar_movimentacao(self, payload: dict) -> tuple[bool, str]:
        if payload.get("valor") is None or payload.get("conta_id") is None:
            return (False, "valor e conta_id obrigatorios")
        movimentacao = MovimentacaoMensal(
            ano=int(payload["ano"]),
            mes=int(payload["mes"]),
            conta_id=int(payload["conta_id"]),
            valor=float(payload["valor"]),
            nota=payload.get("nota", ""),
        )
        self.repository.upsert_movimentacao(movimentacao)
        return (True, "")

    def excluir_movimentacao(self, ano: int, mes: int) -> None:
        self.repository.delete_movimentacao(ano=ano, mes=mes)

