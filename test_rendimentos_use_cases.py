from financeiro.application.rendimentos.use_cases import RendimentosUseCases


class _RendimentosRepositoryFake:
    def __init__(self):
        self.lancamentos = []

    def add_lancamento(self, lancamento):
        self.lancamentos.append(lancamento)
        return len(self.lancamentos)


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
