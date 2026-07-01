"""
Testes de integração para Exportação e Importação do Banco de Dados (BD).

Cobre o ciclo completo (roundtrip) do backup SQLite:
  - Export do arquivo .db
  - Import de arquivo .db válido
  - Rejeição de arquivo inválido/corrompido
  - Backup de segurança (.bak) na importação
  - Sobrevivência de colunas novas (tipo, is_cartao) no roundtrip

Também valida a estrutura estática do Supabase (TABLES com todas as colunas).
"""

import io
import os
import sys
import shutil
import tempfile
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════
# Setup — força SQLite isolado
# ═══════════════════════════════════════════════════════════════════
os.environ["DB_MODE"] = "sqlite"
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_KEY", None)

TMPDIR = tempfile.mkdtemp(prefix="test_db_backup_")
DB_PATH = Path(TMPDIR) / "financeiro.db"
BAK_PATH = Path(TMPDIR) / "financeiro.db.bak"


def _patched_get_data_dir():
    return TMPDIR


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


# Inicializa schema
from financeiro.infrastructure.sqlite.schema import init_db
init_db(_connection_factory)


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _make_repo():
    from financeiro.infrastructure.sqlite.db_backup_repository import SQLiteDBBackupRepository
    return SQLiteDBBackupRepository(_connection_factory)


def _exportar(repo):
    result = repo.exportar_txt()
    # Retorna (body, status, headers) ou (body, status)
    if len(result) == 3:
        return result[0], result[1], result[2]
    return result[0], result[1], {}


def _importar(repo, conteudo_bytes):
    class _FakeFile:
        def read(self):
            return conteudo_bytes
    return repo.importar_txt(_FakeFile())


def _resetar_banco():
    """Fecha conexões pendentes, remove o banco e recria o schema."""
    import gc
    gc.collect()
    try:
        if DB_PATH.exists():
            DB_PATH.unlink()
    except PermissionError:
        # No Windows, o arquivo pode ficar travado; tenta renomear
        try:
            DB_PATH.rename(DB_PATH.with_suffix(".old"))
        except Exception:
            pass
    init_db(_connection_factory)


def _popular_dados():
    """Popula o banco com dados que exercitam colunas novas (tipo, is_cartao)."""
    conn = _connection_factory()
    conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(2026)")

    # Categoria com is_cartao=1
    conn.execute(
        "INSERT INTO categorias (nome, ordem, inclui_fixas, ano, is_cartao) VALUES (?,?,?,?,?)",
        ("Cartao", 1, 1, 2026, 1),
    )

    # Conta
    conn.execute(
        "INSERT INTO contas_correntes (nome, ordem, saldo_inicial) VALUES (?,?,?)",
        ("NuConta", 1, 1000.0),
    )
    conta_id = conn.execute("SELECT id FROM contas_correntes WHERE nome='NuConta'").fetchone()["id"]

    # Movimentação com tipo='rendimento'
    conn.execute(
        "INSERT INTO movimentacoes_mensais (ano, mes, conta_id, valor, nota, tipo) VALUES (?,?,?,?,?,?)",
        (2026, 3, conta_id, 150.0, "Teste", "rendimento"),
    )

    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _limpar_banco():
    """Remove bancos anteriores para garantir isolamento."""
    # Fecha conexões pendentes antes de deletar
    import gc
    gc.collect()
    for p in [DB_PATH, BAK_PATH, Path(str(DB_PATH) + ".tmp_import")]:
        try:
            if p.exists():
                p.unlink()
        except PermissionError:
            # Tenta renomear para evitar lock no Windows
            try:
                p.rename(p.with_suffix(".old_delete"))
            except Exception:
                pass
    # Recria schema
    init_db(_connection_factory)


# ═══════════════════════════════════════════════════════════════════
# Testes SQLite — Export
# ═══════════════════════════════════════════════════════════════════

class TestSQLiteExport:
    def test_export_banco_existente_retorna_bytes(self):
        repo = _make_repo()
        conteudo, status, headers = _exportar(repo)
        assert status == 200
        assert isinstance(conteudo, bytes)
        assert len(conteudo) > 0
        assert headers.get("Content-Type") == "application/octet-stream"

    def test_export_banco_inexistente_retorna_erro(self):
        # Remove o banco
        if DB_PATH.exists():
            DB_PATH.unlink()
        repo = _make_repo()
        body, status = _exportar(repo)[:2]
        assert status == 404
        assert "erro" in body


# ═══════════════════════════════════════════════════════════════════
# Testes SQLite — Import
# ═══════════════════════════════════════════════════════════════════

class TestSQLiteImport:
    def test_import_arquivo_vazio_retorna_erro(self):
        repo = _make_repo()
        body, status = _importar(repo, b"")
        assert status == 400
        assert "erro" in body

    def test_import_arquivo_invalido_retorna_erro(self):
        repo = _make_repo()
        body, status = _importar(repo, b"nao sou um banco sqlite")
        assert status == 400
        assert "erro" in body

    def test_import_sem_arquivo_retorna_erro(self):
        repo = _make_repo()
        body, status = repo.importar_txt(None)
        assert status == 400
        assert "erro" in body


# ═══════════════════════════════════════════════════════════════════
# Testes SQLite — Roundtrip
# ═══════════════════════════════════════════════════════════════════

class TestSQLiteRoundtrip:
    def test_roundtrip_dados_preservados(self):
        """Popula dados → exporta → limpa banco → importa → verifica."""
        # 1. Popular dados
        _popular_dados()
        conn_antes = _connection_factory()
        cats_antes = conn_antes.execute("SELECT * FROM categorias").fetchall()
        movs_antes = conn_antes.execute("SELECT * FROM movimentacoes_mensais").fetchall()
        conn_antes.close()
        assert len(cats_antes) == 1
        assert len(movs_antes) == 1

        # 2. Exportar
        repo = _make_repo()
        conteudo, status, _ = _exportar(repo)
        assert status == 200

        # 3. Limpar banco (simular import em banco vazio)
        _resetar_banco()
        # Verificar que está vazio
        conn_vazio = _connection_factory()
        assert len(conn_vazio.execute("SELECT * FROM categorias").fetchall()) == 0
        conn_vazio.close()

        # 4. Importar
        body, status = _importar(repo, conteudo)
        assert status == 200, f"Importação falhou: {body}"
        assert body["ok"] is True

        # 5. Verificar dados preservados
        conn_depois = _connection_factory()
        cats_depois = conn_depois.execute("SELECT * FROM categorias").fetchall()
        movs_depois = conn_depois.execute("SELECT * FROM movimentacoes_mensais").fetchall()
        conn_depois.close()
        assert len(cats_depois) == 1
        assert len(movs_depois) == 1

    def test_roundtrip_is_cartao_preservado(self):
        """Verifica que a coluna is_cartao sobrevive ao roundtrip."""
        conn = _connection_factory()
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(2026)")
        conn.execute(
            "INSERT INTO categorias (nome, ordem, inclui_fixas, ano, is_cartao) VALUES (?,?,?,?,?)",
            ("Cartao", 1, 1, 2026, 1),
        )
        conn.commit()
        conn.close()

        repo = _make_repo()
        conteudo, status, _ = _exportar(repo)
        assert status == 200

        # Limpa e reimporta
        _resetar_banco()
        body, status = _importar(repo, conteudo)
        assert status == 200

        conn = _connection_factory()
        row = conn.execute("SELECT is_cartao FROM categorias WHERE nome='Cartao'").fetchone()
        conn.close()
        assert row is not None
        assert row["is_cartao"] == 1

    def test_roundtrip_tipo_movimentacao_preservado(self):
        """Verifica que a coluna tipo em movimentacoes_mensais sobrevive."""
        conn = _connection_factory()
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(2026)")
        conn.execute(
            "INSERT INTO contas_correntes (nome, ordem, saldo_inicial) VALUES (?,?,?)",
            ("NuConta", 1, 0),
        )
        conta_id = conn.execute("SELECT id FROM contas_correntes WHERE nome='NuConta'").fetchone()["id"]
        conn.execute(
            "INSERT INTO movimentacoes_mensais (ano, mes, conta_id, valor, nota, tipo) VALUES (?,?,?,?,?,?)",
            (2026, 3, conta_id, 150.0, "Rendimento CDB", "rendimento"),
        )
        conn.commit()
        conn.close()

        repo = _make_repo()
        conteudo, status, _ = _exportar(repo)
        assert status == 200

        _resetar_banco()
        body, status = _importar(repo, conteudo)
        assert status == 200

        conn = _connection_factory()
        row = conn.execute(
            "SELECT tipo, nota FROM movimentacoes_mensais WHERE ano=2026"
        ).fetchone()
        conn.close()
        assert row is not None, "Movimentação não encontrada após roundtrip"
        assert row["tipo"] == "rendimento", f"tipo esperado 'rendimento', obtido '{row['tipo']}'"
        assert row["nota"] == "Rendimento CDB"

    def test_roundtrip_rendimentos_lancamentos(self):
        """Verifica que rendimentos_lancamentos com tipo sobrevivem."""
        conn = _connection_factory()
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(2026)")
        conn.execute(
            "INSERT INTO rendimentos_locais (ano, nome, ordem) VALUES (?,?,?)",
            (2026, "CDB", 1),
        )
        local_id = conn.execute(
            "SELECT id FROM rendimentos_locais WHERE nome='CDB' AND ano=2026"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO rendimentos_lancamentos (ano, mes, local_id, tipo, valor, nota) VALUES (?,?,?,?,?,?)",
            (2026, 5, local_id, "aporte", 500.0, ""),
        )
        conn.execute(
            "INSERT INTO rendimentos_lancamentos (ano, mes, local_id, tipo, valor, nota) VALUES (?,?,?,?,?,?)",
            (2026, 6, local_id, "saque", 100.0, ""),
        )
        conn.commit()
        conn.close()

        repo = _make_repo()
        conteudo, status, _ = _exportar(repo)
        assert status == 200

        _resetar_banco()
        body, status = _importar(repo, conteudo)
        assert status == 200

        conn = _connection_factory()
        lancs = conn.execute(
            "SELECT tipo, valor, mes FROM rendimentos_lancamentos WHERE ano=2026 ORDER BY mes"
        ).fetchall()
        conn.close()
        assert len(lancs) == 2, f"Esperados 2 lançamentos, obtidos {len(lancs)}"
        assert lancs[0]["tipo"] == "aporte"
        assert lancs[0]["valor"] == 500.0
        assert lancs[1]["tipo"] == "saque"
        assert lancs[1]["valor"] == 100.0

    def test_import_cria_backup_seguranca(self):
        """Verifica que o .bak é criado ao importar sobre um banco existente."""
        _popular_dados()
        repo = _make_repo()
        conteudo, status, _ = _exportar(repo)
        assert status == 200

        # Importa sobre o mesmo banco (deve criar .bak)
        body, status = _importar(repo, conteudo)
        assert status == 200
        assert BAK_PATH.exists(), f"Backup .bak não foi criado em {BAK_PATH}"

    def test_roundtrip_conta_vinculada_rendimentos(self):
        """Verifica que conta_vinculada_id em rendimentos_locais sobrevive."""
        conn = _connection_factory()
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(2026)")
        conn.execute(
            "INSERT INTO contas_correntes (nome, ordem, saldo_inicial) VALUES (?,?,?)",
            ("NuConta", 1, 1000.0),
        )
        conta_id = conn.execute("SELECT id FROM contas_correntes WHERE nome='NuConta'").fetchone()["id"]
        conn.execute(
            "INSERT INTO rendimentos_locais (ano, nome, ordem, conta_vinculada_id) VALUES (?,?,?,?)",
            (2026, "CDB", 1, conta_id),
        )
        conn.commit()
        conn.close()

        repo = _make_repo()
        conteudo, status, _ = _exportar(repo)
        assert status == 200

        _resetar_banco()
        body, status = _importar(repo, conteudo)
        assert status == 200

        conn = _connection_factory()
        row = conn.execute(
            "SELECT rl.conta_vinculada_id, cc.nome as conta_nome "
            "FROM rendimentos_locais rl "
            "LEFT JOIN contas_correntes cc ON cc.id = rl.conta_vinculada_id "
            "WHERE rl.nome='CDB' AND rl.ano=2026"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["conta_vinculada_id"] is not None
        assert row["conta_nome"] == "NuConta"


# ═══════════════════════════════════════════════════════════════════
# Testes Supabase — Estrutura estática do TABLES
# ═══════════════════════════════════════════════════════════════════

class TestSupabaseTablesStructure:
    """Valida que o array TABLES contém todas as colunas do schema atual."""

    @pytest.fixture
    def tables(self):
        from financeiro.infrastructure.supabase.db_backup_repository import TABLES
        return {t["name"]: t for t in TABLES}

    def test_movimentacoes_tem_tipo(self, tables):
        t = tables["movimentacoes_mensais"]
        assert "tipo" in t["columns"], (
            "Coluna 'tipo' ausente em movimentacoes_mensais no backup Supabase!\n"
            "Commit 2659464 adicionou esta coluna — o backup exporta sem ela."
        )

    def test_categorias_tem_is_cartao(self, tables):
        t = tables["categorias"]
        assert "is_cartao" in t["columns"], (
            "Coluna 'is_cartao' ausente em categorias no backup Supabase!\n"
            "Commit 6419f89 adicionou esta coluna — o backup exporta sem ela."
        )

    def test_rendimentos_locais_tem_conta_vinculada(self, tables):
        t = tables["rendimentos_locais"]
        assert "conta_vinculada_id" in t["columns"], (
            "Coluna 'conta_vinculada_id' ausente em rendimentos_locais!"
        )

    def test_rendimentos_lancamentos_tem_tipo(self, tables):
        t = tables["rendimentos_lancamentos"]
        assert "tipo" in t["columns"], (
            "Coluna 'tipo' ausente em rendimentos_lancamentos!"
        )

    def test_todas_tabelas_schema_presentes(self, tables):
        """Verifica que as tabelas principais do schema estão no backup."""
        esperadas = [
            "anos", "config", "contas_correntes", "categorias",
            "despesas", "receitas", "despesas_fixas_cartao",
            "fixas_excecoes", "fixas_aplicadas_manual",
            "pagamento_status", "rendimentos_realizados",
            "metas", "depositos_conta", "movimentacoes_mensais",
            "rendimentos_locais", "rendimentos_lancamentos",
        ]
        for nome in esperadas:
            assert nome in tables, f"Tabela '{nome}' ausente no backup Supabase!"


# ═══════════════════════════════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════════════════════════════

def teardown_module():
    _paths_mod.get_data_dir = _original_get_data_dir
    shutil.rmtree(TMPDIR, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
