from datetime import date

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


class _ContasRepositoryFake:
    def __init__(self):
        self.movimentacoes = []

    def save_movimentacao(self, mov, movimentacao_id=None):
        self.movimentacoes.append(mov)
        return len(self.movimentacoes)

    def delete_movimentacao_matching(self, ano, mes, conta_id, valor, nota):
        for m in list(self.movimentacoes):
            if (m.ano, m.mes, m.conta_id, m.valor, m.nota) == (ano, mes, conta_id, valor, nota):
                self.movimentacoes.remove(m)
                return 1
        return 0


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


def _futuro():
    hoje = date.today()
    ano = hoje.year + 1 if hoje.month == 12 else hoje.year
    mes = 1 if hoje.month == 12 else hoje.month + 1
    return ano, mes


def _passado():
    hoje = date.today()
    ano = hoje.year - 1 if hoje.month == 1 else hoje.year
    mes = 12 if hoje.month == 1 else hoje.month - 1
    return ano, mes


def test_rendimento_reflete_em_conta_vinculada_no_mes_corrente_ou_futuro():
    hoje = date.today()
    contas = _ContasRepositoryFake()
    repository = _RendimentosRepositoryFake(locais={
        1: {"id": 1, "nome": "Nu Conta", "conta_vinculada_id": 7},
    })
    use_cases = RendimentosUseCases(repository, contas_repository=contas)

    use_cases.lancar({
        "ano": hoje.year, "mes": hoje.month, "local_id": 1,
        "tipo": "rendimento", "valor": 123.45, "nota": "",
    })

    assert len(contas.movimentacoes) == 1
    mov = contas.movimentacoes[0]
    assert mov.conta_id == 7
    assert mov.valor == 123.45
    assert mov.nota == "Rendimento de Nu Conta"


def test_rendimento_no_passado_nao_reflete():
    contas = _ContasRepositoryFake()
    repository = _RendimentosRepositoryFake(locais={
        1: {"id": 1, "nome": "X", "conta_vinculada_id": 7},
    })
    use_cases = RendimentosUseCases(repository, contas_repository=contas)
    ano, mes = _passado()

    use_cases.lancar({
        "ano": ano, "mes": mes, "local_id": 1,
        "tipo": "rendimento", "valor": 100.0, "nota": "",
    })

    assert contas.movimentacoes == []


def test_projecao_aporte_e_saque_nao_refletem():
    contas = _ContasRepositoryFake()
    repository = _RendimentosRepositoryFake(locais={
        1: {"id": 1, "nome": "X", "conta_vinculada_id": 7},
    })
    use_cases = RendimentosUseCases(repository, contas_repository=contas)
    ano, mes = _futuro()

    use_cases.lancar({"ano": ano, "mes": mes, "local_id": 1,
                      "tipo": "rendimento", "valor": 50.0, "nota": "Projeção"})
    use_cases.lancar({"ano": ano, "mes": mes, "local_id": 1,
                      "tipo": "aporte", "valor": 200.0, "nota": ""})
    use_cases.lancar({"ano": ano, "mes": mes, "local_id": 1,
                      "tipo": "saque", "valor": 30.0, "nota": ""})

    assert contas.movimentacoes == []


def test_rendimento_sem_conta_vinculada_nao_reflete():
    contas = _ContasRepositoryFake()
    repository = _RendimentosRepositoryFake(locais={
        1: {"id": 1, "nome": "X", "conta_vinculada_id": None},
    })
    use_cases = RendimentosUseCases(repository, contas_repository=contas)
    ano, mes = _futuro()

    use_cases.lancar({"ano": ano, "mes": mes, "local_id": 1,
                      "tipo": "rendimento", "valor": 50.0, "nota": ""})

    assert contas.movimentacoes == []


def test_lancar_lote_filtra_meses_passados():
    hoje = date.today()
    contas = _ContasRepositoryFake()
    repository = _RendimentosRepositoryFake(locais={
        1: {"id": 1, "nome": "X", "conta_vinculada_id": 7},
    })
    use_cases = RendimentosUseCases(repository, contas_repository=contas)

    use_cases.lancar_lote({
        "ano": hoje.year, "local_id": 1,
        "tipo": "rendimento", "valor": 10.0, "nota": "",
        "mes_inicio": 1,
    })

    meses_refletidos = sorted(m.mes for m in contas.movimentacoes)
    assert meses_refletidos == list(range(hoje.month, 13))


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


def test_excluir_rendimento_remove_reflexo_quando_match_exato():
    hoje = date.today()
    contas = _ContasRepositoryFake()
    repository = _RendimentosRepositoryFake(locais={
        1: {"id": 1, "nome": "Nu Conta", "conta_vinculada_id": 7},
    })
    use_cases = RendimentosUseCases(repository, contas_repository=contas)

    lid = use_cases.lancar({"ano": hoje.year, "mes": hoje.month, "local_id": 1,
                            "tipo": "rendimento", "valor": 100.0, "nota": ""})
    assert len(contas.movimentacoes) == 1

    use_cases.excluir_lancamento(lid)
    assert contas.movimentacoes == []


def test_excluir_rendimento_nao_remove_se_movimentacao_foi_editada():
    hoje = date.today()
    contas = _ContasRepositoryFake()
    repository = _RendimentosRepositoryFake(locais={
        1: {"id": 1, "nome": "Nu Conta", "conta_vinculada_id": 7},
    })
    use_cases = RendimentosUseCases(repository, contas_repository=contas)

    lid = use_cases.lancar({"ano": hoje.year, "mes": hoje.month, "local_id": 1,
                            "tipo": "rendimento", "valor": 100.0, "nota": ""})
    # Usuário editou a nota da movimentação manualmente.
    mov = contas.movimentacoes[0]
    contas.movimentacoes[0] = type(mov)(
        ano=mov.ano, mes=mov.mes, conta_id=mov.conta_id,
        valor=mov.valor, nota="Editado pelo usuário",
    )

    use_cases.excluir_lancamento(lid)
    assert len(contas.movimentacoes) == 1
    assert contas.movimentacoes[0].nota == "Editado pelo usuário"

