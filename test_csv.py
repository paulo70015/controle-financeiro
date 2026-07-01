"""
Testes de integração para Importação e Exportação CSV.

Cobre o ciclo completo (roundtrip): export → import → re-export e
verifica integridade de todos os blocos:
  - Despesas (categorias com valores mensais)
  - Despesas Fixas
  - Metas
  - Receitas
  - Rendimentos (aporte/saque + conta vinculada)
  - Movimentações Mensais (com conta_id e tipo)
  - Contas — Saldo Acumulado (depósitos)

Também testa cenários de borda:
  - Importação de CSV legado (não-exportado, formato lateral)
  - Saques detectados por valor negativo
  - Coluna conta_vinculada_id no roundtrip
"""

import io
import os
import sys
import csv
import shutil
import tempfile
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════
# Setup — força SQLite isolado antes de qualquer import do projeto
# ═══════════════════════════════════════════════════════════════════
os.environ["DB_MODE"] = "sqlite"
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_KEY", None)

# Redireciona get_data_dir para um diretório temporário isolado
TMPDIR = tempfile.mkdtemp(prefix="test_csv_")
DB_PATH = Path(TMPDIR) / "financeiro.db"


def _patched_get_data_dir():
    return TMPDIR


# Aplica o patch antes que qualquer módulo chame get_data_dir
import financeiro.infrastructure.runtime.paths as _paths_mod
_original_get_data_dir = _paths_mod.get_data_dir
_paths_mod.get_data_dir = _patched_get_data_dir


def _connection_factory(**kwargs):
    """Factory de conexão SQLite para o banco temporário de teste."""
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


# Inicializa schema uma única vez
from financeiro.infrastructure.sqlite.schema import init_db
init_db(_connection_factory)

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _make_repo():
    """Cria uma instância fresca do repositório CSV SQLite."""
    from financeiro.infrastructure.sqlite.csv_repository import SQLiteCSVRepository
    return SQLiteCSVRepository(_connection_factory, MESES)


def _importar_csv(repo, conteudo: str, encoding: str = "utf-8-sig"):
    """Wrapper para importar um CSV a partir de uma string."""

    class _FakeFile:
        def read(self):
            return conteudo.encode(encoding)

    return repo.importar_csv(_FakeFile())


def _exportar_csv(repo, ano: int):
    """Wrapper para exportar CSV e retornar o texto decodificado."""
    csv_bytes, status, headers = repo.exportar_csv(ano)
    return csv_bytes.decode("utf-8-sig"), status, headers


def _csv_para_linhas(texto: str):
    """Converte texto CSV em lista de listas, removendo BOM e sep=."""
    texto_limpo = texto.replace("\ufeff", "")
    if texto_limpo.startswith("sep=;"):
        texto_limpo = texto_limpo.split("\r\n", 1)[1] if "\r\n" in texto_limpo else texto_limpo.split("\n", 1)[1]
    reader = csv.reader(io.StringIO(texto_limpo), delimiter=";")
    return [row for row in reader]


def _bloco_presente(linhas: list, titulo: str) -> bool:
    """Verifica se um bloco com o título dado existe nas linhas do CSV."""
    for row in linhas:
        if row and row[0].strip() == titulo:
            return True
    return False


def _valor_na_linha(linhas: list, primeira_coluna: str, mes: int) -> float:
    """Busca o valor numérico em uma linha cuja primeira coluna bata, no mês 1-12."""
    for row in linhas:
        if row and row[0].strip() == primeira_coluna:
            if mes < len(row):
                raw = row[mes].strip()
                if raw:
                    return float(raw.replace(".", "").replace(",", "."))
    return 0.0


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _limpar_banco():
    """Limpa todas as tabelas antes de cada teste para evitar acúmulo."""
    conn = _connection_factory()
    tabelas = [
        "despesas", "receitas", "despesas_fixas_cartao", "metas",
        "movimentacoes_mensais", "depositos_conta",
        "rendimentos_lancamentos", "rendimentos_locais",
        "fixas_excecoes", "fixas_aplicadas_manual",
        "pagamento_status", "rendimentos_realizados",
        "categorias", "contas_correntes", "anos",
    ]
    for t in tabelas:
        try:
            conn.execute(f"DELETE FROM {t}")
        except Exception:
            pass
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# Testes
# ═══════════════════════════════════════════════════════════════════

class TestCSVImportBasico:
    """Testes de importação de CSV (formato exportado pelo sistema)."""

    def test_import_despesas(self):
        repo = _make_repo()
        csv_conteudo = '''sep=;
"2026";"";"";"";"";"";"";"";"";"";"";"";"";""
"";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total"
"Alimentacao";"100";"200";"";"";"";"";"";"";"";"";"";"";"300"
'''
        result, status = _importar_csv(repo, csv_conteudo)
        assert result["ok"], f"Importação falhou: {result}"
        assert result["importados"]["despesas"] == 2
        assert result["ano"] == 2026

    def test_import_fixas(self):
        repo = _make_repo()
        csv_conteudo = '''sep=;
"2026";"";"";"";"";"";"";"";"";"";"";"";"";""
"";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total"
"";"";"";"";"";"";"";"";"";"";"";"";"";""
"Despesas Fixas";"Dia";"Valor";"";"";"";"";"";"";"";"";"";"";""
"Netflix";"10";"50";"";"";"";"";"";"";"";"";"";"";""
"Total Fixas";"";"50";"";"";"";"";"";"";"";"";"";"";""
'''
        result, status = _importar_csv(repo, csv_conteudo)
        assert result["ok"], f"Importação falhou: {result}"
        assert result["importados"]["fixas"] == 1

    def test_import_metas(self):
        repo = _make_repo()
        csv_conteudo = '''sep=;
"2026";"";"";"";"";"";"";"";"";"";"";"";"";""
"";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total"
"";"";"";"";"";"";"";"";"";"";"";"";"";""
"Metas";"Valor Alvo";"Ano";"Status";"";"";"";"";"";"";"";"";"";""
"Reserva";"10000";"2026";"Em andamento";"";"";"";"";"";"";"";"";"";""
'''
        result, status = _importar_csv(repo, csv_conteudo)
        assert result["ok"], f"Importação falhou: {result}"
        assert result["importados"]["metas"] == 1

    def test_import_receitas(self):
        repo = _make_repo()
        csv_conteudo = '''sep=;
"2026";"";"";"";"";"";"";"";"";"";"";"";"";""
"";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total"
"";"";"";"";"";"";"";"";"";"";"";"";"";""
"Receitas";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total"
"Receitas";"500";"500";"";"";"";"";"";"";"";"";"";"";"1000"
'''
        result, status = _importar_csv(repo, csv_conteudo)
        assert result["ok"], f"Importação falhou: {result}"

    def test_import_rendimentos_com_aporte(self):
        repo = _make_repo()
        csv_conteudo = '''sep=;
"2026";"";"";"";"";"";"";"";"";"";"";"";"";""
"";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total"
"";"";"";"";"";"";"";"";"";"";"";"";"";""
"Rendimentos";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total";"Conta Vinculada"
"CDB";"100";"200";"";"";"";"";"";"";"";"";"";"";"300";"NuConta"
'''
        result, status = _importar_csv(repo, csv_conteudo)
        assert result["ok"], f"Importação falhou: {result}"
        assert result["importados"]["rendimentos"] >= 2

        # Verifica que conta_vinculada_id foi setado
        conn = _connection_factory()
        locais = conn.execute("SELECT * FROM rendimentos_locais WHERE ano=2026").fetchall()
        assert len(locais) == 1
        assert locais[0]["conta_vinculada_id"] is not None
        conn.close()

    def test_import_rendimentos_com_saque(self):
        """Valores negativos no CSV devem ser importados como tipo='saque'."""
        repo = _make_repo()
        csv_conteudo = '''sep=;
"2026";"";"";"";"";"";"";"";"";"";"";"";"";""
"";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total"
"";"";"";"";"";"";"";"";"";"";"";"";"";""
"Rendimentos";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total";"Conta Vinculada"
"CDB";"-50";"";"";"";"";"";"";"";"";"";"";"";"-50";
'''
        result, status = _importar_csv(repo, csv_conteudo)
        assert result["ok"], f"Importação falhou: {result}"

        # Verifica que foi salvo como saque (tipo='saque', valor positivo abs)
        conn = _connection_factory()
        lancs = conn.execute(
            "SELECT tipo, valor FROM rendimentos_lancamentos WHERE ano=2026"
        ).fetchall()
        conn.close()
        assert len(lancs) == 1
        assert lancs[0]["tipo"] == "saque"
        assert lancs[0]["valor"] == 50.0

    def test_import_movimentacoes_com_conta_id(self):
        """Movimentações devem ser importadas com conta_id (antes era omitido → crash)."""
        repo = _make_repo()
        csv_conteudo = '''sep=;
"2026";"";"";"";"";"";"";"";"";"";"";"";"";""
"";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total"
"";"";"";"";"";"";"";"";"";"";"";"";"";""
"Movimentações";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total"
"NuConta";"100";"-30";"";"";"";"";"";"";"";"";"";"";"70"
'''
        result, status = _importar_csv(repo, csv_conteudo)
        assert result["ok"], f"Importação falhou: {result}"
        assert result["importados"]["movimentacoes"] == 2

        # Verifica que conta_id foi preenchido (NOT NULL)
        conn = _connection_factory()
        movs = conn.execute(
            "SELECT conta_id, valor, tipo FROM movimentacoes_mensais WHERE ano=2026"
        ).fetchall()
        conn.close()
        assert len(movs) == 2
        for m in movs:
            assert m["conta_id"] is not None, "conta_id deveria estar preenchido!"

    def test_import_contas_saldo_acumulado(self):
        """Contas Saldo Acumulado devem importar depósitos com delta entre meses."""
        repo = _make_repo()
        csv_conteudo = '''sep=;
"2026";"";"";"";"";"";"";"";"";"";"";"";"";""
"";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total"
"";"";"";"";"";"";"";"";"";"";"";"";"";""
"Contas Saldo Acumulado";"Jan";"Fev";"Mar";"Abr";"Mai";"Jun";"Jul";"Ago";"Set";"Out";"Nov";"Dez";"Total"
"NuConta";"100";"250";"";"";"";"";"";"";"";"";"";"";""
'''
        result, status = _importar_csv(repo, csv_conteudo)
        assert result["ok"], f"Importação falhou: {result}"
        assert result["importados"]["depositos"] >= 1

        # Verifica: mês 1 deve ter delta=100, mês 2 delta=150 (250-100)
        conn = _connection_factory()
        deps = conn.execute(
            "SELECT mes, valor FROM depositos_conta WHERE ano=2026 ORDER BY mes"
        ).fetchall()
        conn.close()
        assert len(deps) >= 2
        assert deps[0]["valor"] == 100.0
        assert deps[1]["valor"] == 150.0


class TestCSVExportBlocos:
    """Testes de exportação — verifica presença de todos os blocos."""

    def _popular_dados(self, ano=2026):
        """Popula o banco com dados variados para testar o export completo."""
        conn = _connection_factory()
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (ano,))

        # Categoria
        conn.execute(
            "INSERT INTO categorias (nome, ordem, inclui_fixas, ano) VALUES (?,?,?,?)",
            ("Alimentacao", 1, 0, ano),
        )
        cat_id = conn.execute("SELECT id FROM categorias WHERE nome='Alimentacao' AND ano=?", (ano,)).fetchone()["id"]

        # Despesas
        conn.execute(
            "INSERT INTO despesas (ano, mes, categoria, valor, nota) VALUES (?,?,?,?,?)",
            (ano, 1, "Alimentacao", 100.0, ""),
        )
        conn.execute(
            "INSERT INTO despesas (ano, mes, categoria, valor, nota) VALUES (?,?,?,?,?)",
            (ano, 2, "Alimentacao", 50.0, ""),
        )

        # Fixas
        conn.execute(
            "INSERT INTO despesas_fixas_cartao (descricao, valor, dia, ativa, cat_id, ano) VALUES (?,?,?,?,?,?)",
            ("Netflix", 39.90, 10, 1, cat_id, ano),
        )

        # Metas
        conn.execute(
            "INSERT INTO metas (descricao, valor, ano_meta, concluida, ano_criacao) VALUES (?,?,?,?,?)",
            ("Reserva", 10000.0, ano, 0, ano),
        )

        # Receitas
        conn.execute(
            "INSERT INTO receitas (ano, mes, descricao, valor, nota) VALUES (?,?,?,?,?)",
            (ano, 1, "Salario", 5000.0, ""),
        )
        conn.execute(
            "INSERT INTO receitas (ano, mes, descricao, valor, nota) VALUES (?,?,?,?,?)",
            (ano, 2, "Salario", 5000.0, ""),
        )

        # Conta corrente
        conn.execute("INSERT OR IGNORE INTO contas_correntes (nome, ordem, saldo_inicial) VALUES (?,?,?)",
                      ("NuConta", 1, 1000.0))
        conta_id = conn.execute("SELECT id FROM contas_correntes WHERE nome='NuConta'").fetchone()["id"]

        # Rendimentos locais
        conn.execute(
            "INSERT INTO rendimentos_locais (ano, nome, ordem, conta_vinculada_id) VALUES (?,?,?,?)",
            (ano, "CDB", 1, conta_id),
        )
        rend_local_id = conn.execute(
            "SELECT id FROM rendimentos_locais WHERE nome='CDB' AND ano=?", (ano,)
        ).fetchone()["id"]

        # Rendimentos lancamentos (aporte + saque)
        conn.execute(
            "INSERT INTO rendimentos_lancamentos (ano, mes, local_id, tipo, valor, nota) VALUES (?,?,?,?,?,?)",
            (ano, 1, rend_local_id, "aporte", 100.0, ""),
        )
        conn.execute(
            "INSERT INTO rendimentos_lancamentos (ano, mes, local_id, tipo, valor, nota) VALUES (?,?,?,?,?,?)",
            (ano, 2, rend_local_id, "saque", 50.0, ""),
        )

        # Movimentações mensais
        conn.execute(
            "INSERT INTO movimentacoes_mensais (ano, mes, conta_id, valor, nota, tipo) VALUES (?,?,?,?,?,?)",
            (ano, 3, conta_id, 200.0, "", "rendimento"),
        )

        # Depósitos
        conn.execute(
            "INSERT INTO depositos_conta (ano, mes, conta_id, valor, nota) VALUES (?,?,?,?,?)",
            (ano, 1, conta_id, 500.0, ""),
        )
        conn.execute(
            "INSERT INTO depositos_conta (ano, mes, conta_id, valor, nota) VALUES (?,?,?,?,?)",
            (ano, 2, conta_id, 300.0, ""),
        )

        conn.commit()
        conn.close()

    def test_export_contem_todos_os_blocos(self):
        self._popular_dados(2026)
        repo = _make_repo()
        csv_text, status, headers = _exportar_csv(repo, 2026)
        linhas = _csv_para_linhas(csv_text)

        assert status == 200
        assert _bloco_presente(linhas, "Despesas Fixas"), "Bloco Despesas Fixas ausente"
        assert _bloco_presente(linhas, "Metas"), "Bloco Metas ausente"
        assert _bloco_presente(linhas, "Receitas"), "Bloco Receitas ausente"
        assert _bloco_presente(linhas, "Rendimentos"), "Bloco Rendimentos ausente"
        assert _bloco_presente(linhas, "Movimentações"), "Bloco Movimentações ausente"
        assert _bloco_presente(linhas, "Contas Saldo Acumulado"), "Bloco Contas Saldo Acumulado ausente"

    def test_export_rendimentos_tem_conta_vinculada(self):
        self._popular_dados(2026)
        repo = _make_repo()
        csv_text, status, headers = _exportar_csv(repo, 2026)
        linhas = _csv_para_linhas(csv_text)

        # Procura a coluna "Conta Vinculada" no cabeçalho de Rendimentos
        for row in linhas:
            if row and row[0].strip() == "Rendimentos":
                assert "Conta Vinculada" in row, f"Cabeçalho de Rendimentos sem 'Conta Vinculada': {row}"
                break
        else:
            pytest.fail("Cabeçalho 'Rendimentos' não encontrado no CSV")

        # Verifica que a linha do CDB (ou CDB - aporte, primeiro do grupo) tem o nome da conta vinculada
        for row in linhas:
            first_col = row[0].strip() if row else ""
            if first_col in ("CDB", "CDB - aporte") and len(row) > 14:
                assert row[14].strip() == "NuConta", f"Conta vinculada esperada 'NuConta', obtida '{row[14]}'"
                break
        else:
            pytest.fail("Linha 'CDB' / 'CDB - aporte' com conta vinculada não encontrada")

    def test_export_rendimentos_tipos_separados(self):
        """Quando há aporte e saque, o export deve gerar linhas 'Local - aporte' e 'Local - saque'."""
        self._popular_dados(2026)
        repo = _make_repo()
        csv_text, status, headers = _exportar_csv(repo, 2026)
        linhas = _csv_para_linhas(csv_text)

        tem_cdb_aporte = any(
            row and row[0].strip() == "CDB - aporte" for row in linhas
        )
        tem_cdb_saque = any(
            row and row[0].strip() == "CDB - saque" for row in linhas
        )
        assert tem_cdb_aporte, "Linha 'CDB - aporte' não encontrada no export"
        assert tem_cdb_saque, "Linha 'CDB - saque' não encontrada no export"


class TestCSVRoundtrip:
    """Testes de ciclo completo: export → import → re-export."""

    def _setup_banco_populado(self, ano=2027):
        """Popula o banco e retorna o CSV exportado."""
        # Aproveita o método da classe acima para popular
        TestCSVExportBlocos()._popular_dados(ano)
        repo = _make_repo()
        csv_text, status, _ = _exportar_csv(repo, ano)
        assert status == 200
        return csv_text

    def test_roundtrip_integridade(self):
        """Exporta, reimporta em ano diferente e verifica consistência."""
        ano_origem = 2027
        csv_text = self._setup_banco_populado(ano_origem)

        # Troca o ano no CSV para 2028 (simula reimportação em outro ano)
        csv_2028 = csv_text.replace(f'"{ano_origem}"', '"2028"')

        # Importa no ano 2028
        repo = _make_repo()
        result, status = _importar_csv(repo, csv_2028)
        assert result["ok"], f"Reimportação falhou: {result}"

        # Exporta 2028 e verifica blocos
        csv_text_2028, status, _ = _exportar_csv(repo, 2028)
        linhas = _csv_para_linhas(csv_text_2028)

        assert _bloco_presente(linhas, "Receitas"), "Bloco Receitas ausente no roundtrip"
        assert _bloco_presente(linhas, "Movimentações"), "Bloco Movimentações ausente no roundtrip"
        assert _bloco_presente(linhas, "Contas Saldo Acumulado"), "Bloco Contas Saldo Acumulado ausente no roundtrip"

    def test_roundtrip_rendimentos_saque_preservado(self):
        """Verifica que saques sobrevivem ao roundtrip export → import."""
        ano = 2029
        conn = _connection_factory()
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (ano,))
        conn.execute("INSERT OR IGNORE INTO contas_correntes (nome, ordem, saldo_inicial) VALUES (?,?,?)",
                      ("NuConta", 1, 0))
        conn.execute(
            "INSERT INTO rendimentos_locais (ano, nome, ordem) VALUES (?,?,?)",
            (ano, "Fundo", 1),
        )
        local_id = conn.execute(
            "SELECT id FROM rendimentos_locais WHERE nome='Fundo' AND ano=?", (ano,)
        ).fetchone()["id"]
        # Um aporte e um saque
        conn.execute(
            "INSERT INTO rendimentos_lancamentos (ano, mes, local_id, tipo, valor, nota) VALUES (?,?,?,?,?,?)",
            (ano, 3, local_id, "aporte", 200.0, ""),
        )
        conn.execute(
            "INSERT INTO rendimentos_lancamentos (ano, mes, local_id, tipo, valor, nota) VALUES (?,?,?,?,?,?)",
            (ano, 4, local_id, "saque", 80.0, ""),
        )
        conn.commit()
        conn.close()

        # Exporta
        repo = _make_repo()
        csv_text, status, _ = _exportar_csv(repo, ano)
        assert status == 200

        # Importa em ano novo (2030)
        csv_2030 = csv_text.replace(f'"{ano}"', '"2030"')
        result, status = _importar_csv(repo, csv_2030)
        assert result["ok"], f"Reimportação falhou: {result}"

        # Verifica que os dois tipos estão presentes no banco 2030
        conn = _connection_factory()
        lancs = conn.execute(
            "SELECT tipo, valor FROM rendimentos_lancamentos WHERE ano=2030 ORDER BY tipo"
        ).fetchall()
        conn.close()
        assert len(lancs) == 2, f"Esperados 2 lançamentos, obtidos {len(lancs)}"
        assert lancs[0]["tipo"] == "aporte"
        assert lancs[0]["valor"] == 200.0
        assert lancs[1]["tipo"] == "saque"
        assert lancs[1]["valor"] == 80.0


class TestCSVImportLegado:
    """Testes de importação de CSV não-exportado (formato lateral / planilha legada)."""

    def test_import_legado_despesas(self):
        """Formato legado: primeira linha com ano, cabeçalho com meses, valores em colunas."""
        repo = _make_repo()
        csv_conteudo = '''sep=,
2026,Jan,Fev,Mar,Abr,Mai,Jun,Jul,Ago,Set,Out,Nov,Dez
Alimentacao,100,200,,,,,,,,,,
Transporte,,50,,,,,,,,,,
'''
        result, status = _importar_csv(repo, csv_conteudo)
        assert result["ok"], f"Importação legado falhou: {result}"
        assert result["importados"]["despesas"] >= 2

    def test_import_legado_movimentacao(self):
        """Formato legado com linha 'nubank' deve criar conta e importar."""
        repo = _make_repo()
        csv_conteudo = '''sep=,
2026,Jan,Fev,Mar,Abr,Mai,Jun,Jul,Ago,Set,Out,Nov,Dez
nubank,100,-30,,,,,,,,,,
'''
        result, status = _importar_csv(repo, csv_conteudo)
        assert result["ok"], f"Importação legado falhou: {result}"
        assert result["importados"]["movimentacoes"] == 2

        # Verifica que conta_id foi preenchido
        conn = _connection_factory()
        movs = conn.execute("SELECT conta_id FROM movimentacoes_mensais WHERE ano=2026").fetchall()
        conn.close()
        for m in movs:
            assert m["conta_id"] is not None, "conta_id deveria estar preenchido (legado)!"

    def test_import_legado_rendimento_com_saque(self):
        """Formato legado: linha 'rendimento' com valor negativo deve virar saque."""
        repo = _make_repo()
        csv_conteudo = '''sep=,
2026,Jan,Fev,Mar,Abr,Mai,Jun,Jul,Ago,Set,Out,Nov,Dez
rendimento,-50,,,,,,,,,,,
'''
        result, status = _importar_csv(repo, csv_conteudo)
        assert result["ok"], f"Importação legado falhou: {result}"

        conn = _connection_factory()
        lancs = conn.execute(
            "SELECT tipo, valor FROM rendimentos_lancamentos WHERE ano=2026"
        ).fetchall()
        conn.close()
        assert len(lancs) == 1
        assert lancs[0]["tipo"] == "saque"
        assert lancs[0]["valor"] == 50.0


# ═══════════════════════════════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════════════════════════════

def teardown_module():
    """Remove o diretório temporário após todos os testes."""
    _paths_mod.get_data_dir = _original_get_data_dir
    shutil.rmtree(TMPDIR, ignore_errors=True)


if __name__ == "__main__":
    # Permite rodar diretamente: python test_csv.py
    pytest.main([__file__, "-v", "--tb=short"])
