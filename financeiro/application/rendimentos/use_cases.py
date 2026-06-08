from datetime import date

from financeiro.domain.contas.entities import MovimentacaoMensal
from financeiro.domain.rendimentos.entities import RendimentoLancamento, RendimentoLocal


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
        self.repository.update_local(
            local_id=local_id,
            nome=nome,
            conta_vinculada_id=conta_vinculada_id,
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
        lancamento_id = self.repository.add_lancamento(lanc)
        self._refletir_em_conta_vinculada(lanc)
        return lancamento_id

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
            self._refletir_em_conta_vinculada(lanc)

    @staticmethod
    def _nota_reflexo(local_nome: str) -> str:
        return f"Rendimento de {local_nome or ''}".strip()

    def _local_para_reflexo(self, lanc_tipo: str, lanc_nota: str, lanc_valor: float, local_id: int):
        """
        Retorna o dict do local quando o lançamento atende aos critérios
        de reflexo na conta corrente; caso contrário, None.
        Centraliza a regra para evitar divergência entre criar e excluir.
        """
        if self.contas_repository is None:
            return None
        if lanc_tipo != "rendimento":
            return None
        if (lanc_nota or "").strip() == "Projeção":
            return None
        if lanc_valor == 0:
            return None
        local = self.repository.get_local_by_id(local_id)
        if not local or not local.get("conta_vinculada_id"):
            return None
        return local

    def _refletir_em_conta_vinculada(self, lanc: RendimentoLancamento) -> None:
        """
        Cria um lançamento comum em movimentacoes_mensais quando os
        critérios em `_local_para_reflexo` são satisfeitos E o mês é
        o corrente ou futuro. Lançamentos passados não são refletidos.
        """
        local = self._local_para_reflexo(lanc.tipo, lanc.nota, lanc.valor, lanc.local_id)
        if not local:
            return

        hoje = date.today()
        if (lanc.ano, lanc.mes) < (hoje.year, hoje.month):
            return

        movimentacao = MovimentacaoMensal(
            ano=lanc.ano,
            mes=lanc.mes,
            conta_id=int(local["conta_vinculada_id"]),
            valor=float(lanc.valor),
            nota=self._nota_reflexo(local.get("nome", "")),
        )
        self.contas_repository.save_movimentacao(movimentacao)

    def editar_lancamento(self, lancamento_id: int, payload: dict) -> None:
        tipo, valor, nota = self._validar_payload_lancamento(payload)
        # Antes de alterar, tenta remover o reflexo do estado anterior; o novo
        # estado, se ainda elegível, gera nova movimentação (não há vínculo,
        # então não há "update" — é remove+add para manter consistência).
        original = self.repository.get_lancamento_by_id(lancamento_id)
        if original:
            self._remover_reflexo_se_existir(original)
        self.repository.update_lancamento(lancamento_id, tipo, valor, nota)
        if original:
            atualizado = RendimentoLancamento(
                ano=int(original["ano"]),
                mes=int(original["mes"]),
                local_id=int(original["local_id"]),
                tipo=tipo,
                valor=valor,
                nota=nota,
            )
            self._refletir_em_conta_vinculada(atualizado)

    def excluir_lancamento(self, lancamento_id: int) -> None:
        original = self.repository.get_lancamento_by_id(lancamento_id)
        self.repository.delete_lancamento(lancamento_id)
        if original:
            self._remover_reflexo_se_existir(original)

    def _remover_reflexo_se_existir(self, lanc_dict: dict) -> None:
        """
        Reverte o reflexo criado pelo gatilho de _refletir_em_conta_vinculada,
        casando exatamente (ano, mes, conta_id, valor, nota="Rendimento de {nome}").
        Se o usuário editou a movimentação na conta, o match falha e ela
        permanece — consistente com "remover manualmente".
        """
        local = self._local_para_reflexo(
            lanc_dict.get("tipo", ""),
            lanc_dict.get("nota", ""),
            float(lanc_dict.get("valor") or 0),
            int(lanc_dict["local_id"]),
        )
        if not local:
            return
        self.contas_repository.delete_movimentacao_matching(
            ano=int(lanc_dict["ano"]),
            mes=int(lanc_dict["mes"]),
            conta_id=int(local["conta_vinculada_id"]),
            valor=float(lanc_dict["valor"]),
            nota=self._nota_reflexo(local.get("nome", "")),
        )

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
