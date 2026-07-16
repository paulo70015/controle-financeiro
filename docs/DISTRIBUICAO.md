# Controle Financeiro - Guia de Distribuição

## Para Gerar o Executável

⚠️ **IMPORTANTE:** Você DEVE escolher um modo de build. Execute sem parâmetros para ver as opções.

### 1. Build Standalone com SQLite (RECOMENDADO para compartilhar) ✨
```bash
scripts\construir.bat --com-sqlite
```
- Gera executável **100% standalone** com banco SQLite local
- **Seguro para compartilhar** - cada usuário terá seu próprio banco
- Não precisa configurar nada - funciona imediatamente
- Banco criado automaticamente na primeira execução
- Ideal para quem não quer depender de serviços externos

### 2. Build Supabase sem Credenciais (para compartilhar)
```bash
scripts\construir.bat --com-env-vazio
```
- Gera executável **sem** suas credenciais
- Seguro para compartilhar com outras pessoas
- Cada usuário precisa criar conta Supabase e configurar `.env`
- Ideal quando você quer que cada pessoa tenha seu próprio banco na nuvem

### 3. Build Supabase com Suas Credenciais (uso pessoal) 🔒
```bash
scripts\construir.bat --com-env
```
- Gera executável **com** suas credenciais do `.env` embutidas
- **⚠️ NÃO COMPARTILHE** este executável - use apenas para você mesmo
- Acessa seu banco Supabase diretamente
- Ideal para usar em outro computador seu sem reconfigurar

---

## Para Quem Recebe o Executável

### Opção A: Modo Standalone (SQLite) - MAIS FÁCIL ✨

Se você recebeu um executável gerado com `--com-sqlite`:

1. **Apenas execute** `ControleFinanceiro.exe`
2. Pronto! O banco de dados será criado automaticamente
3. Seus dados ficam salvos localmente na pasta do executável

**Vantagens:**
- ✅ Zero configuração necessária
- ✅ Funciona offline
- ✅ Dados 100% locais e privados
- ✅ Não precisa criar conta em nenhum serviço

**Desvantagens:**
- ❌ Sem sincronização entre dispositivos
- ❌ Backup manual (copiar arquivo `financeiro.db`)

---

### Opção B: Modo Supabase (Nuvem)

Se você recebeu um executável gerado com `--com-env-vazio`:

#### Passo 1: Criar conta no Supabase
1. Acesse https://supabase.com e crie uma conta gratuita
2. Crie um novo projeto
3. Aguarde a criação do banco de dados (leva ~2 minutos)

#### Passo 2: Configurar o banco de dados
1. No painel do Supabase, vá em **SQL Editor**
2. Execute o script `specs/schema-supabase.sql` (cria as tabelas)
3. Opcionalmente, execute `specs/dados-supabase.sql` (dados de exemplo)

#### Passo 3: Obter credenciais
1. No painel do Supabase, vá em **Settings** → **API**
2. Copie:
   - **Project URL** (ex: https://xxxxx.supabase.co)
   - **anon/public key** (chave pública, começa com "eyJ...")

#### Passo 4: Configurar o aplicativo
1. Na mesma pasta do `ControleFinanceiro.exe`, crie um arquivo chamado `.env`
2. Cole o seguinte conteúdo (substituindo pelos seus valores):

```
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_publica_aqui
```

3. Salve o arquivo

#### Passo 5: Executar
- Dê duplo clique em `ControleFinanceiro.exe`
- O aplicativo abrirá no navegador padrão
- Um ícone aparecerá na bandeja do sistema (próximo ao relógio)

**Vantagens:**
- ✅ Sincronização entre dispositivos
- ✅ Backup automático na nuvem
- ✅ Acesso de qualquer lugar

**Desvantagens:**
- ❌ Precisa criar conta no Supabase
- ❌ Requer conexão com internet

---

## Comparação dos Modos

| Característica | `--com-sqlite` | `--com-env-vazio` | `--com-env` |
|---|---|---|---|
| **Nome** | Standalone SQLite | Supabase Vazio | Supabase Pessoal |
| **Configuração** | Nenhuma | Criar .env + Supabase | Nenhuma |
| **Internet** | Não precisa | Necessário | Necessário |
| **Sincronização** | Não | Sim | Sim |
| **Backup** | Manual | Automático | Automático |
| **Privacidade** | 100% local | Dados na nuvem | Seus dados na nuvem |
| **Compartilhar?** | ✅ Sim | ✅ Sim | ❌ NÃO! |
| **Custo** | Grátis | Grátis (plano free) | Grátis (plano free) |

---

## 🎯 Cenários de Uso

### Cenário 1: Você quer compartilhar com amigos/família
**Use:** `scripts\construir.bat --com-sqlite`
- Eles só precisam executar
- Cada um tem seu banco próprio
- Mais fácil para quem não é técnico
- **RECOMENDADO** ✨

### Cenário 2: Você quer que cada pessoa tenha conta Supabase
**Use:** `scripts\construir.bat --com-env-vazio`
- Mais trabalho inicial (criar conta)
- Vantagem: dados na nuvem, sincronização
- Cada pessoa tem seu próprio banco Supabase

### Cenário 3: Você quer usar em outro PC seu
**Use:** `scripts\construir.bat --com-env`
- Acessa seus dados diretamente
- Não compartilhe este executável!
- Ideal para ter em pendrive/backup pessoal

---

## Suporte

Para mais informações:
- **SQLite**: Banco local, sem configuração adicional
- **Supabase**: https://supabase.com/docs
  - Plano gratuito: 500MB de banco de dados
  - Suficiente para anos de controle financeiro pessoal
