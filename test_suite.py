#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite de Testes de Integração - Controle Financeiro v1.2.3
Valida todas as refatorações DRY/DDD implementadas
"""

import os
import sys

# ═══════════════════════════════════════════════════════════════════
# VERIFICAR Supabase — aborta se Supabase estiver ativo/acessivel
# ═══════════════════════════════════════════════════════════════════
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_browser.verificar_ambiente import verificar as _verificar_supabase
_verificar_supabase()

# ═══════════════════════════════════════════════════════════════════
# FORÇAR SQLite — antes de qualquer import do projeto
# ═══════════════════════════════════════════════════════════════════
os.environ["DB_MODE"] = "sqlite"

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8080"
ANO_TESTE = datetime.now().year + 5
MES_TESTE = 12  # Dezembro (evita conflitos com dados existentes)

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

# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    import subprocess
    import time
    import atexit

    # ── Iniciar servidor Flask em modo SQLite (protege contra Supabase) ──
    env = os.environ.copy()
    env["DB_MODE"] = "sqlite"
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
    atexit.register(lambda: proc.kill() if proc.poll() is None else None)

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
        proc.kill()
        print(f"{Colors.RED}✗ Servidor não iniciou em {timeout}s{Colors.RESET}")
        sys.exit(1)

    print(f"{Colors.GREEN}✓ Servidor SQLite respondendo em {BASE_URL}{Colors.RESET}")

    success = runner.run()

    # Desligar servidor
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    sys.exit(0 if success else 1)
