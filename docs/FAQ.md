# ❓ Perguntas Frequentes (FAQ)

## 🚀 Início e Configuração

### Como faço para começar a usar?
Execute `iniciar_log.bat` (Windows) ou `./iniciar_log.sh` (Linux/Mac). O navegador abrirá automaticamente.

### Preciso instalar alguma coisa?
Apenas Python 3.10+ (baixe em https://python.org). O resto é automático.

### Qual modo devo escolher: SQLite ou Supabase?
- **SQLite:** Se quer começar imediatamente, usa só um PC, prefere dados locais
- **Supabase:** Se quer acessar de vários dispositivos, quer backup automático na nuvem

### Posso mudar de SQLite para Supabase depois?
Sim! Exporte seus dados via CSV, configure o Supabase, e importe o CSV.

---

## 💾 Banco de Dados

### Onde ficam meus dados no modo SQLite?
No arquivo `financeiro.db` na pasta do aplicativo.

### Como faço backup no modo SQLite?
Copie o arquivo `financeiro.db` para um local seguro (pendrive, nuvem, etc.).

### Meus dados estão seguros no Supabase?
Sim! Conexão criptografada (HTTPS) e você é o único com acesso às suas credenciais.

### O Supabase é grátis?
Sim! O plano gratuito tem 500MB de banco, suficiente para anos de uso pessoal.

### E se o Supabase sair do ar?
Você pode exportar seus dados via CSV a qualquer momento e usar SQLite.

### Posso usar os dois modos ao mesmo tempo?
Não simultaneamente, mas pode alternar quando quiser editando o `.env`.

### Como faço backup dos meus dados?
- **SQLite:** Copie o arquivo `financeiro.db` para local seguro
- **Supabase:** Backups automáticos na nuvem + você pode exportar via CSV

---

## 🔧 Configuração Supabase

### Não consigo criar o arquivo .env
Use o Bloco de Notas, salve como "Todos os arquivos" com nome `.env` (sem .txt).

### Onde encontro a URL e KEY do Supabase?
No painel do Supabase: Settings (⚙️) → API. Copie "Project URL" e "anon public".

### Executei o schema-supabase.sql mas deu erro
Certifique-se de copiar TODO o conteúdo do arquivo e colar no SQL Editor do Supabase.

### Como sei se está usando SQLite ou Supabase?
Veja o arquivo `.env`:
- `DB_MODE=sqlite` → SQLite
- `DB_MODE=supabase` → Supabase
- Sem `.env` → SQLite (padrão)

---

## 📦 Executável

### Como gero um executável para compartilhar?
```bash
construir.bat --com-sqlite  # Modo standalone (RECOMENDADO)
```

### Qual a diferença entre os modos de build?
- `--com-sqlite`: Funciona imediatamente, cada um tem banco próprio
- `--com-env-vazio`: Cada pessoa precisa criar conta Supabase
- `--com-env`: Acessa SEU banco (NÃO compartilhe!)

### O executável funciona sem Python instalado?
Sim! O PyInstaller empacota tudo necessário.

### Posso compartilhar o executável gerado com --com-env?
**NÃO!** Ele contém suas credenciais. Use `--com-sqlite` ou `--com-env-vazio`.

### O executável é muito grande
Sim, ~50-80MB. É normal, pois inclui Python e todas as bibliotecas.

---

## 💰 Uso do Aplicativo

### Como adiciono uma despesa?
Clique na célula da categoria e mês desejados, preencha valor e nota, clique em Salvar.

### Como marco uma despesa como paga?
Clique no ícone no canto superior esquerdo da célula. Ciclo: Em aberto → Agendado → Pago.

### Como lanço a mesma despesa em todos os meses?
Ao criar despesa, selecione "Todos os meses" no campo de mês.

### O que são despesas fixas?
Despesas recorrentes mensais (aluguel, cartão, etc.). Configure uma vez e elas aparecem automaticamente.

### Como removo uma fixa de um mês específico?
Clique no X ao lado do valor das fixas na célula. Isso cria uma exceção para aquele mês.

### O que é o Quadrado Mágico?
Segure SHIFT e clique (ou arraste) sobre várias células para ver a soma total instantânea.

### Como reordeno categorias?
Arraste pela alça ≡ à direita do nome da categoria.

### Como redimensiono colunas?
Arraste a borda direita do cabeçalho de cada coluna.

---

## 📈 Rendimentos

### O que são Locais de Rendimento?
Lugares onde você investe (CDB, Ações, Fundos, etc.). Cada local tem seu próprio saldo acumulado.

### Como funciona a projeção?
Configure uma taxa (ex: 1% ao mês) e o sistema calcula automaticamente os rendimentos futuros.

### A projeção altera meus dados reais?
Não! É apenas uma pré-visualização. Você precisa clicar em "Aplicar" para salvar.

### Posso ter vários locais de rendimento?
Sim! Crie quantos quiser e reordene arrastando.

---

## 🎨 Interface

### O que são os ícones [BB], [CX], [NU]?
Tags que convertem automaticamente em ícones coloridos dos bancos:
- [BB] → Banco do Brasil
- [CX] → Caixa Econômica
- [NU] → Nubank

### Onde posso usar essas tags?
Em qualquer texto: categorias, despesas fixas, metas, locais de rendimento.

### Como desfaço uma exclusão?
Antes de fechar o modal de detalhes, clique no botão "Desfazer" na pilha de ações.

### O que é a pilha de Desfazer?
Sistema que permite reverter exclusões e edições antes de fechar o modal (lazy commit).

---

## 📤 Importação/Exportação

### Como exporto meus dados?
Clique no botão "CSV ▾" no header → Exportar. Salva todas as despesas e receitas do ano.

### Posso importar de uma planilha Excel?
Sim! Salve a planilha como CSV e importe. Formato: categoria, mês, valor, nota.

### Importei errado, como desfaço?
Clique em "CSV ▾" → Desfazer Importação. Remove todos os lançamentos da última importação.

### O CSV não abre corretamente no Excel
O arquivo usa UTF-8 com BOM e separador `;` para compatibilidade com Excel PT-BR.

---

## 🔄 Sincronização

### Posso acessar de vários computadores?
Sim, no modo Supabase. Configure o `.env` em cada computador com as mesmas credenciais.

### E no modo SQLite?
Não automaticamente. Você precisa copiar o arquivo `financeiro.db` manualmente entre os computadores.

### Posso usar serviços de nuvem (Dropbox, OneDrive) com SQLite?
Sim! Coloque o arquivo `financeiro.db` em uma pasta sincronizada. Mas atenção: não use em dois computadores ao mesmo tempo para evitar conflitos de arquivo.

---

## 🐛 Problemas

### "Python não encontrado"
Instale Python 3.10+ em https://python.org. No Windows, marque "Add to PATH".

### "Erro ao conectar no Supabase"
- Verifique se o `.env` está na pasta correta
- Confirme que a URL e KEY estão corretas
- Teste se consegue acessar o painel do Supabase

### "Tabelas não existem" (Supabase)
Execute o script `specs/schema-supabase.sql` no SQL Editor do Supabase.

### "Banco de dados vazio" (SQLite)
Normal na primeira execução. O banco é criado automaticamente.

### Executável não abre
- Modo SQLite: deve funcionar imediatamente
- Modo Supabase: precisa criar `.env` na pasta do executável

### Aplicativo está lento
- Verifique conexão com internet (modo Supabase)
- Reduza o número de linhas visíveis nas configurações
- Feche abas desnecessárias do navegador

### Não consigo editar um lançamento
Clique no ícone de lápis (✏️) ao lado do lançamento na lista de detalhes.

### Como faço backup no modo SQLite?
Copie o arquivo `financeiro.db` para um local seguro (pendrive, Dropbox, OneDrive, etc.).

### Como faço backup no modo Supabase?
O Supabase faz backups automáticos. Você também pode exportar seus dados via CSV a qualquer momento.

---

## 🔒 Segurança e Privacidade

### Meus dados são enviados para algum servidor?
- **SQLite:** Não, tudo fica local
- **Supabase:** Sim, para o servidor do Supabase (criptografado)

### Alguém pode ver meus dados no Supabase?
Não. Apenas você tem acesso com suas credenciais.

### Posso usar sem internet?
- **SQLite:** Sim, 100% offline
- **Supabase:** Não, precisa de conexão

### O que acontece se eu perder o .env?
Você perde acesso ao banco Supabase. Guarde suas credenciais em local seguro!

### Posso ter dois bancos diferentes?
Sim! Crie dois projetos no Supabase e alterne mudando o `.env`.

---

## 📱 Mobile

### Tem versão para celular?
Ainda não, mas está em desenvolvimento (app Flutter).

### Posso acessar pelo navegador do celular?
Sim, mas a interface não está otimizada para mobile ainda.

---

## 🛠️ Desenvolvimento

### Posso contribuir com o projeto?
Sim! Veja o arquivo `README.md` para instruções.

### Qual a arquitetura do projeto?
DDD (Domain-Driven Design) com separação clara de camadas.

### Por que não usa ORM?
Preferência por SQL puro para controle total e performance.

### Por que JavaScript Vanilla?
Simplicidade, sem dependências externas, mais leve.

---

## 📞 Mais Ajuda

### Onde encontro mais documentação?
- `LEIAME.txt` - Guia completo
- `INICIO-RAPIDO.md` - Setup passo a passo
- `DISTRIBUICAO.md` - Como compartilhar
- `README.md` - Visão geral técnica

### Encontrei um bug, o que faço?
Abra uma issue no repositório com detalhes do problema.

### Tenho uma sugestão de funcionalidade
Ótimo! Abra uma issue ou discussion no repositório.

---

**Não encontrou sua pergunta?** Abra uma issue no repositório ou consulte a documentação completa! 📚
