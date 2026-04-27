-- ============================================
-- MIGRAÇÃO: Adicionar tabela fixas_aplicadas_manual
-- Data: 2026-04-23
-- Descrição: Permite marcar fixas como aplicadas manualmente
-- ============================================

-- Criar tabela
CREATE TABLE IF NOT EXISTS fixas_aplicadas_manual (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    fixa_id INTEGER NOT NULL,
    data_aplicacao TIMESTAMP DEFAULT NOW(),
    UNIQUE(ano, mes, fixa_id)
);

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_fixas_aplicadas_ano_mes ON fixas_aplicadas_manual(ano, mes);
CREATE INDEX IF NOT EXISTS idx_fixas_aplicadas_fixa_id ON fixas_aplicadas_manual(fixa_id);

-- Adicionar comentário
COMMENT ON TABLE fixas_aplicadas_manual IS 'Fixas marcadas como aplicadas manualmente (antes do dia esperado)';

-- Verificar se a tabela foi criada
SELECT 'Tabela fixas_aplicadas_manual criada com sucesso!' as status;
