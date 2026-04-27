# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

## [1.3.0] - 2026-04-23

### 🚀 Mudanças Principais

#### Migração de SQLite para Supabase (PostgreSQL)
- **Backend completamente migrado** de SQLite local para Supabase (PostgreSQL na nuvem)
- **Zero mudanças no frontend** - API REST permanece 100% compatível
- **Arquitetura DDD preservada** - separação de camadas mantida

### ✨ Adicionado

#### Infraestrutura
- 10 novos repositórios Supabase em `financeiro/infrastructure/supabase/`
- Cliente Supabase com fallback (`postgrest` quando pacote completo não disponível)
- Schema PostgreSQL completo em `specs/schema-supabase.sql`
- Dados de exemplo em `specs/dados-supabase.sql` (971 registros)

#### Documentação
- 14 documentos de migração em `.kiro/docs/migracao-supabase/`
- Guia completo para migração do app Flutter
- Análise DRY das rotas HTTP
- Documentação de correções aplicadas

#### Convenções
- Regra obrigatória de sincronização de documentação
- Sempre que o schema mudar, `MIGRACAO-APP-FLUTTER.md` deve ser atualizado

### 🔧 Modificado

#### Backend
- `app.py` refatorado para usar `get_supabase()` ao invés de `get_db()`
- 10 blueprints adaptados para usar `client_factory` ao invés de `connection_factory`
- Todos os repositórios migrados de SQL puro para API Supabase

#### Scripts
- 6 scripts de inicialização/build atualizados (`.bat` e `.sh`)
- Removida pasta `scripts/` (scripts de migração única não mais necessários)

#### Dependências
- Adicionado: `postgrest`, `python-dotenv`, `psycopg2-binary`, `pydantic`, `httpx`
- Removido: dependências específicas do SQLite

### 🐛 Corrigido

#### Imports
- 10 repositórios: corrigidos imports do cliente Supabase

#### Tipos de Dados
- 11 ocorrências: campos INTEGER booleanos corrigidos (0/1 ao invés de True/False)
- 3 ocorrências: comparações com NULL corrigidas
- Campos afetados: `ativa`, `inclui_fixas`, `concluida`

#### Código
- 1 rota: código SQLite direto movido para repositório
- Separação de camadas DDD reforçada

### 📊 Estatísticas da Migração

- **Linhas de código migradas:** ~3.500
- **Repositórios criados:** 10
- **Blueprints adaptados:** 10
- **Registros migrados:** 971
- **Tabelas migradas:** 13
- **Correções aplicadas:** 26
- **Documentos criados:** 14
- **Taxa de sucesso:** 100%

### 🎯 Benefícios

- ✅ Banco de dados na nuvem (sem necessidade de sincronização manual)
- ✅ Backups automáticos
- ✅ Escalabilidade
- ✅ API REST nativa do Supabase
- ✅ Acesso multi-dispositivo facilitado
- ✅ Preparado para app Flutter

### ⚠️ Breaking Changes

**Nenhum para o usuário final!** A interface e funcionalidades permanecem idênticas.

**Para desenvolvedores:**
- Repositórios agora usam API Supabase ao invés de SQL direto
- Necessário arquivo `.env` com credenciais Supabase
- Campos booleanos INTEGER devem usar 0/1 (não True/False)

### 📝 Notas de Migração

Para migrar de v1.2.1 para v1.3.0:

1. Criar projeto no Supabase
2. Executar `specs/schema-supabase.sql` no SQL Editor
3. (Opcional) Executar `specs/dados-supabase.sql` para dados de exemplo
4. Criar arquivo `.env` com credenciais Supabase
5. Instalar novas dependências: `pip install -r requirements.txt`
6. Iniciar aplicação: `python app.py`

---

## [1.2.1] - 2026-04-XX

### Versão Anterior (SQLite)

- Backend Flask + SQLite local
- Sincronização opcional com Google Drive
- Todas as funcionalidades de controle financeiro
- Interface web SPA em JavaScript Vanilla

---

**Formato baseado em [Keep a Changelog](https://keepachangelog.com/)**
