---
name: commit
description: Faz commit com mensagem no padrão Conventional Commits, após revisão do diff.
---

# Skill: Commit

Fluxo interativo para criar commits com mensagem padronizada.

## Fluxo

1. **Verificar estado** — `git status --short`. Se não houver nada para commitar, informe e pare.
2. **Stage** — `git add -A` (ou arquivos específicos se o usuário os passar nos `arguments`).
3. **Mostrar diff** — `git diff --staged --stat` para o usuário revisar o que vai entrar.
4. **Classificar versão** — Analise o diff e defina o impacto sobre `VERSION_BASE`:
   - `major` (`X.0.0`): melhorias grandes, mudanças estruturais ou incompatíveis.
   - `minor` (`X.Y.0`): melhorias pequenas/funcionalidades compatíveis.
   - `patch` (`X.Y.Z`): correções, ajustes internos, docs, testes e chores.
5. **Calcular próxima versão** — Rode `python version.py --next <major|minor|patch>` (ou `python3`, se `python` não existir) para exibir a mudança sem gravar.
6. **Gerar mensagem** — Analise o diff e proponha uma mensagem no formato **Conventional Commits**:
   ```
   <tipo>(<escopo>): <descricao curta em PT-BR>

   <corpo opcional com detalhes>
   ```
   Tipos comuns: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `style`, `perf`.
   Escopo é opcional — use o módulo ou área afetada (ex: `despesas`, `receitas`, `e2e`, `db`).
   Descrição em PT-BR, imperativa, ≤ 72 chars.
7. **Confirmar** — Mostre a mensagem proposta, o bump escolhido e a nova versão. Peça confirmação do usuário. Se recusar, permita editar sem alterar `version.py`.
8. **Atualizar versão** — Após confirmação, rode `python version.py --bump <major|minor|patch>`, depois `git add version.py` e mostre `git diff --staged --stat` atualizado.
9. **Commit** — `git commit -m "<mensagem>"`.
10. **Push (opcional)** — Pergunte se deve fazer `git push`.

## Regras

- Use `run_command` para todos os comandos git.
- NUNCA faça commit sem mostrar o diff e pedir confirmação.
- Se `git status --short` estiver vazio, informe e pare.
- Se houver arquivos sensíveis no stage (`.env`, `*.db`, `credentials.json`), alerte o usuário antes de commitar.
- Mensagem sempre em PT-BR (exceto o prefixo do Conventional Commits que é padrão).
- Se o diff for muito grande (>200 linhas), resuma as mudanças no corpo da mensagem em tópicos.
- Nunca deixe `VERSION_BASE` fora do commit quando houver bump; o hook de pre-commit continua gerando apenas `BUILD_NUMBER`.

## Exemplo de invocação

```
/run_skill commit
/run_skill commit static/js/modules/despesas.js
```
