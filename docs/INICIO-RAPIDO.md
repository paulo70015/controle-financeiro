# 🚀 Início Rápido - Controle Financeiro

Escolha seu caminho:

---

## 🟢 Caminho 1: Quero Começar AGORA (SQLite)

**Tempo: 30 segundos**

1. Dê duplo clique em `scripts\iniciar_log.bat` (Windows) ou execute `./scripts/iniciar_log.sh` (Linux/Mac)
2. Pronto! ✨

O navegador abrirá automaticamente e você já pode começar a usar.

---

## 🔵 Caminho 2: Quero Dados na Nuvem (Supabase)

**Tempo: 5-10 minutos**

### Passo 1: Criar Conta (2 min)
1. Acesse https://supabase.com
2. Clique em "Start your project"
3. Faça login com GitHub ou Google
4. Clique em "New Project"
5. Preencha:
   - Nome: `financeiro-pessoal` (ou qualquer nome)
   - Senha: escolha uma senha forte (anote!)
   - Região: escolha a mais próxima
6. Clique em "Create new project"
7. Aguarde ~2 minutos ⏳

### Passo 2: Criar Tabelas (2 min)
1. No painel do Supabase, clique em **SQL Editor** (ícone 🗄️)
2. Clique em **+ New Query**
3. Abra o arquivo `specs/schema-supabase.sql` (está na pasta do projeto)
4. Copie TUDO (Ctrl+A, Ctrl+C)
5. Cole no editor SQL do Supabase (Ctrl+V)
6. Clique em **Run** (ou Ctrl+Enter)
7. Deve aparecer "Success. No rows returned" ✅

### Passo 3: Pegar Credenciais (1 min)
1. No painel do Supabase, clique em **Settings** (⚙️) → **API**
2. Você verá:
   ```
   Project URL: https://xxxxx.supabase.co
   anon public: eyJhbGc...
   ```
3. Copie esses dois valores

### Passo 4: Configurar Aplicativo (1 min)
1. Na pasta do projeto, crie um arquivo chamado `.env`
   - **Windows:** Clique com botão direito → Novo → Documento de Texto
   - Renomeie para `.env` (sem .txt no final)
   - Se não conseguir, use o Bloco de Notas e salve como "Todos os arquivos"
   
2. Cole este conteúdo (substitua pelos seus valores):
   ```
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=eyJhbGc...
   DB_MODE=supabase
   ```

3. Salve o arquivo

### Passo 5: Iniciar (30 seg)
1. Dê duplo clique em `scripts\iniciar_log.bat` (Windows) ou execute `./scripts/iniciar_log.sh` (Linux/Mac)
2. Pronto! ✨

---

## 📊 Comparação Rápida

| | SQLite (Local) | Supabase (Nuvem) |
|---|---|---|
| **Tempo de setup** | 30 segundos | 5-10 minutos |
| **Configuração** | Nenhuma | Criar conta + .env |
| **Internet** | Não precisa | Necessário |
| **Múltiplos PCs** | Não (só local) | Sim |
| **Backup** | Manual | Automático |
| **Custo** | Grátis | Grátis (500MB) |

---

## 🎯 Qual Escolher?

### Escolha SQLite se:
- ✅ Quer começar imediatamente
- ✅ Usa apenas um computador
- ✅ Prefere dados 100% locais
- ✅ Não quer criar contas em serviços

### Escolha Supabase se:
- ✅ Quer acessar de vários dispositivos
- ✅ Quer backup automático na nuvem
- ✅ Planeja usar app mobile no futuro
- ✅ Não se importa com 5 min de configuração

---

## 🔄 Posso Mudar Depois?

**Sim!** Você pode alternar entre os modos a qualquer momento:

**SQLite → Supabase:**
1. Configure o Supabase (passos acima)
2. Exporte seus dados via CSV
3. Mude para Supabase no `.env`
4. Importe o CSV

**Supabase → SQLite:**
1. Exporte seus dados via CSV
2. Apague o `.env` (ou mude `DB_MODE=sqlite`)
3. Importe o CSV

---

## ❓ Dúvidas Frequentes

**P: Preciso pagar pelo Supabase?**
R: Não! O plano gratuito tem 500MB, suficiente para anos de uso pessoal.

**P: Meus dados estão seguros no Supabase?**
R: Sim! Conexão criptografada (HTTPS) e você é o único com acesso.

**P: E se o Supabase sair do ar?**
R: Você pode exportar seus dados via CSV a qualquer momento e usar SQLite.

**P: Posso usar os dois modos ao mesmo tempo?**
R: Não simultaneamente, mas pode alternar quando quiser.

**P: Onde fica o banco SQLite?**
R: Na pasta do projeto, arquivo `financeiro.db`

**P: Como faço backup do SQLite?**
R: Copie o arquivo `financeiro.db` para um local seguro (pendrive, nuvem, etc.)

---

## 🆘 Problemas?

### "Python não encontrado"
→ Instale em https://python.org (marque "Add to PATH")

### "Erro ao conectar Supabase"
→ Verifique se o `.env` está correto (URL e KEY)

### "Tabelas não existem"
→ Execute o script `specs/schema-supabase.sql` no SQL Editor

### "Não consigo criar arquivo .env"
→ Use Bloco de Notas, salve como "Todos os arquivos" com nome `.env`

---

## ✅ Checklist de Sucesso

### SQLite:
- [ ] Executei `scripts\iniciar_log.bat` ou `./scripts/iniciar_log.sh`
- [ ] Navegador abriu automaticamente
- [ ] Consigo criar categorias e lançamentos

### Supabase:
- [ ] Criei conta no Supabase
- [ ] Executei `schema-supabase.sql` no SQL Editor
- [ ] Criei arquivo `.env` com minhas credenciais
- [ ] Executei `scripts\iniciar_log.bat` ou `./scripts/iniciar_log.sh`
- [ ] Navegador abriu e consigo usar normalmente

---

## 🎉 Pronto!

Agora é só começar a controlar suas finanças!

**Próximos passos:**
1. Crie suas categorias (Alimentação, Transporte, etc.)
2. Lance suas despesas e receitas
3. Configure despesas fixas (aluguel, cartão, etc.)
4. Defina suas metas financeiras

**Dica:** Comece simples! Não precisa cadastrar tudo de uma vez.
Vá adicionando conforme usa o sistema.

Bom controle financeiro! 💰📊
