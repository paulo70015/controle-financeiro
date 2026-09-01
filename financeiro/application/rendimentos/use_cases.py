from financeiro.domain.contas.entities import MovimentacaoMensal
from financeiro.domain.rendimentos.entities import RendimentoLancamento, RendimentoLocal
from financeiro.domain.validacao import parse_valor_finito


class RendimentosUseCases:
    def __init__(self, repository, contas_repository=None):
        self.repository = repository
        self.contas_repository = contas_repository

    def listar_locais(self, ano: int) -> list[dict]:
        return self.repository.get_locais(ano=ano)

    def criar_local(self, payload: dict) -> int:
        local = RendimentoLocal(
            ano=int(payload["ano"]),
            nome=(payload.get("nome") or "").strip(),
            conta_vinculada_id=self._parse_conta_vinculada(payload),
        )
        if not local.nome:
            raise ValueError("Nome do local é obrigatório")
        return self.repository.add_local(local)

    def editar_local(self, local_id: int, payload: dict) -> None:
        nome = (payload.get("nome") or "").strip()
        if not nome:
            raise ValueError("Nome do local é obrigatório")
        conta_vinculada_id = self._parse_conta_vinculada(payload)
        local_anterior = self.repository.get_local_by_id(local_id)
        self.repository.update_local(
            local_id=local_id,
            nome=nome,
            conta_vinculada_id=conta_vinculada_id,
        )
        # Re-propaga os reflexos quando a conta vinculada ou o nome muda
        # (a nota do reflexo carrega o nome do local).
        if self.contas_repository is not None and local_anterior:
            self._repropagar_reflexos_local(
                ano=int(local_anterior["ano"]), local_id=local_id
            )

    @staticmethod
    def _parse_conta_vinculada(payload: dict):
        if "conta_vinculada_id" not in payload:
            return None
        valor = payload.get("conta_vinculada_id")
        if valor in (None, "", 0, "0"):
            return None
        try:
            return int(valor)
        except (TypeError, ValueError):
            return None

    def excluir_local(self, local_id: int) -> None:
        if self.contas_repository is not None:
            # BUG-9: remover reflexos de TODOS os anos do local, não apenas do
            # ano do local — lançamentos de outros anos ficariam órfãos.
            lancs = self.repository.get_lancamentos_local(local_id)
            for lanc in lancs:
                self.contas_repository.delete_movimentacao_reflexo(lanc["id"])
        self.repository.delete_local(local_id)

    def excluir_lancamentos_local_ano(self, ano: int, local_id: int) -> None:
        if self.contas_repository is not None:
            self._remover_reflexos_local(ano=ano, local_id=local_id)
        self.repository.delete_lancamentos_local_ano(ano=ano, local_id=local_id)

    def detalhar(self, ano: int, mes: int, local_id: int) -> list[dict]:
        return self.repository.get_lancamentos_detalhe(ano=ano, mes=mes, local_id=local_id)

    def _validar_payload_lancamento(self, payload: dict) -> tuple[str, float, str]:
        tipo = (payload.get("tipo") or "").strip().lower()
        if tipo not in ("aporte", "rendimento", "saque"):
            raise ValueError("Tipo inválido. Use 'aporte', 'rendimento' ou 'saque'")
        valor = parse_valor_finito(payload.get("valor") or 0)  # BUG-7: rejeita NaN/Inf
        nota = (payload.get("nota") or "").strip()
        # Normalização de sinais: o saldo é calculado como saldo + aporte - saque.
        # Aporte negativo vira saque; saque negativo é normalizado para positivo.
        if tipo == "aporte" and valor < 0:
            tipo, valor = "saque", -valor
        elif tipo == "saque" and valor < 0:
            valor = -valor
        if tipo == "saque" and valor == 0:
            raise ValueError("Saque deve ter valor diferente de zero")
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
        lancamento_id = self.repository.add_lancamento(lanc)
        # BUG-10: reflexo em passo separado — se falhar, remove o lançamento
        # recém-criado (rollback compensatório) para não deixar estado parcial.
        try:
            self._refletir_em_conta_vinculada(lanc, lancamento_id)
        except Exception:
            self.repository.delete_lancamento(lancamento_id)
            raise
        return lancamento_id

    def lancar_lote(self, payload: dict) -> None:
        tipo, valor, nota = self._validar_payload_lancamento(payload)
        ano = int(payload["ano"])
        local_id = int(payload["local_id"])
        mes_inicio = int(payload.get("mes_inicio", 1))
        # BUG-6: valida mês inicial antes de gerar linhas (evita mês 0/negativo)
        if not 1 <= mes_inicio <= 12:
            raise ValueError("mes_inicio deve estar entre 1 e 12")

        criados: list[int] = []
        try:
            for mes in range(mes_inicio, 13):
                lanc = RendimentoLancamento(
                    ano=ano,
                    mes=mes,
                    local_id=local_id,
                    tipo=tipo,
                    valor=valor,
                    nota=nota,
                )
                lancamento_id = self.repository.add_lancamento(lanc)
                criados.append(lancamento_id)
                self._refletir_em_conta_vinculada(lanc, lancamento_id)
        except Exception:
            # BUG-10: rollback compensatório do lote
            for lancamento_id in criados:
                self.repository.delete_lancamento(lancamento_id)
            raise

    def editar_lancamento(self, lancamento_id: int, payload: dict) -> None:
        tipo, valor, nota = self._validar_payload_lancamento(payload)
        self.repository.update_lancamento(lancamento_id, tipo, valor, nota)
        # Recalcula o reflexo (upsert) ou o remove se não deve mais refletir.
        if self.contas_repository is not None:
            lanc = self.repository.get_lancamento_by_id(lancamento_id)
            if lanc:
                self._refletir_em_conta_vinculada(
                    self._lancamento_para_reflexo(lanc), lancamento_id
                )

    def excluir_lancamento(self, lancamento_id: int) -> None:
        if self.contas_repository is not None:
            self.contas_repository.delete_movimentacao_reflexo(lancamento_id)
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
        # BUG-16: impede sobrescrever ordens de outro ano — todos os ids
        # devem existir e pertencer ao mesmo ano.
        anos = set()
        for local_id in ordem_ids:
            local = self.repository.get_local_by_id(local_id)
            if not local:
                raise ValueError(f"Local {local_id} não encontrado")
            anos.add(local["ano"])
        if len(anos) > 1:
            raise ValueError("ordem_ids deve conter apenas locais do mesmo ano")
        self.repository.reorder_locais(ordem_ids)

    # ------------------------------------------------------------------
    # Reflexo automático na conta vinculada
    # ------------------------------------------------------------------

    def _local_para_reflexo(self, lanc_tipo: str, lanc_nota: str, lanc_valor: float, local_id: int):
        """
        Retorna o local de rendimento quando o lançamento deve refletir na
        conta corrente vinculada; caso contrário, None.

        Visão B (conta = patrimônio total): apenas aportes e rendimentos
        refletem; saques não (resgate é conversão interna — o dinheiro já
        está contabilizado na conta). Apenas lançamentos reais (não
        'Projeção'), com valor != 0, de local com conta vinculada.
        """
        if self.contas_repository is None:
            return None
        if lanc_tipo not in ("aporte", "rendimento"):
            return None
        if (lanc_nota or "").strip() == "Projeção":
            return None
        if not lanc_valor:
            return None
        local = self.repository.get_local_by_id(local_id)
        if not local or not local.get("conta_vinculada_id"):
            return None
        return local

    @staticmethod
    def _nota_reflexo(local_nome: str, tipo: str) -> str:
        nome = (local_nome or "").strip()
        if tipo == "aporte":
            return f"Aporte em {nome}".strip()
        if tipo == "saque":
            return f"Saque de {nome}".strip()
        return f"Rendimento de {nome}".strip()

    @staticmethod
    def _lancamento_para_reflexo(lanc_dict: dict) -> RendimentoLancamento:
        return RendimentoLancamento(
            ano=int(lanc_dict["ano"]),
            mes=int(lanc_dict["mes"]),
            local_id=int(lanc_dict["local_id"]),
            tipo=lanc_dict["tipo"],
            valor=float(lanc_dict["valor"] or 0),
            nota=lanc_dict.get("nota") or "",
        )

    def _refletir_em_conta_vinculada(self, lanc: RendimentoLancamento, lancamento_id: int) -> None:
        """
        Cria ou atualiza a movimentação refletida do lançamento na conta
        vinculada ao local. Se o lançamento não deve mais refletir, remove
        a movimentação existente (vínculo por rendimento_lancamento_id).

        Visão B (conta = patrimônio total):
        - Aporte: crédito na conta (o valor investido permanece no patrimônio).
        - Rendimento: crédito na conta (riqueza nova).
        - Saque: não reflete — o resgate é conversão interna e o dinheiro já
          está contabilizado na conta.
        """
        if self.contas_repository is None:
            return
        local = self._local_para_reflexo(
            lanc.tipo, lanc.nota, lanc.valor, lanc.local_id
        )
        if not local:
            self.contas_repository.delete_movimentacao_reflexo(lancamento_id)
            return
        movimentacao = MovimentacaoMensal(
            ano=lanc.ano,
            mes=lanc.mes,
            conta_id=int(local["conta_vinculada_id"]),
            valor=float(lanc.valor),
            nota=self._nota_reflexo(local.get("nome", ""), lanc.tipo),
            tipo=lanc.tipo,
        )
        self.contas_repository.save_movimentacao_reflexo(
            lancamento_id=lancamento_id, movimentacao=movimentacao
        )

    def _remover_reflexos_local(self, ano: int, local_id: int) -> None:
        """Remove os reflexos de todos os lançamentos de um local/ano."""
        lancs = self.repository.get_lancamentos_local_ano(ano=ano, local_id=local_id)
        for lanc in lancs:
            self.contas_repository.delete_movimentacao_reflexo(lanc["id"])

    def _repropagar_reflexos_local(self, ano: int, local_id: int) -> None:
        """Recria os reflexos de um local/ano após troca de conta ou nome."""
        lancs = self.repository.get_lancamentos_local_ano(ano=ano, local_id=local_id)
        for lanc in lancs:
            self._refletir_em_conta_vinculada(
                self._lancamento_para_reflexo(lanc), lanc["id"]
            )
