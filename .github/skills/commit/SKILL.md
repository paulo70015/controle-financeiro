---
name: commit
description: Faz commit com mensagem no padrão Conventional Commits, após revisão do diff. Use quando o usuário pedir para commitar alterações.
---

# Skill: Commit

Fluxo interativo para criar commits com mensagem padronizada.

## Fluxo

1. **Verificar hook** — Rode `git config core.hooksPath .githooks` para garantir que o pre-commit gere `BUILD_NUMBER`.
2. **Verificar estado** — `git status --short`. Se não houver nada para commitar, informe e pare.
3. **Stage** — `git add -A` ou arquivos específicos se o usuário indicar um escopo.
4. **Mostrar diff** — `git diff --staged --stat` para o usuário revisar o que vai entrar.
5. **Classificar versão** — Analise o diff e defina o impacto sobre `VERSION_BASE`:
   - `major` (`X.0.0`): melhorias grandes, mudanças estruturais ou incompatíveis.
   - `minor` (`X.Y.0`): melhorias pequenas/funcionalidades compatíveis.
   - `patch` (`X.Y.Z`): correções, ajustes internos, docs, testes e chores.
6. **Calcular próxima versão** — Rode `python version.py --next <major|minor|patch>` ou `python3`, se `python` não existir, para exibir a mudança sem gravar.
7. **Gerar mensagem** — Analise o diff e proponha uma mensagem no formato **Conventional Commits**:
   ```text
   <tipo>(<escopo>): <descricao curta em PT-BR>

   <corpo opcional com detalhes>
   ```
   Tipos comuns: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `style`, `perf`.
   Escopo é opcional; use o módulo ou área afetada, como `despesas`, `receitas`, `e2e` ou `db`.
   A descrição deve ficar em PT-BR, no imperativo, com até 72 caracteres.
8. **Confirmar** — Mostre a mensagem proposta, o bump escolhido e a nova versão. Peça confirmação do usuário. Se recusar, permita editar sem alterar `version.py`.
9. **Atualizar versão** — Após confirmação, rode `python version.py --bump <major|minor|patch>`, depois `git add version.py` e mostre `git diff --staged --stat` atualizado.
10. **Commit** — Rode `git commit -m "<mensagem>"`.
11. **Push opcional** — Pergunte se deve fazer `git push`.

## Regras

- Use comandos git não interativos.
- Nunca faça commit sem mostrar o diff e pedir confirmação.
- Se `git status --short` estiver vazio, informe e pare.
- Se houver arquivos sensíveis no stage (`.env`, `*.db`, `credentials.json`), alerte o usuário antes de commitar.
- Mensagem sempre em PT-BR, exceto o prefixo do Conventional Commits.
- Se o diff for muito grande, resuma as mudanças no corpo da mensagem em tópicos.
- Nunca deixe `VERSION_BASE` fora do commit quando houver bump; o hook de pre-commit continua gerando apenas `BUILD_NUMBER`.
- Inclua o trailer padrão quando aplicável:
  ```text
  Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
  ```
