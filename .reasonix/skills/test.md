---
name: test
description: Roda a suite completa de testes (unitários + E2E Playwright) e reporta falhas.
---

# Skill: Testes Completos

Roda todos os testes do projeto e reporta o resultado de forma clara.

## Fluxo

1. **Testes unitários / integração** — `python test_suite.py`
2. Se passou, roda **testes E2E com Playwright** — `bash test_browser/rodar-testes.sh` (Linux/macOS) ou `test_browser\rodar-testes.bat` (Windows)
3. Reporta um resumo: quantos passaram, quantos falharam, e quais arquivos falharam.

## Regras

- Rode SEMPRE na ordem: unitários primeiro, E2E depois.
- Se os unitários falharem, interrompa e reporte as falhas — não rode os E2E.
- Use `run_command` para ambos (comando finito, não servidor).
- Para o script E2E, detecte o SO: se `test_browser/rodar-testes.sh` existe e é executável, use `bash test_browser/rodar-testes.sh`; senão tente `test_browser/rodar-testes.bat`.
- Passe argumentos adicionais (ex: `-k "test_despesas"`) para o script E2E se o usuário os fornecer nos `arguments`.
- Ao final, exiba um resumo claro: ✅ verdes para sucesso, ❌ vermelhos para falhas, com os nomes dos arquivos/problemáticos.
- Se `DB_MODE=supabase` estiver no ambiente, alerte que os testes E2E forçam SQLite e isso não é problema.

## Exemplo de invocação

```
/run_skill test
/run_skill test -k "test_lazy_commit"
```
