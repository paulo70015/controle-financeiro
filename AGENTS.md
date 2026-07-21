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
- **NUNCA fazer commit ou push sem permissao explicita do usuario.** Antes de qualquer `git commit` ou `git push`, perguntar. Para commits, usar a skill `commit` do projeto (`/commit`), que revisa o diff antes de commitar.

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

Apos alteracoes relevantes, rodar os testes aplicaveis:

### Testes unitarios / integracao
- `python test_suite.py`
- `python test_sqlite_mode.py`
- `python test_csv.py`          (importacao/exportacao CSV — blocos, tipos, roundtrip)
- `python test_db_backup.py`    (backup/restore BD — export .db, roundtrip, colunas novas)
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

## Isolamento de Ambiente (Testes vs Producao)

- **Portas separadas**: os testes usam portas diferentes da aplicacao real.
  - App real: `PORT` do ambiente ou `8080`.
  - E2E (Playwright): `8085` (`conftest.py`).
  - Unitarios (`test_suite.py`): `8086`.
  - `app.py` respeita `os.environ.get("PORT")` — nunca hardcodar porta.
- **Ano de teste**: `ANO_TESTE = ano_atual + 10` para evitar colisao com dados reais
  mesmo apos multiplas execucoes acumularem registros.
- **Licao aprendida**: antes de cacar race conditions complexas no frontend
  (debouncedLoad, innerHTML, wait_for_function), verifique se a infra esta isolada:
  portas, bancos e arquivos compartilhados entre ambientes sao a causa mais comum
  de falhas intermitentes.
