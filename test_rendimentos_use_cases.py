import pytest

from financeiro.application.rendimentos.use_cases import RendimentosUseCases


class _RendimentosRepositoryFake:
    def __init__(self, locais: dict | None = None):
        self.lancamentos = []
        self.locais = locais or {}
        self._lancamentos_by_id = {}

    def add_lancamento(self, lancamento):
        self.lancamentos.append(lancamento)
        lanc_id = len(self.lancamentos)
        self._lancamentos_by_id[lanc_id] = {
            "id": lanc_id,
            "ano": lancamento.ano,
            "mes": lancamento.mes,
            "local_id": lancamento.local_id,
            "tipo": lancamento.tipo,
            "valor": lancamento.valor,
            "nota": lancamento.nota,
        }
        return lanc_id

    def get_local_by_id(self, local_id):
        return self.locais.get(local_id)

    def update_local(self, local_id, nome, conta_vinculada_id=None):
        if local_id in self.locais:
            self.locais[local_id].update({
                "nome": nome,
                "conta_vinculada_id": conta_vinculada_id,
            })

    def get_lancamento_by_id(self, lancamento_id):
        return self._lancamentos_by_id.get(lancamento_id)

    def get_lancamentos_local_ano(self, ano, local_id):
        return [
            dict(l)
            for l in self._lancamentos_by_id.values()
            if l["ano"] == ano and l["local_id"] == local_id
        ]

    def get_lancamentos_local(self, local_id):
        return [
            dict(l)
            for l in self._lancamentos_by_id.values()
            if l["local_id"] == local_id
        ]

    def delete_lancamento(self, lancamento_id):
        self._lancamentos_by_id.pop(lancamento_id, None)

    def delete_lancamentos_local_ano(self, ano, local_id):
        for lanc_id in [
            i for i, l in self._lancamentos_by_id.items()
            if l["ano"] == ano and l["local_id"] == local_id
        ]:
            self._lancamentos_by_id.pop(lanc_id, None)

    def delete_local(self, local_id):
        for lanc_id in [
            i for i, l in self._lancamentos_by_id.items()
            if l["local_id"] == local_id
        ]:
            self._lancamentos_by_id.pop(lanc_id, None)
        self.locais.pop(local_id, None)

    def update_lancamento(self, lancamento_id, tipo, valor, nota):
        if lancamento_id in self._lancamentos_by_id:
            self._lancamentos_by_id[lancamento_id].update({
                "tipo": tipo, "valor": valor, "nota": nota,
            })


def test_lancar_rendimento_negativo():
    repository = _RendimentosRepositoryFake()
    use_cases = RendimentosUseCases(repository)

    lancamento_id = use_cases.lancar({
        "ano": 2026,
        "mes": 3,
        "local_id": 1,
        "tipo": "rendimento",
        "valor": -25.50,
        "nota": "Rendimento negativo",
    })

    assert lancamento_id == 1
    assert repository.lancamentos[0].tipo == "rendimento"
    assert repository.lancamentos[0].valor == -25.50


def test_aporte_negativo_vira_saque():
    repository = _RendimentosRepositoryFake()
    use_cases = RendimentosUseCases(repository)

    use_cases.lancar({
        "ano": 2026,
        "mes": 8,
        "local_id": 13,
        "tipo": "aporte",
        "valor": -750,
        "nota": "",
    })

    lanc = repository.lancamentos[0]
    assert lanc.tipo == "saque"
    assert lanc.valor == 750


def test_saque_negativo_normaliza_para_positivo():
    repository = _RendimentosRepositoryFake()
    use_cases = RendimentosUseCases(repository)

    use_cases.lancar({
        "ano": 2026,
        "mes": 8,
        "local_id": 13,
        "tipo": "saque",
        "valor": -2700,
        "nota": "",
    })

    lanc = repository.lancamentos[0]
    assert lanc.tipo == "saque"
    assert lanc.valor == 2700


def test_saque_zero_rejeitado():
    repository = _RendimentosRepositoryFake()
    use_cases = RendimentosUseCases(repository)

    with pytest.raises(ValueError, match="Saque deve ter valor diferente de zero"):
        use_cases.lancar({
            "ano": 2026,
            "mes": 8,
            "local_id": 13,
            "tipo": "saque",
            "valor": 0,
            "nota": "sem valor",
        })


def test_editar_lancamento_tambem_normaliza_sinais():
    repository = _RendimentosRepositoryFake()
    use_cases = RendimentosUseCases(repository)

    lanc_id = use_cases.lancar({
        "ano": 2026, "mes": 8, "local_id": 13,
        "tipo": "aporte", "valor": 100, "nota": "",
    })
    use_cases.editar_lancamento(lanc_id, {"tipo": "aporte", "valor": -50, "nota": ""})

    lanc = repository._lancamentos_by_id[lanc_id]
    assert lanc["tipo"] == "saque"
    assert lanc["valor"] == 50


def test_criar_local_aceita_conta_vinculada_id():
    captured = {}

    class _Repo:
        def add_local(self, local):
            captured["local"] = local
            return 99

    use_cases = RendimentosUseCases(_Repo())
    rid = use_cases.criar_local({"ano": 2026, "nome": "X", "conta_vinculada_id": 5})

    assert rid == 99
    assert captured["local"].conta_vinculada_id == 5


def test_editar_local_normaliza_conta_vazia_para_none():
    captured = {}

    class _Repo:
        def get_local_by_id(self, local_id):
            return None

        def update_local(self, local_id, nome, conta_vinculada_id=None):
            captured["args"] = (local_id, nome, conta_vinculada_id)

    use_cases = RendimentosUseCases(_Repo())
    use_cases.editar_local(1, {"nome": "X", "conta_vinculada_id": ""})
    assert captured["args"] == (1, "X", None)


# ---------------------------------------------------------------------------
# Reflexo automático na conta vinculada
# ---------------------------------------------------------------------------


class _ContasRepositoryFake:
    def __init__(self):
        self.movimentacoes = {}  # lancamento_id -> dict

    def save_movimentacao_reflexo(self, lancamento_id, movimentacao):
        self.movimentacoes[lancamento_id] = {
            "ano": movimentacao.ano,
            "mes": movimentacao.mes,
            "conta_id": movimentacao.conta_id,
            "valor": movimentacao.valor,
            "nota": movimentacao.nota,
            "tipo": movimentacao.tipo,
        }
        return lancamento_id

    def delete_movimentacao_reflexo(self, lancamento_id):
        self.movimentacoes.pop(lancamento_id, None)


def _use_cases_com_reflexo(locais=None):
    repo = _RendimentosRepositoryFake(
        locais=locais
        or {
            1: {"id": 1, "ano": 2026, "nome": "CDB", "conta_vinculada_id": 7},
            2: {"id": 2, "ano": 2026, "nome": "Sem conta", "conta_vinculada_id": None},
        }
    )
    contas = _ContasRepositoryFake()
    return RendimentosUseCases(repo, contas_repository=contas), repo, contas


def test_aporte_reflete_como_credito_na_conta_vinculada():
    use_cases, repo, contas = _use_cases_com_reflexo()

    lanc_id = use_cases.lancar({
        "ano": 2026, "mes": 3, "local_id": 1,
        "tipo": "aporte", "valor": 500, "nota": "",
    })

    mov = contas.movimentacoes[lanc_id]
    assert mov["conta_id"] == 7
    assert mov["valor"] == 500
    assert mov["mes"] == 3
    assert mov["tipo"] == "aporte"
    assert mov["nota"] == "Aporte em CDB"


def test_rendimento_reflete_como_credito_no_mesmo_mes():
    use_cases, repo, contas = _use_cases_com_reflexo()

    lanc_id = use_cases.lancar({
        "ano": 2026, "mes": 3, "local_id": 1,
        "tipo": "rendimento", "valor": 125.50, "nota": "",
    })

    mov = contas.movimentacoes[lanc_id]
    assert mov["conta_id"] == 7
    assert mov["valor"] == 125.50
    assert mov["mes"] == 3
    assert mov["tipo"] == "rendimento"
    assert mov["nota"] == "Rendimento de CDB"


def test_saque_nao_reflete_na_conta_vinculada():
    """Visão B: saque/resgate é conversão interna — o dinheiro já está
    contabilizado na conta (patrimônio total), então não gera reflexo."""
    use_cases, repo, contas = _use_cases_com_reflexo()

    lanc_id = use_cases.lancar({
        "ano": 2026, "mes": 5, "local_id": 1,
        "tipo": "saque", "valor": 2700, "nota": "",
    })

    assert lanc_id not in contas.movimentacoes


def test_local_sem_conta_vinculada_nao_reflete():
    use_cases, repo, contas = _use_cases_com_reflexo()

    lanc_id = use_cases.lancar({
        "ano": 2026, "mes": 3, "local_id": 2,
        "tipo": "aporte", "valor": 500, "nota": "",
    })

    assert lanc_id not in contas.movimentacoes


def test_projecao_nao_reflete_na_conta():
    use_cases, repo, contas = _use_cases_com_reflexo()

    lanc_id = use_cases.lancar({
        "ano": 2026, "mes": 3, "local_id": 1,
        "tipo": "rendimento", "valor": 999, "nota": "Projeção",
    })

    assert lanc_id not in contas.movimentacoes


def test_editar_lancamento_atualiza_reflexo():
    use_cases, repo, contas = _use_cases_com_reflexo()

    lanc_id = use_cases.lancar({
        "ano": 2026, "mes": 3, "local_id": 1,
        "tipo": "aporte", "valor": 500, "nota": "",
    })
    use_cases.editar_lancamento(lanc_id, {
        "tipo": "rendimento", "valor": 50, "nota": "",
    })

    mov = contas.movimentacoes[lanc_id]
    assert mov["valor"] == 50
    assert mov["tipo"] == "rendimento"
    assert mov["nota"] == "Rendimento de CDB"


def test_editar_lancamento_para_projecao_remove_reflexo():
    use_cases, repo, contas = _use_cases_com_reflexo()

    lanc_id = use_cases.lancar({
        "ano": 2026, "mes": 3, "local_id": 1,
        "tipo": "rendimento", "valor": 50, "nota": "",
    })
    use_cases.editar_lancamento(lanc_id, {
        "tipo": "rendimento", "valor": 50, "nota": "Projeção",
    })

    assert lanc_id not in contas.movimentacoes


def test_excluir_lancamento_remove_reflexo():
    use_cases, repo, contas = _use_cases_com_reflexo()

    lanc_id = use_cases.lancar({
        "ano": 2026, "mes": 3, "local_id": 1,
        "tipo": "aporte", "valor": 500, "nota": "",
    })
    assert lanc_id in contas.movimentacoes

    use_cases.excluir_lancamento(lanc_id)
    assert lanc_id not in contas.movimentacoes


def test_lancar_lote_reflete_cada_mes():
    use_cases, repo, contas = _use_cases_com_reflexo()

    use_cases.lancar_lote({
        "ano": 2026, "local_id": 1, "mes_inicio": 3,
        "tipo": "aporte", "valor": 100, "nota": "",
    })

    assert len(contas.movimentacoes) == 10  # meses 3..12
    for lanc_id, mov in contas.movimentacoes.items():
        assert mov["valor"] == 100
        assert mov["tipo"] == "aporte"


def test_excluir_lancamentos_local_ano_remove_reflexos():
    use_cases, repo, contas = _use_cases_com_reflexo()

    use_cases.lancar({
        "ano": 2026, "mes": 3, "local_id": 1,
        "tipo": "aporte", "valor": 100, "nota": "",
    })
    use_cases.lancar({
        "ano": 2026, "mes": 4, "local_id": 1,
        "tipo": "rendimento", "valor": 10, "nota": "",
    })
    assert len(contas.movimentacoes) == 2

    use_cases.excluir_lancamentos_local_ano(ano=2026, local_id=1)
    assert contas.movimentacoes == {}


def test_excluir_local_remove_reflexos():
    use_cases, repo, contas = _use_cases_com_reflexo()

    use_cases.lancar({
        "ano": 2026, "mes": 3, "local_id": 1,
        "tipo": "aporte", "valor": 100, "nota": "",
    })
    assert len(contas.movimentacoes) == 1

    use_cases.excluir_local(1)
    assert contas.movimentacoes == {}


def test_trocar_conta_do_local_repropaga_reflexos():
    repo = _RendimentosRepositoryFake(
        locais={
            1: {"id": 1, "ano": 2026, "nome": "CDB", "conta_vinculada_id": 7},
        }
    )
    contas = _ContasRepositoryFake()
    use_cases = RendimentosUseCases(repo, contas_repository=contas)

    use_cases.lancar({
        "ano": 2026, "mes": 3, "local_id": 1,
        "tipo": "aporte", "valor": 100, "nota": "",
    })
    assert contas.movimentacoes[1]["conta_id"] == 7

    repo.locais[1]["conta_vinculada_id"] = 9
    use_cases.editar_local(1, {"nome": "CDB", "conta_vinculada_id": 9})

    assert contas.movimentacoes[1]["conta_id"] == 9
    assert contas.movimentacoes[1]["valor"] == 100


def test_aporte_negativo_vira_saque_e_nao_reflete():
    use_cases, repo, contas = _use_cases_com_reflexo()

    lanc_id = use_cases.lancar({
        "ano": 2026, "mes": 8, "local_id": 1,
        "tipo": "aporte", "valor": -750, "nota": "",
    })

    lanc = repo.lancamentos[0]
    assert lanc.tipo == "saque"
    assert lanc.valor == 750
    # Visão B: saque não gera reflexo na conta.
    assert lanc_id not in contas.movimentacoes


# ============================================================================
# REGRESSÃO — bugs da caçada (BUG-6, BUG-7, BUG-9, BUG-10, BUG-16)
# ============================================================================

def test_bug6_lote_rejeita_mes_inicio_invalido():
    repository = _RendimentosRepositoryFake()
    use_cases = RendimentosUseCases(repository)

    for mes_inicio in (0, -1, 13):
        with pytest.raises(ValueError, match="mes_inicio"):
            use_cases.lancar_lote({
                "ano": 2026, "local_id": 1, "tipo": "aporte",
                "valor": 100, "nota": "", "mes_inicio": mes_inicio,
            })
    assert repository.lancamentos == []


def test_bug7_nan_inf_rejeitados():
    repository = _RendimentosRepositoryFake()
    use_cases = RendimentosUseCases(repository)

    for valor in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finito"):
            use_cases.lancar({
                "ano": 2026, "mes": 3, "local_id": 1,
                "tipo": "aporte", "valor": valor, "nota": "",
            })
    assert repository.lancamentos == []


def test_bug9_excluir_local_remove_reflexos_de_todos_os_anos():
    repo = _RendimentosRepositoryFake(
        locais={1: {"id": 1, "ano": 2026, "nome": "CDB", "conta_vinculada_id": 7}}
    )
    contas = _ContasRepositoryFake()
    use_cases = RendimentosUseCases(repo, contas_repository=contas)

    # Lançamentos do mesmo local em anos diferentes
    use_cases.lancar({"ano": 2026, "mes": 3, "local_id": 1, "tipo": "aporte", "valor": 100, "nota": ""})
    use_cases.lancar({"ano": 2027, "mes": 3, "local_id": 1, "tipo": "aporte", "valor": 50, "nota": ""})
    assert len(contas.movimentacoes) == 2

    use_cases.excluir_local(1)
    assert contas.movimentacoes == {}, "Reflexos de TODOS os anos deveriam ser removidos"


def test_bug10_rollback_compensatorio_quando_reflexo_falha():
    class _RepoFalhaReflexo(_RendimentosRepositoryFake):
        pass

    class _ContasFalha:
        def save_movimentacao_reflexo(self, lancamento_id, movimentacao):
            raise RuntimeError("falha no reflexo")

        def delete_movimentacao_reflexo(self, lancamento_id):
            pass

    repo = _RepoFalhaReflexo(
        locais={1: {"id": 1, "ano": 2026, "nome": "CDB", "conta_vinculada_id": 7}}
    )
    use_cases = RendimentosUseCases(repo, contas_repository=_ContasFalha())

    with pytest.raises(RuntimeError):
        use_cases.lancar({"ano": 2026, "mes": 3, "local_id": 1, "tipo": "aporte", "valor": 100, "nota": ""})

    assert repo._lancamentos_by_id == {}, "Lançamento deveria ser removido no rollback compensatório"


def test_bug16_reorder_rejeita_locais_de_anos_diferentes():
    repo = _RendimentosRepositoryFake(
        locais={
            1: {"id": 1, "ano": 2026, "nome": "A", "conta_vinculada_id": None},
            2: {"id": 2, "ano": 2027, "nome": "B", "conta_vinculada_id": None},
        }
    )
    use_cases = RendimentosUseCases(repo)

    with pytest.raises(ValueError, match="mesmo ano"):
        use_cases.reordenar_locais({"ordem_ids": [1, 2]})
