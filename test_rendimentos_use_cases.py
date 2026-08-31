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

    def get_lancamento_by_id(self, lancamento_id):
        return self._lancamentos_by_id.get(lancamento_id)

    def delete_lancamento(self, lancamento_id):
        self._lancamentos_by_id.pop(lancamento_id, None)

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
        def update_local(self, local_id, nome, conta_vinculada_id=None):
            captured["args"] = (local_id, nome, conta_vinculada_id)

    use_cases = RendimentosUseCases(_Repo())
    use_cases.editar_local(1, {"nome": "X", "conta_vinculada_id": ""})
    assert captured["args"] == (1, "X", None)
