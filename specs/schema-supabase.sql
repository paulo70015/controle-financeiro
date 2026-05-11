-- ============================================
-- Schema PostgreSQL para Supabase v1.3.0
-- Migração de SQLite → PostgreSQL
-- ============================================

-- Ativar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Tabela: config
-- Armazena configurações chave-valor (ex: schema_version)
-- ============================================
CREATE TABLE IF NOT EXISTS config (
    chave TEXT PRIMARY KEY,
    valor TEXT
);

-- Inserir versão inicial do schema
INSERT INTO config (chave, valor) 
VALUES ('schema_version', '1')
ON CONFLICT (chave) DO NOTHING;

-- Inserir dia de início do mês fiscal (padrão: 25)
INSERT INTO config (chave, valor) 
VALUES ('dia_inicio_mes_fiscal', '25')
ON CONFLICT (chave) DO NOTHING;

-- ============================================
-- Tabela: categorias
-- Categorias de despesas por ano
-- ============================================
CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    ordem INTEGER DEFAULT 0,
    inclui_fixas INTEGER DEFAULT 0,
    conta_vinculada_id INTEGER DEFAULT NULL,
    tooltip TEXT,
    ano INTEGER NOT NULL,
    is_cartao INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_categorias_ano ON categorias(ano);
CREATE INDEX IF NOT EXISTS idx_categorias_ordem ON categorias(ordem);

-- ============================================
-- Tabela: despesas
-- Lançamentos de despesas
-- ============================================
CREATE TABLE IF NOT EXISTS despesas (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    categoria TEXT NOT NULL,
    valor NUMERIC(10,2) NOT NULL,
    nota TEXT DEFAULT '',
    data_alteracao TIMESTAMP DEFAULT NOW(),
    ignorar_total BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_despesas_ano_mes ON despesas(ano, mes);
CREATE INDEX IF NOT EXISTS idx_despesas_categoria ON despesas(categoria);

-- ============================================
-- Tabela: receitas
-- Lançamentos de receitas
-- ============================================
CREATE TABLE IF NOT EXISTS receitas (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    descricao TEXT NOT NULL,
    valor NUMERIC(10,2) NOT NULL,
    nota TEXT DEFAULT '',
    data_alteracao TIMESTAMP DEFAULT NOW(),
    status INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_receitas_ano_mes ON receitas(ano, mes);

-- ============================================
-- Tabela: despesas_fixas_cartao
-- Despesas fixas recorrentes
-- ============================================
CREATE TABLE IF NOT EXISTS despesas_fixas_cartao (
    id SERIAL PRIMARY KEY,
    descricao TEXT NOT NULL,
    valor NUMERIC(10,2) NOT NULL,
    dia INTEGER DEFAULT 1,
    ativa INTEGER DEFAULT 1,
    cat_id INTEGER,
    ano INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fixas_ano ON despesas_fixas_cartao(ano);
CREATE INDEX IF NOT EXISTS idx_fixas_cat_id ON despesas_fixas_cartao(cat_id);

-- ============================================
-- Tabela: fixas_excecoes
-- Exceções de fixas por mês (não deletar fixa, apenas ocultar)
-- ============================================
CREATE TABLE IF NOT EXISTS fixas_excecoes (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    cat_id INTEGER NOT NULL,
    UNIQUE(ano, mes, cat_id)
);

CREATE INDEX IF NOT EXISTS idx_fixas_excecoes_ano_mes ON fixas_excecoes(ano, mes);

-- ============================================
-- Tabela: fixas_aplicadas_manual
-- Fixas marcadas como aplicadas manualmente (antes do dia esperado)
-- ============================================
CREATE TABLE IF NOT EXISTS fixas_aplicadas_manual (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    fixa_id INTEGER NOT NULL,
    data_aplicacao TIMESTAMP DEFAULT NOW(),
    UNIQUE(ano, mes, fixa_id)
);

CREATE INDEX IF NOT EXISTS idx_fixas_aplicadas_ano_mes ON fixas_aplicadas_manual(ano, mes);
CREATE INDEX IF NOT EXISTS idx_fixas_aplicadas_fixa_id ON fixas_aplicadas_manual(fixa_id);

-- ============================================
-- Tabela: pagamento_status
-- Status de pagamento por célula (ano × mes × categoria)
-- ============================================
CREATE TABLE IF NOT EXISTS pagamento_status (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    categoria TEXT NOT NULL,
    status INTEGER DEFAULT 0,
    UNIQUE(ano, mes, categoria)
);

CREATE INDEX IF NOT EXISTS idx_pagamento_status_ano_mes ON pagamento_status(ano, mes);

-- ============================================
-- Tabela: metas
-- Metas financeiras
-- ============================================
CREATE TABLE IF NOT EXISTS metas (
    id SERIAL PRIMARY KEY,
    descricao TEXT NOT NULL,
    valor NUMERIC(10,2) NOT NULL,
    ano_meta INTEGER NOT NULL,
    concluida INTEGER DEFAULT 0,
    ano_criacao INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_metas_ano_meta ON metas(ano_meta);

-- ============================================
-- Tabela: contas_correntes
-- Contas bancárias
-- ============================================
CREATE TABLE IF NOT EXISTS contas_correntes (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    ordem INTEGER DEFAULT 0,
    saldo_inicial NUMERIC(10,2) DEFAULT 0
);

-- ============================================
-- Tabela: depositos_conta
-- Depósitos e saques em contas correntes
-- ============================================
CREATE TABLE IF NOT EXISTS depositos_conta (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    conta_id INTEGER NOT NULL,
    valor NUMERIC(10,2) NOT NULL DEFAULT 0,
    nota TEXT DEFAULT '',
    despesa_id INTEGER DEFAULT NULL,
    FOREIGN KEY (conta_id) REFERENCES contas_correntes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_depositos_ano_mes ON depositos_conta(ano, mes);
CREATE INDEX IF NOT EXISTS idx_depositos_conta_id ON depositos_conta(conta_id);

-- ============================================
-- Tabela: movimentacoes_mensais
-- Movimentações mensais consolidadas
-- ============================================
CREATE TABLE IF NOT EXISTS movimentacoes_mensais (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    conta_id INTEGER NOT NULL,
    valor NUMERIC(10,2) NOT NULL DEFAULT 0,
    nota TEXT DEFAULT '',
    UNIQUE(ano, mes),
    FOREIGN KEY (conta_id) REFERENCES contas_correntes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_movimentacoes_ano_mes ON movimentacoes_mensais(ano, mes);

-- ============================================
-- Tabela: rendimentos_locais
-- Locais de investimento/rendimento por ano
-- ============================================
CREATE TABLE IF NOT EXISTS rendimentos_locais (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    nome TEXT NOT NULL,
    ordem INTEGER DEFAULT 0,
    projecao_taxa NUMERIC(5,2) DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_rendimentos_locais_ano ON rendimentos_locais(ano);

-- ============================================
-- Tabela: rendimentos_lancamentos
-- Aportes e rendimentos por local
-- ============================================
CREATE TABLE IF NOT EXISTS rendimentos_lancamentos (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    local_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    valor NUMERIC(10,2) NOT NULL DEFAULT 0,
    nota TEXT DEFAULT '',
    data_alteracao TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (local_id) REFERENCES rendimentos_locais(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rendimentos_lancamentos_ano_mes ON rendimentos_lancamentos(ano, mes);
CREATE INDEX IF NOT EXISTS idx_rendimentos_lancamentos_local_id ON rendimentos_lancamentos(local_id);

-- ============================================
-- Políticas RLS (Row Level Security)
-- Desabilitadas por padrão (app usa service_role key)
-- ============================================
-- ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE despesas ENABLE ROW LEVEL SECURITY;
-- ... (adicionar conforme necessidade futura)

-- ============================================
-- Comentários nas tabelas (documentação)
-- ============================================
COMMENT ON TABLE categorias IS 'Categorias de despesas por ano';
COMMENT ON TABLE despesas IS 'Lançamentos de despesas';
COMMENT ON TABLE receitas IS 'Lançamentos de receitas';
COMMENT ON TABLE despesas_fixas_cartao IS 'Despesas fixas recorrentes';
COMMENT ON TABLE fixas_excecoes IS 'Exceções de fixas por mês (ocultar sem deletar)';
COMMENT ON TABLE pagamento_status IS 'Status de pagamento por célula (ano × mes × categoria)';
COMMENT ON TABLE metas IS 'Metas financeiras';
COMMENT ON TABLE contas_correntes IS 'Contas bancárias';
COMMENT ON TABLE depositos_conta IS 'Depósitos e saques em contas correntes';
COMMENT ON TABLE movimentacoes_mensais IS 'Movimentações mensais consolidadas';
COMMENT ON TABLE rendimentos_locais IS 'Locais de investimento/rendimento por ano';
COMMENT ON TABLE rendimentos_lancamentos IS 'Aportes e rendimentos por local';

-- ============================================
-- Funções auxiliares (opcional)
-- ============================================

-- Função para obter próximo ano disponível
CREATE OR REPLACE FUNCTION proximo_ano_disponivel()
RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE((SELECT MAX(ano) FROM categorias), EXTRACT(YEAR FROM NOW())::INTEGER);
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Triggers (opcional - para auditoria futura)
-- ============================================

-- Trigger para atualizar data_alteracao automaticamente
CREATE OR REPLACE FUNCTION atualizar_data_alteracao()
RETURNS TRIGGER AS $$
BEGIN
    NEW.data_alteracao = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger em despesas
CREATE TRIGGER trigger_despesas_data_alteracao
BEFORE UPDATE ON despesas
FOR EACH ROW
EXECUTE FUNCTION atualizar_data_alteracao();

-- Aplicar trigger em receitas
CREATE TRIGGER trigger_receitas_data_alteracao
BEFORE UPDATE ON receitas
FOR EACH ROW
EXECUTE FUNCTION atualizar_data_alteracao();

-- Aplicar trigger em rendimentos_lancamentos
CREATE TRIGGER trigger_rendimentos_data_alteracao
BEFORE UPDATE ON rendimentos_lancamentos
FOR EACH ROW
EXECUTE FUNCTION atualizar_data_alteracao();

-- ============================================
-- Fim do Schema
-- ============================================
