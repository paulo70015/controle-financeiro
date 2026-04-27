import logging

def init_db(connection_factory):
    """
    Inicializa o banco de dados, ativando chaves estrangeiras 
    e executando migrações sequenciais baseadas no schema_version.
    """
    conn = connection_factory()
    cur = conn.cursor()
    
    # 1. Forçar integridade referencial para permitir 'Cascade Controlado'
    cur.execute('PRAGMA foreign_keys = ON;')
    
    # 2. Garantir que a tabela config existe primeiro para versionamento
    cur.execute("""CREATE TABLE IF NOT EXISTS config(chave TEXT PRIMARY KEY, valor TEXT)""")
    
    # 3. Obter a versão atual do schema
    cur.execute("SELECT valor FROM config WHERE chave = 'schema_version'")
    row = cur.fetchone()
    
    # Em sqlite3.Row nativo, precisamos acessar por índice ou chave, se configurado. 
    # Como o tipo de row pode variar, lidamos com isso de forma segura:
    current_version = int(row[0]) if row else 0
    
    logging.info(f"Iniciando DB. schema_version atual: {current_version}")
    
    # 4. Executar migrações de forma sequencial
    try:
        if current_version < 1:
            _migration_v1(cur)
            _update_schema_version(cur, 1)
        
        if current_version < 2:
            _migration_v2(cur)
            _update_schema_version(cur, 2)
            
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Falha ao migrar o banco de dados: {e}")
        raise
    finally:
        conn.close()

def _update_schema_version(cur, version: int):
    cur.execute("""
        INSERT INTO config (chave, valor) 
        VALUES ('schema_version', ?) 
        ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
    """, (str(version),))
    logging.info(f"Schema do banco atualizado com sucesso para versão {version}")

def _migration_v1(cur):
    """
    Migração inicial - Base V1. 
    Contém a modelagem canônica obrigatória do Flutter.
    """
    cur.execute(
        """CREATE TABLE IF NOT EXISTS categorias(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL, 
        ordem INTEGER DEFAULT 0,
        inclui_fixas INTEGER DEFAULT 0,
        conta_vinculada_id INTEGER DEFAULT NULL, 
        tooltip TEXT, 
        ano INTEGER NOT NULL)"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS despesas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL, 
        mes INTEGER NOT NULL, 
        categoria TEXT NOT NULL, 
        valor REAL NOT NULL, 
        nota TEXT DEFAULT '', 
        data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        ignorar_total BOOLEAN DEFAULT 0)"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS receitas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL, 
        mes INTEGER NOT NULL, 
        descricao TEXT NOT NULL, 
        valor REAL NOT NULL, 
        nota TEXT DEFAULT '', 
        data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        status INTEGER DEFAULT 0)"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS despesas_fixas_cartao(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL, valor REAL NOT NULL, dia INTEGER DEFAULT 1, ativa INTEGER DEFAULT 1, cat_id INTEGER, ano INTEGER NOT NULL)"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS metas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL, valor REAL NOT NULL, ano_meta INTEGER NOT NULL, concluida INTEGER DEFAULT 0, ano_criacao INTEGER NOT NULL)"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS contas_correntes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE, ordem INTEGER DEFAULT 0, saldo_inicial REAL DEFAULT 0)"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS depositos_conta(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL, mes INTEGER NOT NULL, conta_id INTEGER NOT NULL,
        valor REAL NOT NULL DEFAULT 0, nota TEXT DEFAULT '', despesa_id INTEGER DEFAULT NULL)"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS movimentacoes_mensais(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL, mes INTEGER NOT NULL, conta_id INTEGER NOT NULL,
        valor REAL NOT NULL DEFAULT 0, nota TEXT DEFAULT '', UNIQUE(ano, mes))"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS fixas_excecoes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL, mes INTEGER NOT NULL, cat_id INTEGER NOT NULL, UNIQUE(ano, mes, cat_id))"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS pagamento_status(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL, mes INTEGER NOT NULL, categoria TEXT NOT NULL, status INTEGER DEFAULT 0, UNIQUE(ano, mes, categoria))"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS rendimentos_locais(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL, nome TEXT NOT NULL, ordem INTEGER DEFAULT 0, projecao_taxa REAL DEFAULT NULL)"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS rendimentos_lancamentos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL, mes INTEGER NOT NULL, local_id INTEGER NOT NULL,
        tipo TEXT NOT NULL, valor REAL NOT NULL DEFAULT 0, nota TEXT DEFAULT '', data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(local_id) REFERENCES rendimentos_locais(id) ON DELETE CASCADE)"""
    )

def _migration_v2(cur):
    """
    Migração V2 - Adiciona suporte a fixas aplicadas manualmente e ajusta restrição de movimentações.
    """
    cur.execute(
        """CREATE TABLE IF NOT EXISTS fixas_aplicadas_manual(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL, mes INTEGER NOT NULL, fixa_id INTEGER NOT NULL, UNIQUE(ano, mes, fixa_id))"""
    )
    
    # Recria a tabela movimentacoes_mensais com a constraint UNIQUE correta
    cur.execute(
        """CREATE TABLE IF NOT EXISTS movimentacoes_mensais_new(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ano INTEGER NOT NULL, mes INTEGER NOT NULL, conta_id INTEGER NOT NULL,
        valor REAL NOT NULL DEFAULT 0, nota TEXT DEFAULT '', UNIQUE(ano, mes, conta_id))"""
    )
    cur.execute("INSERT INTO movimentacoes_mensais_new (id, ano, mes, conta_id, valor, nota) SELECT id, ano, mes, conta_id, valor, nota FROM movimentacoes_mensais")
    cur.execute("DROP TABLE movimentacoes_mensais")
    cur.execute("ALTER TABLE movimentacoes_mensais_new RENAME TO movimentacoes_mensais")