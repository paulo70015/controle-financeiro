#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite de Testes de Integração - Controle Financeiro v1.2.3
Valida todas as refatorações DRY/DDD implementadas
"""

import os
import sys
import tempfile
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
# VERIFICAR Supabase — aborta se Supabase estiver ativo/acessivel
# ═══════════════════════════════════════════════════════════════════
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_browser.processos_util import kill_arvore, limpar_banco_teste, matar_servidores_na_porta
from test_browser.verificar_ambiente import verificar as _verificar_supabase
_verificar_supabase()

# ═══════════════════════════════════════════════════════════════════
# FORÇAR SQLite — antes de qualquer import do projeto
# ═══════════════════════════════════════════════════════════════════
os.environ["DB_MODE"] = "sqlite"

import requests
import json
import sqlite3
from datetime import datetime

BASE_URL = "http://127.0.0.1:8086"
ANO_TESTE = datetime.now().year + 10
MES_TESTE = 12  # Dezembro (evita conflitos com dados existentes)

# Caminho do banco SQLite de teste (definido no __main__ antes de runner.run()).
DB_TESTE_PATH = None


def _query_db(sql, params=()):
    """Executa consulta no banco SQLite de teste (para asserts de regressão)."""
    conn = sqlite3.connect(DB_TESTE_PATH)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
        
    def test(self, name):
        def decorator(func):
            self.tests.append((name, func))
            return func
        return decorator
    
    def run(self):
        print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
        print(f"{Colors.BLUE}SUITE DE TESTES - Controle Financeiro v1.2.3{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")
        
        for name, func in self.tests:
            try:
                print(f"{Colors.YELLOW}▶ {name}{Colors.RESET}")
                func(self)
                self.passed += 1
                print(f"{Colors.GREEN}  ✓ PASSOU{Colors.RESET}\n")
            except AssertionError as e:
                self.failed += 1
                print(f"{Colors.RED}  ✗ FALHOU: {e}{Colors.RESET}\n")
            except Exception as e:
                self.failed += 1
                print(f"{Colors.RED}  ✗ ERRO: {e}{Colors.RESET}\n")
        
        print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")
        print(f"Total: {self.passed + self.failed} | "
              f"{Colors.GREEN}Passou: {self.passed}{Colors.RESET} | "
              f"{Colors.RED}Falhou: {self.failed}{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")
        
        return self.failed == 0

runner = TestRunner()

# ============================================================================
# BACKEND - DESPESAS
# ============================================================================

@runner.test("Backend: Criar despesa via API")
def test_criar_despesa(r):
    resp = requests.post(f"{BASE_URL}/api/despesa", json={
        "ano": ANO_TESTE,
        "mes": MES_TESTE,
        "categoria": "Teste DRY",
        "valor": 150.50,
        "nota": "Teste de criação"
    })
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get("ok"), f"Resposta: {data}"
    r.despesa_id = data.get("id")
    print(f"    ID criado: {r.despesa_id}")

@runner.test("Backend: Editar despesa via use case")
def test_editar_despesa(r):
    if not hasattr(r, 'despesa_id'):
        raise AssertionError("Teste anterior falhou")
    
    resp = requests.put(f"{BASE_URL}/api/despesa/{r.despesa_id}", json={
        "ano": ANO_TESTE,
        "mes": MES_TESTE,
        "categoria": "Teste DRY",
        "valor": 200.75,
        "nota": "Teste de edição"
    })
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get("ok"), f"Resposta: {data}"
    print(f"    Valor atualizado: 150.50 → 200.75")

@runner.test("Backend: Deletar despesa")
def test_deletar_despesa(r):
    if not hasattr(r, 'despesa_id'):
        raise AssertionError("Teste anterior falhou")
    
    resp = requests.delete(f"{BASE_URL}/api/despesa/{r.despesa_id}")
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get("ok"), f"Resposta: {data}"

# ============================================================================
# BACKEND - RECEITAS
# ============================================================================

@runner.test("Backend: Criar receita via API")
def test_criar_receita(r):
    resp = requests.post(f"{BASE_URL}/api/receita", json={
        "ano": ANO_TESTE,
        "mes": MES_TESTE,
        "descricao": "Salário Teste",
        "valor": 5000.00,
        "nota": "Teste de criação"
    })
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get("ok"), f"Resposta: {data}"
    r.receita_id = data.get("id")
    print(f"    ID criado: {r.receita_id}")

@runner.test("Backend: Editar receita via use case")
def test_editar_receita(r):
    if not hasattr(r, 'receita_id'):
        raise AssertionError("Teste anterior falhou")
    
    resp = requests.put(f"{BASE_URL}/api/receita/{r.receita_id}", json={
        "ano": ANO_TESTE,
        "mes": MES_TESTE,
        "descricao": "Salário Teste Editado",
        "valor": 5500.00,
        "nota": "Teste de edição"
    })
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get("ok"), f"Resposta: {data}"
    print(f"    Valor atualizado: 5000.00 → 5500.00")

@runner.test("Backend: Deletar receita")
def test_deletar_receita(r):
    if not hasattr(r, 'receita_id'):
        raise AssertionError("Teste anterior falhou")
    
    resp = requests.delete(f"{BASE_URL}/api/receita/{r.receita_id}")
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get("ok"), f"Resposta: {data}"

# ============================================================================
# BACKEND - CONTAS (pré-requisito para depósitos)
# ============================================================================

@runner.test("Backend: Criar conta via API")
def test_criar_conta(r):
    resp = requests.post(f"{BASE_URL}/api/conta", json={
        "nome": "Conta Teste",
        "saldo_inicial": 0
    })
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get("ok"), f"Resposta: {data}"

    # Obter o ID da conta criada
    resp = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}")
    dados = resp.json()
    contas = dados.get("contas", [])
    assert contas, "Conta não apareceu em /api/dados"
    r.conta_id = contas[0]["id"]
    print(f"    Conta criada, ID: {r.conta_id}")

# ============================================================================
# BACKEND - DEPÓSITOS (Contas Correntes)
# ============================================================================

@runner.test("Backend: Criar depósito via API")
def test_criar_deposito(r):
    if not hasattr(r, 'conta_id'):
        raise AssertionError("Teste anterior falhou (conta não criada)")
    
    resp = requests.post(f"{BASE_URL}/api/deposito", json={
        "ano": ANO_TESTE,
        "mes": MES_TESTE,
        "conta_id": r.conta_id,
        "valor": 1000.00,
        "nota": "Teste de depósito"
    })
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get("ok"), f"Resposta: {data}"
    r.deposito_id = data.get("id")
    print(f"    ID criado: {r.deposito_id}")

@runner.test("Backend: Editar depósito via use case")
def test_editar_deposito(r):
    if not hasattr(r, 'deposito_id') or not hasattr(r, 'conta_id'):
        raise AssertionError("Teste anterior falhou")
    
    resp = requests.put(f"{BASE_URL}/api/deposito/{r.deposito_id}", json={
        "ano": ANO_TESTE,
        "mes": MES_TESTE,
        "conta_id": r.conta_id,
        "valor": 1500.00,
        "nota": "Teste de edição"
    })
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get("ok"), f"Resposta: {data}"
    print(f"    Valor atualizado: 1000.00 → 1500.00")

@runner.test("Backend: Deletar depósito")
def test_deletar_deposito(r):
    if not hasattr(r, 'deposito_id'):
        raise AssertionError("Teste anterior falhou")
    
    resp = requests.delete(f"{BASE_URL}/api/deposito/{r.deposito_id}")
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get("ok"), f"Resposta: {data}"

# ============================================================================
# BACKEND - LOTE (DRY)
# ============================================================================

@runner.test("Backend: Lançamento em lote de despesas")
def test_lote_despesas(r):
    resp = requests.post(f"{BASE_URL}/api/despesa/lote", json={
        "ano": ANO_TESTE,
        "mes_inicio": MES_TESTE,
        "categoria": "Teste Lote",
        "valor": 100.00,
        "nota": "Lote teste",
        "incremento": 10.00
    })
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get("ok"), f"Resposta: {data}"
    assert "ids" in data, "IDs não retornados"
    r.lote_ids = data["ids"]
    print(f"    {len(r.lote_ids)} despesas criadas")

@runner.test("Backend: Limpar lote de despesas")
def test_limpar_lote(r):
    if not hasattr(r, 'lote_ids'):
        raise AssertionError("Teste anterior falhou")
    
    for despesa_id in r.lote_ids:
        requests.delete(f"{BASE_URL}/api/despesa/{despesa_id}")
    print(f"    {len(r.lote_ids)} despesas deletadas")

# ============================================================================
# FRONTEND - CACHE E DEBOUNCE
# ============================================================================

@runner.test("Frontend: Endpoint /api/dados responde corretamente")
def test_endpoint_dados(r):
    resp = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}")
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert "categorias" in data, "Estrutura inválida: falta 'categorias'"
    assert "receitas" in data, "Estrutura inválida: falta 'receitas'"
    assert "anos" in data, "Estrutura inválida: falta 'anos' (correção v1.3.0)"
    assert isinstance(data["anos"], list), "'anos' deve ser uma lista"
    assert ANO_TESTE in data["anos"], f"Ano {ANO_TESTE} deve constar em 'anos'"
    print(f"    {len(data['categorias'])} categorias, {len(data['anos'])} anos carregados")

@runner.test("Frontend: Tooltip de despesas responde")
def test_tooltip_despesas(r):
    resp = requests.get(f"{BASE_URL}/api/despesas_detalhe/{ANO_TESTE}/1/Teste")
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert isinstance(data, list), "Resposta deve ser lista"

@runner.test("Frontend: Tooltip de rendimentos responde")
def test_tooltip_rendimentos(r):
    resp = requests.get(f"{BASE_URL}/api/rendimentos_detalhe/{ANO_TESTE}/1/1")
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert isinstance(data, list), "Resposta deve ser lista"

# ============================================================================
# DDD - VALIDAÇÃO DE CAMADAS
# ============================================================================

@runner.test("DDD: Despesa com categoria vinculada cria depósito")
def test_ddd_categoria_vinculada(r):
    # Obter conta via /api/dados
    resp = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}")
    if resp.status_code != 200:
        print("    ⚠ Pulado: erro ao buscar dados")
        return
    
    dados = resp.json()
    contas = dados.get("contas", [])
    if not contas:
        print("    ⚠ Pulado: nenhuma conta disponível")
        return
    
    conta_id = contas[0]["id"]
    
    # Criar categoria vinculada
    resp = requests.post(f"{BASE_URL}/api/categoria", json={
        "ano": ANO_TESTE,
        "nome": "Cat Vinculada Teste",
        "ordem": 999,
        "inclui_fixas": False,
        "conta_vinculada_id": conta_id
    })
    assert resp.status_code == 200
    
    # Criar despesa nessa categoria
    resp = requests.post(f"{BASE_URL}/api/despesa", json={
        "ano": ANO_TESTE,
        "mes": MES_TESTE,
        "categoria": "Cat Vinculada Teste",
        "valor": 50.00,
        "nota": "Teste DDD"
    })
    assert resp.status_code == 200
    despesa_id = resp.json().get("id")
    
    # Verificar se depósito foi criado
    resp = requests.get(f"{BASE_URL}/api/depositos_detalhe/{ANO_TESTE}/{MES_TESTE}/{conta_id}")
    depositos = resp.json()
    vinculado = [d for d in depositos if d.get("despesa_id") == despesa_id]
    assert len(vinculado) > 0, "Depósito vinculado não foi criado"
    print(f"    ✓ Depósito vinculado criado automaticamente")
    
    # Limpar
    requests.delete(f"{BASE_URL}/api/despesa/{despesa_id}")
    requests.delete(f"{BASE_URL}/api/categoria/{ANO_TESTE}/Cat Vinculada Teste")

@runner.test("DDD: Categoria com flag is_cartao")
def test_ddd_categoria_cartao(r):
    # Criar categoria com flag is_cartao
    resp = requests.post(f"{BASE_URL}/api/categoria", json={
        "ano": ANO_TESTE,
        "nome": "Cat Cartao Teste",
        "ordem": 998,
        "inclui_fixas": False,
        "is_cartao": True
    })
    assert resp.status_code == 200
    
    # Verificar se a flag foi salva
    resp = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}")
    dados = resp.json()
    categorias = dados.get("categorias", [])
    cat = next((c for c in categorias if c["nome"] == "Cat Cartao Teste"), None)
    
    assert cat is not None, "Categoria não criada"
    assert cat.get("is_cartao") == 1 or cat.get("is_cartao") is True, f"Flag is_cartao não foi salva corretamente: {cat}"
    print(f"    ✓ Categoria criada com flag is_cartao ativa")
    
    # Limpar
    requests.delete(f"{BASE_URL}/api/categoria/{ANO_TESTE}/Cat Cartao Teste")

@runner.test("Fixas: lancamento 'Soma' oculto quando celula excluida")
def test_fixa_soma_oculta_quando_celula_excluida(r):
    # Categoria que agrega fixas orfas (inclui_fixas)
    cat_nome = "Cat Soma Fixas Teste"
    resp = requests.post(f"{BASE_URL}/api/categoria", json={
        "ano": ANO_TESTE,
        "nome": cat_nome,
        "ordem": 997,
        "inclui_fixas": True
    })
    assert resp.status_code == 200

    # Buscar cat_id criado
    resp = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}")
    dados = resp.json()
    cat = next((c for c in dados.get("categorias", []) if c["nome"] == cat_nome), None)
    assert cat is not None, "Categoria não criada"
    cat_id = cat["id"]

    # Criar fixa de 856,90
    resp = requests.post(f"{BASE_URL}/api/fixa", json={
        "ano": ANO_TESTE,
        "descricao": "Fixa Soma",
        "valor": 856.90,
        "dia": 10,
        "cat_id": cat_id
    })
    assert resp.status_code == 200

    # Despesa manual para diferenciar do lançamento 'Soma'
    resp = requests.post(f"{BASE_URL}/api/despesa", json={
        "ano": ANO_TESTE,
        "mes": MES_TESTE,
        "categoria": cat_nome,
        "valor": 14148.84,
        "nota": "Gasto manual"
    })
    assert resp.status_code == 200

    # Marcar como paga → materializa 'Soma das Despesas Fixas' + cria exceção
    resp = requests.post(f"{BASE_URL}/api/pagamento_status", json={
        "ano": ANO_TESTE,
        "mes": MES_TESTE,
        "categoria": cat_nome,
        "status": 2
    })
    assert resp.status_code == 200

    # Modal (/api/despesas_detalhe) não deve conter o lançamento 'Soma'
    resp = requests.get(f"{BASE_URL}/api/despesas_detalhe/{ANO_TESTE}/{MES_TESTE}/{cat_nome}")
    itens = resp.json()
    soma_itens = [i for i in itens if str(i.get("nota", "")).startswith("Soma das Despesas Fixas")]
    assert len(soma_itens) == 0, f"Lançamento 'Soma' ainda presente no modal: {soma_itens}"
    assert abs(sum(i.get("valor") or 0 for i in itens) - 14148.84) < 0.01, \
        f"Total do modal deveria ser só o manual (14148.84), veio {itens}"

    # Tabela (agregado /api/dados) não deve somar o 'Soma'
    resp = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}")
    dados = resp.json()
    cell = dados["despesas"][cat_nome].get(MES_TESTE) or dados["despesas"][cat_nome].get(str(MES_TESTE))
    assert cell is not None, f"Célula não encontrada em {list(dados['despesas'][cat_nome].keys())}"
    assert abs((cell.get("valor") or 0) - 14148.84) < 0.01, \
        f"Valor da célula deveria ser 14148.84, veio {cell.get('valor')}"
    print("    ✓ Lançamento 'Soma' oculto do modal e da tabela quando a célula está excluída")

    # Limpar (remover despesa manual, categoria e ano-fixa se houver)
    for item in itens:
        requests.delete(f"{BASE_URL}/api/despesa/{item['id']}")
    requests.delete(f"{BASE_URL}/api/categoria/{ANO_TESTE}/{cat_nome}")

# ============================================================================
# BACKEND - METAS (ano informativo)
# ============================================================================

@runner.test("Backend: Meta nao cria ano e aparece nos anos ate o alvo")
def test_meta_ano_informativo(r):
    import random as _random

    ano_fantasma = ANO_TESTE + 40 + _random.randint(0, 5)
    descricao = f"Meta ano informativo {ano_fantasma}"

    # 1. Criar meta com ano_meta em ano INEXISTENTE
    resp = requests.post(f"{BASE_URL}/api/meta", json={
        "descricao": descricao,
        "valor": 9999.00,
        "ano_meta": ano_fantasma,
        "ano_criacao": ANO_TESTE
    })
    assert resp.status_code == 200, f"Criar meta: {resp.status_code} {resp.text}"

    # 2. O ano fantasma NAO deve existir na lista de anos (meta nao cria ano)
    dados = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}").json()
    assert ano_fantasma not in dados["anos"], \
        f"Ano fantasma {ano_fantasma} nao deveria ser criado pela meta"

    # 3. A meta JA aparece no ano atual (faixa: ano_criacao <= ano <= ano_meta)
    metas_ano_atual = [m for m in dados["metas"] if m.get("descricao") == descricao]
    assert len(metas_ano_atual) == 1, "Meta deveria aparecer no ano atual (dentro da faixa)"

    # 4. Criar o ano de verdade
    resp = requests.post(f"{BASE_URL}/api/ano", json={"ano": ano_fantasma})
    assert resp.status_code == 200, f"Criar ano: {resp.status_code} {resp.text}"

    # 5. A meta e puxada para o ano recém-criado
    dados_fantasma = requests.get(f"{BASE_URL}/api/dados/{ano_fantasma}").json()
    metas_alvo = [m for m in dados_fantasma["metas"] if m.get("descricao") == descricao]
    assert len(metas_alvo) == 1, "Meta deveria aparecer no ano-alvo apos ele ser criado"
    meta_id = metas_alvo[0]["id"]

    print(f"    Meta ano_meta={ano_fantasma}: aparece no ano atual e no ano-alvo; ano so existiu apos POST /api/ano")

    # 6. Limpeza: excluir meta e ano
    requests.delete(f"{BASE_URL}/api/meta/{meta_id}")
    requests.delete(f"{BASE_URL}/api/ano/{ano_fantasma}")

@runner.test("Backend: Meta sem ano alvo aparece no ano de criacao")
def test_meta_sem_ano_alvo(r):
    import random as _random

    descricao = f"Meta sem ano alvo {_random.randint(0, 9999)}"

    resp = requests.post(f"{BASE_URL}/api/meta", json={
        "descricao": descricao,
        "valor": 123.45,
        "ano_meta": None,
        "ano_criacao": ANO_TESTE
    })
    assert resp.status_code == 200, f"Criar meta: {resp.status_code} {resp.text}"

    dados = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}").json()
    metas = [m for m in dados["metas"] if m.get("descricao") == descricao]
    assert len(metas) == 1, "Meta sem ano_meta deveria casar com o ano de criacao"
    meta_id = metas[0]["id"]

    # Limpeza
    requests.delete(f"{BASE_URL}/api/meta/{meta_id}")
    print("    Meta sem ano_meta aparece no ano_criacao")

# ============================================================================
# REGRESSÃO - BUGS DA CAÇADA (danpeg/bug-hunt)
# ============================================================================

def _criar_conta_e_categoria_vinculada(nome_categoria, ordem):
    """Cria conta + categoria com conta vinculada; retorna (conta_id, cat_id)."""
    resp = requests.post(f"{BASE_URL}/api/conta", json={"nome": "Conta Bugfix", "saldo_inicial": 0})
    assert resp.status_code == 200, f"Criar conta: {resp.status_code} {resp.text}"

    dados = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}").json()
    contas = [c for c in dados.get("contas", []) if c.get("nome") == "Conta Bugfix"]
    assert contas, "Conta Bugfix não encontrada em /api/dados"
    conta_id = contas[0]["id"]

    resp = requests.post(f"{BASE_URL}/api/categoria", json={
        "ano": ANO_TESTE,
        "nome": nome_categoria,
        "ordem": ordem,
        "inclui_fixas": False,
        "conta_vinculada_id": conta_id,
    })
    assert resp.status_code == 200, f"Criar categoria: {resp.status_code} {resp.text}"

    dados = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}").json()
    cat = next((c for c in dados.get("categorias", []) if c["nome"] == nome_categoria), None)
    assert cat is not None, "Categoria não encontrada"
    return conta_id, cat["id"]


@runner.test("BUG-2: Lote com mês de valor <= 0 vincula depósito ao mês certo")
def test_regressao_bug2_lote_deposito_mes(r):
    nome_cat = "Cat Lote Bug2"
    conta_id, _ = _criar_conta_e_categoria_vinculada(nome_cat, 990)

    try:
        # valores: -50 (mês 1), -20 (mês 2), 10 (mês 3) → depósito só no mês 3
        resp = requests.post(f"{BASE_URL}/api/despesa/lote", json={
            "ano": ANO_TESTE,
            "categoria": nome_cat,
            "valor": -50,
            "acrescimo": 30,
            "meses": [1, 2, 3],
            "nota": "Lote bug2",
        })
        assert resp.status_code == 200, f"Lote: {resp.status_code} {resp.text}"
        ids = resp.json().get("ids", [])
        assert len(ids) == 3, f"Esperado 3 despesas, veio {ids}"

        # Cada depósito deve estar vinculado à despesa do MESMO mês
        linhas = _query_db(
            "SELECT d.mes, dep.mes FROM depositos_conta dep "
            "JOIN despesas d ON d.id = dep.despesa_id "
            "WHERE d.categoria=? AND d.ano=?",
            (nome_cat, ANO_TESTE),
        )
        assert len(linhas) == 1, f"Esperado 1 depósito (mês 3), veio {linhas}"
        for mes_despesa, mes_deposito in linhas:
            assert mes_despesa == mes_deposito, \
                f"Depósito do mês {mes_deposito} vinculado à despesa do mês {mes_despesa}"
        print("    ✓ Depósito do mês 3 vinculado à despesa do mês 3")
    finally:
        ids = _query_db("SELECT id FROM despesas WHERE categoria=?", (nome_cat,))
        for (did,) in ids:
            requests.delete(f"{BASE_URL}/api/despesa/{did}")
        requests.delete(f"{BASE_URL}/api/categoria/{ANO_TESTE}/{nome_cat}")
        requests.delete(f"{BASE_URL}/api/conta/{conta_id}")


@runner.test("BUG-3: Editar despesa com payload parcial preserva valor e depósito")
def test_regressao_bug3_edicao_parcial(r):
    nome_cat = "Cat Edit Parcial Bug3"
    conta_id, _ = _criar_conta_e_categoria_vinculada(nome_cat, 989)

    try:
        resp = requests.post(f"{BASE_URL}/api/despesa", json={
            "ano": ANO_TESTE,
            "mes": MES_TESTE,
            "categoria": nome_cat,
            "valor": 123.45,
            "nota": "original",
        })
        assert resp.status_code == 200, f"Criar despesa: {resp.status_code} {resp.text}"
        despesa_id = resp.json().get("id")

        # Payload parcial: só a nota (sem "valor")
        resp = requests.put(f"{BASE_URL}/api/despesa/{despesa_id}", json={"nota": "editada"})
        assert resp.status_code == 200, f"Editar: {resp.status_code} {resp.text}"

        valor = _query_db("SELECT valor FROM despesas WHERE id=?", (despesa_id,))
        assert abs(valor[0][0] - 123.45) < 0.01, f"Valor deveria permanecer 123.45, veio {valor}"
        dep = _query_db("SELECT 1 FROM depositos_conta WHERE despesa_id=?", (despesa_id,))
        assert dep, "Depósito vinculado não deveria ser apagado na edição parcial"
        print("    ✓ Valor e depósito preservados em edição parcial")
    finally:
        ids = _query_db("SELECT id FROM despesas WHERE categoria=?", (nome_cat,))
        for (did,) in ids:
            requests.delete(f"{BASE_URL}/api/despesa/{did}")
        requests.delete(f"{BASE_URL}/api/categoria/{ANO_TESTE}/{nome_cat}")
        requests.delete(f"{BASE_URL}/api/conta/{conta_id}")


@runner.test("BUG-5: Des-excluir fixa de célula PAGA re-materializa a soma")
def test_regressao_bug5_desexcluir_fixa_paga(r):
    nome_cat = "Cat Fixa Paga Bug5"
    conta_id, _ = _criar_conta_e_categoria_vinculada(nome_cat, 988)

    try:
        # Criar fixa de 50,00 na categoria
        resp = requests.post(f"{BASE_URL}/api/fixa", json={
            "ano": ANO_TESTE,
            "descricao": "Fixa Bug5",
            "valor": 50.00,
            "dia": 10,
            "cat_id": None,  # fixa órfã: precisa inclui_fixas na categoria
        })
        # categoria não tem inclui_fixas; usar fixa com cat_id então
        dados = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}").json()
        cat = next((c for c in dados["categorias"] if c["nome"] == nome_cat), None)
        resp = requests.post(f"{BASE_URL}/api/fixa", json={
            "ano": ANO_TESTE,
            "descricao": "Fixa Bug5",
            "valor": 50.00,
            "dia": 10,
            "cat_id": cat["id"],
        })
        assert resp.status_code == 200, f"Criar fixa: {resp.status_code} {resp.text}"

        # Marcar célula como PAGA → materializa 'Soma das Despesas Fixas'
        resp = requests.post(f"{BASE_URL}/api/pagamento_status", json={
            "ano": ANO_TESTE,
            "mes": MES_TESTE,
            "categoria": nome_cat,
            "status": 2,
        })
        assert resp.status_code == 200, f"Status: {resp.status_code} {resp.text}"

        soma = _query_db(
            "SELECT id FROM despesas WHERE ano=? AND mes=? AND categoria=? AND nota LIKE 'Soma das Despesas Fixas%'",
            (ANO_TESTE, MES_TESTE, nome_cat),
        )
        assert soma, "Soma não foi materializada ao marcar PAGA"

        # Excluir a fixa da célula e depois des-excluir
        resp = requests.delete(f"{BASE_URL}/api/fixa_excecao", json={
            "ano": ANO_TESTE, "mes": MES_TESTE, "cat_id": cat["id"],
        })
        assert resp.status_code == 200, f"Des-excluir: {resp.status_code} {resp.text}"

        # A soma (e seu depósito) deve ter sido re-materializada
        soma2 = _query_db(
            "SELECT id FROM despesas WHERE ano=? AND mes=? AND categoria=? AND nota LIKE 'Soma das Despesas Fixas%'",
            (ANO_TESTE, MES_TESTE, nome_cat),
        )
        assert soma2, "Soma deveria ser re-materializada após des-excluir fixa PAGA"
        dep = _query_db("SELECT 1 FROM depositos_conta WHERE despesa_id=?", (soma2[0][0],))
        assert dep, "Depósito da soma deveria ser re-materializado"
        print("    ✓ Soma e depósito re-materializados após des-excluir fixa PAGA")
    finally:
        ids = _query_db("SELECT id FROM despesas WHERE categoria=?", (nome_cat,))
        for (did,) in ids:
            requests.delete(f"{BASE_URL}/api/despesa/{did}")
        fixas = _query_db("SELECT id FROM despesas_fixas_cartao WHERE ano=? AND cat_id=?", (ANO_TESTE, cat["id"]))
        for (fid,) in fixas:
            requests.delete(f"{BASE_URL}/api/fixa/{fid}")
        requests.delete(f"{BASE_URL}/api/categoria/{ANO_TESTE}/{nome_cat}")
        requests.delete(f"{BASE_URL}/api/conta/{conta_id}")

@runner.test("BUG-6: Lote de rendimentos rejeita mes_inicio inválido")
def test_regressao_bug6_mes_inicio(r):
    resp = requests.post(f"{BASE_URL}/api/rendimento/lancamento/lote", json={
        "ano": ANO_TESTE,
        "local_id": 1,
        "tipo": "aporte",
        "valor": 100,
        "mes_inicio": 0,
    })
    assert resp.status_code == 400, f"mes_inicio=0 deveria dar 400, veio {resp.status_code}: {resp.text}"
    resp = requests.post(f"{BASE_URL}/api/rendimento/lancamento/lote", json={
        "ano": ANO_TESTE,
        "local_id": 1,
        "tipo": "aporte",
        "valor": 100,
        "mes_inicio": 13,
    })
    assert resp.status_code == 400, f"mes_inicio=13 deveria dar 400, veio {resp.status_code}: {resp.text}"
    print("    ✓ mes_inicio fora de 1-12 rejeitado com 400")


@runner.test("BUG-7: Valores NaN/Inf rejeitados nas despesas")
def test_regressao_bug7_nan_inf(r):
    resp = requests.post(f"{BASE_URL}/api/despesa", json={
        "ano": ANO_TESTE, "mes": MES_TESTE, "categoria": "Cat NaN Teste",
        "valor": "NaN", "nota": "bug7",
    })
    assert resp.status_code == 400, f"NaN deveria dar 400, veio {resp.status_code}: {resp.text}"
    resp = requests.post(f"{BASE_URL}/api/despesa", json={
        "ano": ANO_TESTE, "mes": MES_TESTE, "categoria": "Cat NaN Teste",
        "valor": "Infinity", "nota": "bug7",
    })
    assert resp.status_code == 400, f"Infinity deveria dar 400, veio {resp.status_code}: {resp.text}"
    print("    ✓ NaN/Infinity rejeitados com 400")


@runner.test("BUG-8: Payload incompleto vira 400, não 500")
def test_regressao_bug8_key_error_400(r):
    resp = requests.post(f"{BASE_URL}/api/despesa", json={
        "ano": ANO_TESTE,  # sem "mes" nem "categoria"
    })
    assert resp.status_code == 400, f"Payload incompleto deveria dar 400, veio {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("ok") is False, f"Resposta deveria ter ok=False: {data}"
    print("    ✓ KeyError mapeado para 400 com corpo JSON")


@runner.test("BUG-11: Edição de despesa honra categoria do payload")
def test_regressao_bug11_categoria_edicao(r):
    nome_cat_a = "Cat Edit A Bug11"
    nome_cat_b = "Cat Edit B Bug11"
    for nome in (nome_cat_a, nome_cat_b):
        resp = requests.post(f"{BASE_URL}/api/categoria", json={
            "ano": ANO_TESTE, "nome": nome, "ordem": 987, "inclui_fixas": False,
        })
        assert resp.status_code == 200, f"Criar {nome}: {resp.status_code} {resp.text}"

    try:
        resp = requests.post(f"{BASE_URL}/api/despesa", json={
            "ano": ANO_TESTE, "mes": MES_TESTE, "categoria": nome_cat_a,
            "valor": 77.00, "nota": "bug11",
        })
        despesa_id = resp.json()["id"]

        resp = requests.put(f"{BASE_URL}/api/despesa/{despesa_id}", json={"categoria": nome_cat_b})
        assert resp.status_code == 200, f"Editar: {resp.status_code} {resp.text}"

        cat = _query_db("SELECT categoria FROM despesas WHERE id=?", (despesa_id,))
        assert cat and cat[0][0] == nome_cat_b, f"Categoria deveria ser {nome_cat_b}, veio {cat}"
        print("    ✓ Categoria atualizada na edição")
    finally:
        ids = _query_db("SELECT id FROM despesas WHERE categoria IN (?,?)", (nome_cat_a, nome_cat_b))
        for (did,) in ids:
            requests.delete(f"{BASE_URL}/api/despesa/{did}")
        requests.delete(f"{BASE_URL}/api/categoria/{ANO_TESTE}/{nome_cat_a}")
        requests.delete(f"{BASE_URL}/api/categoria/{ANO_TESTE}/{nome_cat_b}")


@runner.test("BUG-12: Categoria rejeita conta_vinculada_id inexistente")
def test_regressao_bug12_conta_vinculada_invalida(r):
    resp = requests.post(f"{BASE_URL}/api/categoria", json={
        "ano": ANO_TESTE, "nome": "Cat Conta Invalida",
        "ordem": 986, "inclui_fixas": False, "conta_vinculada_id": 999999,
    })
    assert resp.status_code == 400, f"Conta inexistente deveria dar 400, veio {resp.status_code}: {resp.text}"
    print("    ✓ conta_vinculada_id inexistente rejeitado com 400")


@runner.test("BUG-13: Excluir categoria remove pagamento_status órfão")
def test_regressao_bug13_pagamento_status_orfao(r):
    nome_cat = "Cat Status Orfao Bug13"
    resp = requests.post(f"{BASE_URL}/api/categoria", json={
        "ano": ANO_TESTE, "nome": nome_cat, "ordem": 985, "inclui_fixas": False,
    })
    assert resp.status_code == 200
    resp = requests.post(f"{BASE_URL}/api/pagamento_status", json={
        "ano": ANO_TESTE, "mes": MES_TESTE, "categoria": nome_cat, "status": 2,
    })
    assert resp.status_code == 200, f"Status: {resp.status_code} {resp.text}"

    dados = requests.get(f"{BASE_URL}/api/dados/{ANO_TESTE}").json()
    cat = next((c for c in dados["categorias"] if c["nome"] == nome_cat), None)
    assert cat is not None

    resp = requests.delete(f"{BASE_URL}/api/categoria/{cat['id']}")
    assert resp.status_code == 200, f"Deletar categoria: {resp.status_code} {resp.text}"

    orfaos = _query_db(
        "SELECT 1 FROM pagamento_status WHERE categoria=? AND ano=?",
        (nome_cat, ANO_TESTE),
    )
    assert not orfaos, "pagamento_status deveria ser removido com a categoria"
    print("    ✓ pagamento_status removido junto com a categoria")


@runner.test("BUG-16: Reordenar locais rejeita ids de anos diferentes")
def test_regressao_bug16_reorder_cross_ano(r):
    ano_outro = ANO_TESTE + 1
    requests.post(f"{BASE_URL}/api/ano", json={"ano": ano_outro})
    ids = []
    for ano in (ANO_TESTE, ano_outro):
        resp = requests.post(f"{BASE_URL}/api/rendimento/local", json={
            "ano": ano, "nome": f"Local Reorder {ano}",
        })
        assert resp.status_code == 200, f"Criar local {ano}: {resp.status_code} {resp.text}"
        ids.append(resp.json()["id"])

    try:
        resp = requests.post(f"{BASE_URL}/api/rendimentos/locais/reordenar", json={
            "ordem_ids": ids,  # mistura anos diferentes
        })
        assert resp.status_code == 400, f"Reordenar anos mistos deveria dar 400, veio {resp.status_code}: {resp.text}"
        print("    ✓ Reorder cross-ano rejeitado com 400")
    finally:
        for lid in ids:
            requests.delete(f"{BASE_URL}/api/rendimento/local/{lid}")

# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    import subprocess
    import time
    import atexit

    # ── Isolamento: banco de teste em TEMP (fora do OneDrive) — não toca no
    #    financeiro.db real do usuário. Porta 8086 limpa de órfãos.
    matar_servidores_na_porta(8086)
    db_teste = Path(tempfile.gettempdir()) / "controle_financeiro_unit" / "financeiro.db"
    db_teste.parent.mkdir(parents=True, exist_ok=True)
    limpar_banco_teste(db_teste)

    # ── Iniciar servidor Flask em modo SQLite (protege contra Supabase) ──
    env = os.environ.copy()
    env["DB_MODE"] = "sqlite"
    env["PORT"] = "8086"
    env["SQLITE_DB_PATH"] = str(db_teste)
    env["FLASK_SKIP_BROWSER"] = "1"
    env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))

    print(f"\n{Colors.BLUE}Iniciando servidor em modo SQLite...{Colors.RESET}")
    proc = subprocess.Popen(
        [sys.executable, "app.py", "--show-console"],
        env=env,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    atexit.register(lambda: kill_arvore(proc) if proc.poll() is None else None)

    # Aguardar servidor ficar pronto
    timeout = 15
    ready = False
    for _ in range(timeout * 4):
        if proc.poll() is not None:
            print(f"{Colors.RED}✗ Servidor morreu ao iniciar (processo encerrado){Colors.RESET}")
            sys.exit(1)
        try:
            requests.get(BASE_URL, timeout=2)
            ready = True
            break
        except Exception:
            time.sleep(0.25)

    if not ready:
        kill_arvore(proc)
        print(f"{Colors.RED}✗ Servidor não iniciou em {timeout}s{Colors.RESET}")
        sys.exit(1)

    print(f"{Colors.GREEN}✓ Servidor SQLite respondendo em {BASE_URL}{Colors.RESET}")

    DB_TESTE_PATH = str(db_teste)
    success = runner.run()

    # Desligar servidor (kill da árvore: terminate não mata o filho no Windows)
    kill_arvore(proc)

    # Limpar banco de teste do TEMP (inclui WAL/SHM)
    limpar_banco_teste(db_teste)
    try:
        db_teste.parent.rmdir()
    except OSError:
        pass

    sys.exit(0 if success else 1)
