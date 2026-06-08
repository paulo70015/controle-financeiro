"""
Schema do banco SQLite — definição canónica com tabela `anos` e
FOREIGN KEY ... ON DELETE CASCADE em todas as tabelas filhas.

Para bancos legados (sem FKs para `anos`), a rotina `_upgrade_to_anos`
recria as tabelas filhas com as constraints.
"""

import logging


def init_db(connection_factory):
    """
    Inicializa o banco de dados, ativando chaves estrangeiras,
    criando o schema base (idempotente) e aplicando upgrade se necessário.
    """
    conn = connection_factory()
    cur = conn.cursor()

    # 1. Forçar integridade referencial para permitir 'Cascade Controlado'
    cur.execute("PRAGMA foreign_keys = ON;")

    # 2. Garantir que a tabela config existe para versionamento
    cur.execute(
        """CREATE TABLE IF NOT EXISTS config(
        chave TEXT PRIMARY KEY,
        valor TEXT)"""
    )

    # 3. Schema base (idempotente — IF NOT EXISTS)
    _create_schema(cur)

    # 4. Verificar se banco legado precisa de upgrade (FKs para `anos`)
    if not _has_anos_fks(cur):
        logging.info("Banco legado detectado — aplicando upgrade para FKs `anos`...")
        _upgrade_to_anos(cur)
        logging.info("Upgrade para FKs `anos` concluído.")

    # 5. Remover unique legada de movimentações para permitir múltiplos lançamentos por mês.
    _migrate_movimentacoes_multiplas(cur)

    # 5b. Adicionar coluna conta_vinculada_id em rendimentos_locais (idempotente).
    _migrate_rendimentos_locais_conta_vinculada(cur)

    # 6. Atualizar schema_version para a versão corrente (1 = schema unificado)
    _update_schema_version(cur, 1)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Schema canónico
# ---------------------------------------------------------------------------

def _create_schema(cur):
    """
    Cria todas as tabelas na sua forma definitiva.
    `IF NOT EXISTS` garante idempotência.
    """

    # --- Tabela raiz: anos (fonte da verdade) ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS anos(
        ano INTEGER PRIMARY KEY)"""
    )

    # --- categorias ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS categorias(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        ordem INTEGER DEFAULT 0,
        inclui_fixas INTEGER DEFAULT 0,
        conta_vinculada_id INTEGER DEFAULT NULL,
        tooltip TEXT,
        ano INTEGER NOT NULL,
        is_cartao INTEGER DEFAULT 0,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )

    # --- despesas ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS despesas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        valor REAL NOT NULL,
        nota TEXT DEFAULT '',
        data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ignorar_total BOOLEAN DEFAULT 0,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )

    # --- receitas ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS receitas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        nota TEXT DEFAULT '',
        data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status INTEGER DEFAULT 0,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )

    # --- despesas_fixas_cartao ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS despesas_fixas_cartao(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        dia INTEGER DEFAULT 1,
        ativa INTEGER DEFAULT 1,
        cat_id INTEGER,
        ano INTEGER NOT NULL,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )

    # --- metas ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS metas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        ano_meta INTEGER NOT NULL,
        concluida INTEGER DEFAULT 0,
        ano_criacao INTEGER NOT NULL,
        FOREIGN KEY(ano_meta) REFERENCES anos(ano) ON DELETE CASCADE,
        FOREIGN KEY(ano_criacao) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )

    # --- contas_correntes (sem FK para anos — não tem coluna ano) ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS contas_correntes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        ordem INTEGER DEFAULT 0,
        saldo_inicial REAL DEFAULT 0)"""
    )

    # --- depositos_conta ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS depositos_conta(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        conta_id INTEGER NOT NULL,
        valor REAL NOT NULL DEFAULT 0,
        nota TEXT DEFAULT '',
        despesa_id INTEGER DEFAULT NULL,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )

    # --- movimentacoes_mensais ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS movimentacoes_mensais(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        conta_id INTEGER NOT NULL,
        valor REAL NOT NULL DEFAULT 0,
        nota TEXT DEFAULT '',
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_movimentacoes_ano_mes_conta ON movimentacoes_mensais(ano, mes, conta_id)"
    )

    # --- fixas_excecoes ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS fixas_excecoes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        cat_id INTEGER NOT NULL,
        UNIQUE(ano, mes, cat_id),
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )

    # --- pagamento_status ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS pagamento_status(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        status INTEGER DEFAULT 0,
        UNIQUE(ano, mes, categoria),
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )

    # --- rendimentos_realizados ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS rendimentos_realizados(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        status INTEGER DEFAULT 0,
        data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(ano, mes),
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )

    # --- rendimentos_locais ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS rendimentos_locais(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        nome TEXT NOT NULL,
        ordem INTEGER DEFAULT 0,
        projecao_taxa REAL DEFAULT NULL,
        conta_vinculada_id INTEGER DEFAULT NULL,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE,
        FOREIGN KEY(conta_vinculada_id) REFERENCES contas_correntes(id) ON DELETE SET NULL)"""
    )

    # --- rendimentos_lancamentos ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS rendimentos_lancamentos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        local_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        valor REAL NOT NULL DEFAULT 0,
        nota TEXT DEFAULT '',
        data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE,
        FOREIGN KEY(local_id) REFERENCES rendimentos_locais(id) ON DELETE CASCADE)"""
    )

    # --- fixas_aplicadas_manual ---
    cur.execute(
        """CREATE TABLE IF NOT EXISTS fixas_aplicadas_manual(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        fixa_id INTEGER NOT NULL,
        UNIQUE(ano, mes, fixa_id),
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )


# ---------------------------------------------------------------------------
# Detecção de banco legado
# ---------------------------------------------------------------------------

def _has_anos_fks(cur) -> bool:
    """
    Verifica se a tabela `despesas` já possui FK para `anos`.
    Se sim, assume-se que todas as tabelas filhas estão actualizadas.
    """
    fks = cur.execute("PRAGMA foreign_key_list(despesas)").fetchall()
    # fk[2] = nome da tabela referenciada
    return any(fk[2] == "anos" for fk in fks)


# ---------------------------------------------------------------------------
# Upgrade de bancos legados (sem FKs para `anos`)
# ---------------------------------------------------------------------------

def _upgrade_to_anos(cur):
    """
    Aplica FKs com ON DELETE CASCADE a todas as tabelas filhas,
    recriando-as.  SQLite não suporta ALTER TABLE ADD FOREIGN KEY.
    """

    # 1. Criar tabela `anos` (pode já existir em bancos que rodaram
    #    `_create_schema` mas não têm FKs — IF NOT EXISTS garante)
    cur.execute(
        """CREATE TABLE IF NOT EXISTS anos(
        ano INTEGER PRIMARY KEY)"""
    )

    # 2. Popular com todos os anos já existentes
    cur.execute(
        """INSERT OR IGNORE INTO anos(ano)
        SELECT DISTINCT ano FROM despesas
        UNION SELECT DISTINCT ano FROM receitas
        UNION SELECT DISTINCT ano FROM categorias
        UNION SELECT DISTINCT ano FROM despesas_fixas_cartao
        UNION SELECT DISTINCT ano FROM fixas_excecoes
        UNION SELECT DISTINCT ano FROM pagamento_status
        UNION SELECT DISTINCT ano FROM rendimentos_realizados
        UNION SELECT DISTINCT ano_meta FROM metas
        UNION SELECT DISTINCT ano_criacao FROM metas
        UNION SELECT DISTINCT ano FROM depositos_conta
        UNION SELECT DISTINCT ano FROM movimentacoes_mensais
        UNION SELECT DISTINCT ano FROM rendimentos_locais
        UNION SELECT DISTINCT ano FROM rendimentos_lancamentos
        UNION SELECT DISTINCT ano FROM fixas_aplicadas_manual"""
    )

    # 3. Recriar tabelas filhas com FKs.
    #    Ordem: independentes primeiro; `rendimentos_locais` antes de
    #    `rendimentos_lancamentos` (FK entre elas).
    _recreate_with_fk(
        cur, "categorias",
        """CREATE TABLE categorias(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        ordem INTEGER DEFAULT 0,
        inclui_fixas INTEGER DEFAULT 0,
        conta_vinculada_id INTEGER DEFAULT NULL,
        tooltip TEXT,
        ano INTEGER NOT NULL,
        is_cartao INTEGER DEFAULT 0,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)""",
    )

    _recreate_with_fk(
        cur, "despesas",
        """CREATE TABLE despesas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        valor REAL NOT NULL,
        nota TEXT DEFAULT '',
        data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ignorar_total BOOLEAN DEFAULT 0,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)""",
    )

    _recreate_with_fk(
        cur, "receitas",
        """CREATE TABLE receitas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        nota TEXT DEFAULT '',
        data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status INTEGER DEFAULT 0,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)""",
    )

    _recreate_with_fk(
        cur, "despesas_fixas_cartao",
        """CREATE TABLE despesas_fixas_cartao(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        dia INTEGER DEFAULT 1,
        ativa INTEGER DEFAULT 1,
        cat_id INTEGER,
        ano INTEGER NOT NULL,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)""",
    )

    _recreate_with_fk(
        cur, "metas",
        """CREATE TABLE metas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        ano_meta INTEGER NOT NULL,
        concluida INTEGER DEFAULT 0,
        ano_criacao INTEGER NOT NULL,
        FOREIGN KEY(ano_meta) REFERENCES anos(ano) ON DELETE CASCADE,
        FOREIGN KEY(ano_criacao) REFERENCES anos(ano) ON DELETE CASCADE)""",
    )

    _recreate_with_fk(
        cur, "depositos_conta",
        """CREATE TABLE depositos_conta(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        conta_id INTEGER NOT NULL,
        valor REAL NOT NULL DEFAULT 0,
        nota TEXT DEFAULT '',
        despesa_id INTEGER DEFAULT NULL,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)""",
    )

    _recreate_with_fk(
        cur, "movimentacoes_mensais",
        """CREATE TABLE movimentacoes_mensais(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        conta_id INTEGER NOT NULL,
        valor REAL NOT NULL DEFAULT 0,
        nota TEXT DEFAULT '',
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)""",
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_movimentacoes_ano_mes_conta ON movimentacoes_mensais(ano, mes, conta_id)"
    )

    _recreate_with_fk(
        cur, "fixas_excecoes",
        """CREATE TABLE fixas_excecoes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        cat_id INTEGER NOT NULL,
        UNIQUE(ano, mes, cat_id),
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)""",
    )

    _recreate_with_fk(
        cur, "pagamento_status",
        """CREATE TABLE pagamento_status(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        status INTEGER DEFAULT 0,
        UNIQUE(ano, mes, categoria),
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)""",
    )

    _recreate_with_fk(
        cur, "rendimentos_realizados",
        """CREATE TABLE rendimentos_realizados(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        status INTEGER DEFAULT 0,
        data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(ano, mes),
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)""",
    )

    _recreate_with_fk(
        cur, "fixas_aplicadas_manual",
        """CREATE TABLE fixas_aplicadas_manual(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        fixa_id INTEGER NOT NULL,
        UNIQUE(ano, mes, fixa_id),
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)""",
    )

    # `rendimentos_locais` ANTES de `rendimentos_lancamentos`
    # porque a segunda tem FK para a primeira.
    _recreate_with_fk(
        cur, "rendimentos_locais",
        """CREATE TABLE rendimentos_locais(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        nome TEXT NOT NULL,
        ordem INTEGER DEFAULT 0,
        projecao_taxa REAL DEFAULT NULL,
        conta_vinculada_id INTEGER DEFAULT NULL,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE,
        FOREIGN KEY(conta_vinculada_id) REFERENCES contas_correntes(id) ON DELETE SET NULL)""",
        columns=["id", "ano", "nome", "ordem", "projecao_taxa"],
    )

    _recreate_with_fk(
        cur, "rendimentos_lancamentos",
        """CREATE TABLE rendimentos_lancamentos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        local_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        valor REAL NOT NULL DEFAULT 0,
        nota TEXT DEFAULT '',
        data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE,
        FOREIGN KEY(local_id) REFERENCES rendimentos_locais(id) ON DELETE CASCADE)""",
    )


def _recreate_with_fk(cur, table: str, create_sql: str, columns: list[str] | None = None):
    """
    Recria `table` com a nova definição (que inclui FK para `anos`).
    Preserva todos os dados existentes. Quando `columns` é informado,
    a cópia é restrita a essas colunas (necessário quando a recriação
    introduz colunas novas inexistentes na tabela legada).
    """
    old = f"{table}_old"
    cur.execute(f"ALTER TABLE {table} RENAME TO {old}")
    cur.execute(create_sql)
    if columns:
        col_list = ",".join(columns)
        cur.execute(f"INSERT INTO {table}({col_list}) SELECT {col_list} FROM {old}")
    else:
        cur.execute(f"INSERT INTO {table} SELECT * FROM {old}")
    cur.execute(f"DROP TABLE {old}")
    logging.info("Tabela %s recriada com FK para `anos`.", table)


def _migrate_rendimentos_locais_conta_vinculada(cur):
    """
    Acrescenta a coluna `conta_vinculada_id` em rendimentos_locais
    quando ausente (bancos atualizados antes da feature de reflexo
    do rendimento na conta corrente). Não recria a tabela: ALTER TABLE
    ADD COLUMN é suficiente porque o vínculo é nullable.
    """
    cols = [row[1] for row in cur.execute("PRAGMA table_info('rendimentos_locais')").fetchall()]
    if "conta_vinculada_id" in cols:
        return
    cur.execute(
        "ALTER TABLE rendimentos_locais ADD COLUMN conta_vinculada_id INTEGER DEFAULT NULL"
    )
    logging.info("Coluna conta_vinculada_id adicionada em rendimentos_locais.")


def _migrate_movimentacoes_multiplas(cur):
    """
    Remove constraints UNIQUE legadas de movimentacoes_mensais.
    A regra atual permite vários lançamentos no mesmo ano/mês/conta.
    """
    unique_cols = []
    for idx in cur.execute("PRAGMA index_list('movimentacoes_mensais')").fetchall():
        is_unique = idx[2]
        if not is_unique:
            continue
        idx_name = idx[1]
        cols = [
            row[2]
            for row in cur.execute(f"PRAGMA index_info('{idx_name}')").fetchall()
        ]
        unique_cols.append(tuple(cols))

    if ("ano", "mes") not in unique_cols and ("ano", "mes", "conta_id") not in unique_cols:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_movimentacoes_ano_mes_conta ON movimentacoes_mensais(ano, mes, conta_id)"
        )
        return

    old = "movimentacoes_mensais_old_multi"
    cur.execute(f"DROP TABLE IF EXISTS {old}")
    cur.execute(f"ALTER TABLE movimentacoes_mensais RENAME TO {old}")
    cur.execute(
        """CREATE TABLE movimentacoes_mensais(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        conta_id INTEGER NOT NULL,
        valor REAL NOT NULL DEFAULT 0,
        nota TEXT DEFAULT '',
        FOREIGN KEY(ano) REFERENCES anos(ano) ON DELETE CASCADE)"""
    )
    cur.execute(
        f"""INSERT INTO movimentacoes_mensais(id,ano,mes,conta_id,valor,nota)
        SELECT id,ano,mes,conta_id,valor,nota FROM {old}"""
    )
    cur.execute(f"DROP TABLE {old}")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_movimentacoes_ano_mes_conta ON movimentacoes_mensais(ano, mes, conta_id)"
    )
    logging.info("Tabela movimentacoes_mensais migrada para múltiplos lançamentos.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _update_schema_version(cur, version: int):
    cur.execute(
        """INSERT INTO config (chave, valor)
        VALUES ('schema_version', ?)
        ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor""",
        (str(version),),
    )
    logging.info("Schema version actualizado para %s.", version)
