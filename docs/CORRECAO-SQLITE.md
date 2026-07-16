# Correção do Modo SQLite

## Problema Identificado

O modo SQLite estava quebrado devido à ausência do módulo `financeiro.infrastructure.runtime.paths`, que era importado pelo `repository_factory.py` mas não existia no código.

**Erro original:**
```
ModuleNotFoundError: No module named 'financeiro.infrastructure.runtime.paths'
```

## Solução Implementada

### 1. Criação do módulo `paths.py`

Arquivo: `financeiro/infrastructure/runtime/paths.py`

Implementa duas funções essenciais:

- **`get_base_dir()`**: Retorna o diretório base da aplicação
  - PyInstaller: `sys._MEIPASS` (arquivos embutidos temporários)
  - Dev: diretório raiz do projeto

- **`get_data_dir()`**: Retorna o diretório de dados persistentes
  - PyInstaller: pasta onde o `.exe` está rodando
  - Dev: diretório raiz do projeto

### 2. Integração com `repository_factory.py`

O factory já estava preparado para usar o módulo, apenas faltava a implementação:

```python
from financeiro.infrastructure.runtime.paths import get_data_dir

def _get_sqlite_connection():
    db_path = Path(get_data_dir()) / "financeiro.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn
```

## Validação

Todos os repositórios SQLite foram testados e estão funcionando:

```
✓ Despesas             - OK
✓ Receitas             - OK
✓ Categorias           - OK
✓ Contas               - OK
✓ Planejamento         - OK
✓ Rendimentos          - OK
✓ Dashboard            - OK
✓ Admin                - OK
✓ Home                 - OK
✓ CSV                  - OK
```

## Como Usar

### Modo Desenvolvimento

```bash
# Criar/usar .env com DB_MODE=sqlite
DB_MODE=sqlite

# Executar aplicação
python app.py --show-console
```

### Build Standalone

```bash
# Gerar executável com SQLite embutido
scripts\construir.bat --com-sqlite
```

O executável gerado:
- Funciona imediatamente, sem configuração
- Cria o banco `financeiro.db` automaticamente na primeira execução
- Cada usuário tem seu próprio banco local
- Ideal para compartilhar

## Estrutura de Arquivos

```
financeiro/
└── infrastructure/
    ├── runtime/
    │   ├── __init__.py
    │   ├── paths.py          ← NOVO (correção)
    │   └── tray.py
    ├── sqlite/
    │   ├── schema.py         ← Inicialização do banco
    │   └── *_repository.py   ← Repositórios SQLite
    └── repository_factory.py ← Factory que usa paths.py
```

## Status Atual

✅ **SQLite totalmente funcional**
- Modo dev: OK
- Build standalone: OK
- Todos os repositórios: OK
- Criação automática do banco: OK

✅ **Supabase continua funcionando**
- Modo padrão da aplicação
- Sem impacto nas funcionalidades existentes

## Arquivos Relacionados

- `financeiro/infrastructure/runtime/paths.py` - Helper de paths (NOVO)
- `financeiro/infrastructure/repository_factory.py` - Factory de repositórios
- `.env.sqlite` - Configuração para modo SQLite
- `scripts\construir.bat` - Script de build com opção `--com-sqlite`
- `test_sqlite_mode.py` - Teste de integridade (NOVO)
