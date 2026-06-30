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
    def __init__(self, anos_existentes=None):
        self.movimentacoes = []
        self.anos_existentes = set(anos_existentes or [])

    def save_movimentacao(self, mov, movimentacao_id=None):
        self.movimentacoes.append(mov)
        return len(self.movimentacoes)

    def delete_movimentacao_matching(self, ano, mes, conta_id, valor, nota, tipo=""):
        for m in list(self.movimentacoes):
            if (m.ano, m.mes, m.conta_id, m.valor, m.nota, getattr(m, 'tipo', '')) == (ano, mes, conta_id, valor, nota, tipo):
                self.movimentacoes.remove(m)
                return 1
        return 0

    def ano_existe(self, ano):
        return ano in self.anos_existentes


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


def test_rendimento_reflete_em_conta_vinculada_no_mes_seguinte():
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

    # Rendimentos sao captados no ultimo dia do mes, entao o efeito em
    # caixa fica no MES SEGUINTE.
    esperado_ano, esperado_mes = (hoje.year + 1, 1) if hoje.month == 12 else (hoje.year, hoje.month + 1)

    assert len(contas.movimentacoes) == 1
    mov = contas.movimentacoes[0]
    assert (mov.ano, mov.mes) == (esperado_ano, esperado_mes)
    assert mov.conta_id == 7
    assert mov.valor == 123.45
    assert mov.nota == "Rendimento de Nu Conta"
    assert mov.tipo == "rendimento"


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
    # Ano seguinte existe -> rendimento de dezembro rola para janeiro/ano+1.
    contas = _ContasRepositoryFake(anos_existentes={hoje.year + 1})
    repository = _RendimentosRepositoryFake(locais={
        1: {"id": 1, "nome": "X", "conta_vinculada_id": 7},
    })
    use_cases = RendimentosUseCases(repository, contas_repository=contas)

    use_cases.lancar_lote({
        "ano": hoje.year, "local_id": 1,
        "tipo": "rendimento", "valor": 10.0, "nota": "",
        "mes_inicio": 1,
    })

    esperados = []
    for m in range(hoje.month, 13):
        if m == 12:
            esperados.append((hoje.year + 1, 1))
        else:
            esperados.append((hoje.year, m + 1))
    refletidos = sorted((mov.ano, mov.mes) for mov in contas.movimentacoes)
    assert refletidos == sorted(esperados)


def test_rendimento_em_dezembro_com_ano_seguinte_existente_reflete_em_janeiro():
    """Dezembro -> janeiro do ano seguinte quando o ano ja existe."""
    hoje = date.today()
    ano_rend = hoje.year if hoje.month <= 12 else hoje.year + 1
    contas = _ContasRepositoryFake(anos_existentes={ano_rend + 1})
    repository = _RendimentosRepositoryFake(locais={
        1: {"id": 1, "nome": "Nu Conta", "conta_vinculada_id": 7},
    })
    use_cases = RendimentosUseCases(repository, contas_repository=contas)

    use_cases.lancar({
        "ano": ano_rend, "mes": 12, "local_id": 1,
        "tipo": "rendimento", "valor": 50.0, "nota": "",
    })

    assert len(contas.movimentacoes) == 1
    mov = contas.movimentacoes[0]
    assert (mov.ano, mov.mes) == (ano_rend + 1, 1)
    assert mov.tipo == "rendimento"


def test_rendimento_em_dezembro_sem_ano_seguinte_fica_em_dezembro():
    """Quando o ano seguinte ainda nao existe, dezembro reflete no proprio dezembro."""
    hoje = date.today()
    ano_rend = hoje.year if hoje.month <= 12 else hoje.year + 1
    contas = _ContasRepositoryFake(anos_existentes=set())  # ano+1 NAO existe
    repository = _RendimentosRepositoryFake(locais={
        1: {"id": 1, "nome": "Nu Conta", "conta_vinculada_id": 7},
    })
    use_cases = RendimentosUseCases(repository, contas_repository=contas)

    lid = use_cases.lancar({
        "ano": ano_rend, "mes": 12, "local_id": 1,
        "tipo": "rendimento", "valor": 50.0, "nota": "",
    })

    assert len(contas.movimentacoes) == 1
    mov = contas.movimentacoes[0]
    assert (mov.ano, mov.mes) == (ano_rend, 12)
    assert mov.tipo == "rendimento"

    # Cascata reversa tambem deve usar o mesmo destino (dezembro/mesmo ano).
    use_cases.excluir_lancamento(lid)
    assert contas.movimentacoes == []


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
    assert contas.movimentacoes[0].tipo == "rendimento"

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
        valor=mov.valor, nota="Editado pelo usuário", tipo=mov.tipo,
    )

    use_cases.excluir_lancamento(lid)
    assert len(contas.movimentacoes) == 1
    assert contas.movimentacoes[0].nota == "Editado pelo usuário"

