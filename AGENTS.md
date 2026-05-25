# AGENTS.md

## Contexto do Projeto

Este projeto e o Controle Financeiro Pessoal v1.3.0.

Antes de alterar codigo, leia quando relevante:
- `.kiro/steering/project-context.md`
- `.kiro/steering/conventions.md`

Para mudancas relacionadas a Supabase, SQLite, schema, Flutter ou migracao, consulte tambem:
- `.kiro/docs/migracao-supabase/`
- `specs/`
- `docs/`

## Regras Principais

- **Proteger o arquivo `.env`**: Ele contém credenciais de produção (Supabase). Regras por contexto:
  - **Build** (`construir_macos.sh --com-env`, `construir.bat --com-env`): pode LER e COPIAR o `.env` para dentro do executável. O original nunca é alterado.
  - **Runtime** (`app.py`): pode LER o `.env` via `load_dotenv`, respeitando `DB_MODE` definido no ambiente como prioritário.
  - **Testes e scripts auxiliares**: PROIBIDO ler, escrever, renomear, copiar ou deletar o `.env`. Testes usam SQLite hardcoded e nunca precisam deste arquivo.
- **Testes sempre usam SQLite hardcoded**: Todos os testes forçam `os.environ["DB_MODE"] = "sqlite"` no topo do módulo, antes de qualquer import do projeto. Nenhum teste pode depender de `.env`, `load_dotenv`, ou env var externa para escolher o banco. SQLite é a única opção, sempre.
- Backend: Python 3.10+ e Flask.
- Frontend: HTML, CSS e JavaScript Vanilla. Nao sugerir React, Vue, Svelte, jQuery ou frameworks externos.
- Manter arquitetura DDD simplificada:
  - `financeiro/domain/`: entidades e regras puras.
  - `financeiro/application/`: use cases e orquestracao de negocio.
  - `financeiro/infrastructure/`: banco de dados e servicos externos.
  - `financeiro/interfaces/http/`: rotas Flask sem regra de negocio.
- Interface, alertas e mensagens voltadas ao usuario devem ficar em PT-BR.
- Nao renomear tabelas ou colunas existentes sem necessidade explicita.
- Preservar compatibilidade com runtime PyInstaller.
- Nao criar rotas de gravacao que alterem arquivos no `BASE_DIR` em producao.
- Sempre verificar nulidade antes de manipular elementos DOM.
- Aplicar DRY rigorosamente no backend e no frontend.

## Fluxo Para Funcionalidades Backend

Ao criar ou alterar funcionalidade que envolva backend, seguir este fluxo:

1. Repository: criar ou adaptar metodo no `*_repository.py`.
2. Use Case: atualizar regra em `use_cases.py`.
3. Route: expor via blueprint Flask em `*_routes.py`.
4. JS Module: conectar no modulo correspondente em `static/js/modules/`.

## Regras de Negocio Criticas

- Fixas com excecoes: ao apagar uma fixa de um mes especifico, inserir em `fixas_excecoes`; nao deletar a fixa recorrente.
- Status de pagamento pertence a celula `(ano, mes, categoria)`, nao a uma despesa individual.
- Rendimentos usam saldo acumulado: `Saldo(N) = Saldo(N-1) + Aporte(N) + Rendimento(N)`.
- Ao criar, editar ou duplicar fixas entre anos, remapear `cat_id` para categoria homonima no ano de destino.
- Modais de detalhe usam Lazy Commit com filas locais; gravacao/delecao efetiva ocorre no fechamento do modal.
- Requisicoes de `load()` devem proteger contra race condition com identificador sequencial.

## Testes

**⚠️ Antes de rodar QUALQUER teste, pergunte ao utilizador.** O ambiente pode estar
com Supabase ativo ou a aplicação em execução, e rodar testes sem aviso pode causar
conflitos ou perda de dados. Nunca assuma que é seguro rodar testes sem confirmação.

Apos alteracoes relevantes, **pergunte antes** de rodar os testes aplicaveis:

### Testes unitarios / integracao
- `python test_suite.py`
- `python test_sqlite_mode.py`
- `python test_dependencies_compatibility.py`

### Testes E2E com Playwright

Os testes de ponta a ponta usam **Playwright** com **Chromium headless** e rodam
contra um servidor Flask efemero com SQLite temporario. **Nunca tocam no Supabase**
— o `DB_MODE=sqlite` e forcado pelos scripts.

| Sistema     | Comando                                |
|-------------|----------------------------------------|
| macOS/Linux | `bash test_browser/rodar-testes.sh`    |
| Windows     | `test_browser\rodar-testes.bat`        |

Ambos aceitam opcoes extras do pytest (ex: `-k "test_despesas"`).

Cobertura atual dos testes E2E (`test_browser/`):
- Navegacao entre abas e anos (`test_navegacao.py`)
- CRUD de despesas, receitas, fixas, contas, categorias e metas
- Status de pagamento (`test_status_pagamento.py`)
- Lazy Commit em modais de detalhe (`test_lazy_commit.py`)
- Validacao de formularios (`test_validacao.py`)
- Interacoes de UI (botoes, confirmacoes, loading) (`test_ui_interactions.py`)
- Rendimentos com saldo acumulado (`test_rendimentos.py`)
- Fixas avancado — excecoes, duplicacao, remapeamento (`test_fixas_avancado.py`)
- Configuracoes (`test_config.py`)

Ao adicionar ou alterar fluxos de UI, considere incluir ou atualizar o teste E2E
correspondente em `test_browser/`.

Se algum teste nao puder ser executado, informe o motivo.
