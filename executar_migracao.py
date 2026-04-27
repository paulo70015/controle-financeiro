#!/usr/bin/env python3
"""
Script para executar migração: criar tabela fixas_aplicadas_manual
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from financeiro.infrastructure.supabase.client import get_supabase

def executar_migracao():
    print("=" * 60)
    print("MIGRAÇÃO: Criar tabela fixas_aplicadas_manual")
    print("=" * 60)
    
    try:
        client = get_supabase()
        print("\n✓ Conectado ao Supabase")
        
        # Ler o arquivo SQL
        with open('specs/migration-fixas-aplicadas-manual.sql', 'r', encoding='utf-8') as f:
            sql = f.read()
        
        print("\n📄 SQL a ser executado:")
        print("-" * 60)
        print(sql)
        print("-" * 60)
        
        # Supabase não suporta executar SQL diretamente via client Python
        # Precisamos usar a API REST do PostgREST ou o SQL Editor
        print("\n⚠️  ATENÇÃO:")
        print("O cliente Python do Supabase não suporta executar SQL DDL diretamente.")
        print("\nPor favor, execute MANUALMENTE no Supabase Dashboard:")
        print("\n1. Acesse: https://supabase.com/dashboard")
        print("2. Selecione seu projeto")
        print("3. Vá em 'SQL Editor' no menu lateral")
        print("4. Clique em 'New Query'")
        print("5. Cole o SQL acima")
        print("6. Clique em 'Run' (ou Ctrl+Enter)")
        print("\nOu copie e execute este comando SQL:")
        print("\n" + "=" * 60)
        print("""
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
""")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        return False
    
    return True

if __name__ == "__main__":
    executar_migracao()
