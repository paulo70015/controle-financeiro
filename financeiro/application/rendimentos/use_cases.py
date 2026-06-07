from financeiro.domain.rendimentos.entities import RendimentoLancamento, RendimentoLocal


class RendimentosUseCases:
    def __init__(self, repository):
        self.repository = repository

    def listar_locais(self, ano: int) -> list[dict]:
        return self.repository.get_locais(ano=ano)

    def criar_local(self, payload: dict) -> int:
        local = RendimentoLocal(
            ano=int(payload["ano"]),
            nome=(payload.get("nome") or "").strip(),
        )
        if not local.nome:
            raise ValueError("Nome do local é obrigatório")
        return self.repository.add_local(local)

    def editar_local(self, local_id: int, payload: dict) -> None:
        nome = (payload.get("nome") or "").strip()
        if not nome:
            raise ValueError("Nome do local é obrigatório")
        self.repository.update_local(local_id=local_id, nome=nome)

    def excluir_local(self, local_id: int) -> None:
        self.repository.delete_local(local_id)

    def excluir_lancamentos_local_ano(self, ano: int, local_id: int) -> None:
        self.repository.delete_lancamentos_local_ano(ano=ano, local_id=local_id)

    def detalhar(self, ano: int, mes: int, local_id: int) -> list[dict]:
        return self.repository.get_lancamentos_detalhe(ano=ano, mes=mes, local_id=local_id)

    def _validar_payload_lancamento(self, payload: dict) -> tuple[str, float, str]:
        tipo = (payload.get("tipo") or "").strip().lower()
        if tipo not in ("aporte", "rendimento", "saque"):
            raise ValueError("Tipo inválido. Use 'aporte', 'rendimento' ou 'saque'")
        valor = float(payload.get("valor") or 0)
        nota = (payload.get("nota") or "").strip()
        if tipo == "saque" and valor <= 0:
            raise ValueError("Saque deve ter valor maior que zero")
        if valor == 0 and not nota:
            raise ValueError("Informe um valor ou nota")
        return tipo, valor, nota

    def lancar(self, payload: dict) -> int:
        tipo, valor, nota = self._validar_payload_lancamento(payload)
        lanc = RendimentoLancamento(
            ano=int(payload["ano"]),
            mes=int(payload["mes"]),
            local_id=int(payload["local_id"]),
            tipo=tipo,
            valor=valor,
            nota=nota,
        )
        return self.repository.add_lancamento(lanc)

    def lancar_lote(self, payload: dict) -> None:
        tipo, valor, nota = self._validar_payload_lancamento(payload)
        ano = int(payload["ano"])
        local_id = int(payload["local_id"])
        mes_inicio = int(payload.get("mes_inicio", 1))
        
        for mes in range(mes_inicio, 13):
            lanc = RendimentoLancamento(
                ano=ano,
                mes=mes,
                local_id=local_id,
                tipo=tipo,
                valor=valor,
                nota=nota,
            )
            self.repository.add_lancamento(lanc)

    def editar_lancamento(self, lancamento_id: int, payload: dict) -> None:
        tipo, valor, nota = self._validar_payload_lancamento(payload)
        self.repository.update_lancamento(lancamento_id, tipo, valor, nota)

    def excluir_lancamento(self, lancamento_id: int) -> None:
        self.repository.delete_lancamento(lancamento_id)

    def definir_projecao(self, payload: dict) -> None:
        local_id = int(payload["local_id"])
        taxa = payload.get("taxa")
        if taxa is not None:
            taxa = float(taxa)
            if taxa <= 0:
                raise ValueError("Taxa de projeção deve ser maior que zero.")
        self.repository.update_projecao_taxa(local_id=local_id, taxa=taxa)

    def reordenar_locais(self, payload: dict) -> None:
        ordem_ids = payload.get("ordem_ids", [])
        if not isinstance(ordem_ids, list):
            raise ValueError("ordem_ids deve ser uma lista válida.")
        self.repository.reorder_locais(ordem_ids)
