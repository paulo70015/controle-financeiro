# Exemplos de Uso do Build

## Executando sem parâmetros (mostra ajuda)

```bash
C:\projeto> scripts\construir.bat

============================================
 Controle Financeiro - Gerador de Executavel
 Windows (PyInstaller)
============================================

ERRO: Parametro obrigatorio nao fornecido!

Escolha um modo de build:

  scripts\construir.bat --com-sqlite
    > Modo STANDALONE com SQLite local
    > Funciona imediatamente, sem configuracao
    > Ideal para compartilhar
    > Cada usuario tem seu proprio banco local

  scripts\construir.bat --com-env-vazio
    > Modo Supabase SEM credenciais
    > Usuario precisa criar .env com suas credenciais
    > Ideal para compartilhar quando quer que cada um use seu Supabase

  scripts\construir.bat --com-env
    > Modo Supabase COM suas credenciais embutidas
    > NAO compartilhe - acessa SEU banco Supabase
    > Ideal para uso pessoal em outro computador

Pressione qualquer tecla para continuar...
```

---

## Build Standalone (SQLite)

```bash
C:\projeto> scripts\construir.bat --com-sqlite

============================================
 Controle Financeiro - Gerador de Executavel
 Windows (PyInstaller)
============================================

[INFO] Build STANDALONE com SQLite - banco local embutido

[OK] Python encontrado.

[1/3] Instalando dependencias de build...
[OK] Dependencias instaladas.

[2/3] Gerando executavel com PyInstaller...
[OK] Executavel gerado.

[3/3] Preparando pasta de distribuicao...
Executavel criado em: dist\ControleFinanceiro.exe

========================================
  SUCESSO: Executavel standalone criado!
========================================
Este executavel pode ser compartilhado.
Funciona imediatamente, sem configuracao.
Cada usuario tera seu proprio banco local.
O banco sera criado automaticamente na primeira execucao.

============================================
 Build concluido!
============================================
```

---

## Build Supabase Vazio (para compartilhar)

```bash
C:\projeto> scripts\construir.bat --com-env-vazio

============================================
 Controle Financeiro - Gerador de Executavel
 Windows (PyInstaller)
============================================

[INFO] Build Supabase SEM credenciais - seguro para compartilhar

[OK] Python encontrado.

[1/3] Instalando dependencias de build...
[OK] Dependencias instaladas.

[2/3] Gerando executavel com PyInstaller...
[OK] Executavel gerado.

[3/3] Preparando pasta de distribuicao...
Executavel criado em: dist\ControleFinanceiro.exe

========================================
  SUCESSO: Executavel seguro criado!
========================================
Este executavel pode ser compartilhado.
O usuario precisara criar um arquivo .env com:
  SUPABASE_URL=https://seu-projeto.supabase.co
  SUPABASE_KEY=sua_chave_publica

Use .env.example como modelo.

============================================
 Build concluido!
============================================
```

---

## Build Pessoal (com suas credenciais)

```bash
C:\projeto> scripts\construir.bat --com-env

============================================
 Controle Financeiro - Gerador de Executavel
 Windows (PyInstaller)
============================================

[AVISO] Build com suas credenciais Supabase - NAO compartilhe!

[OK] Python encontrado.

[1/3] Instalando dependencias de build...
[OK] Dependencias instaladas.

[2/3] Gerando executavel com PyInstaller...
[OK] Executavel gerado.

[3/3] Preparando pasta de distribuicao...
Executavel criado em: dist\ControleFinanceiro.exe

========================================
  ATENCAO: Executavel com suas credenciais!
========================================
NAO compartilhe este arquivo.
Ele acessa SEU banco Supabase diretamente.
Use apenas para uso pessoal.

============================================
 Build concluido!
============================================
```

---

## Parâmetro Inválido

```bash
C:\projeto> scripts\construir.bat --outro-parametro

============================================
 Controle Financeiro - Gerador de Executavel
 Windows (PyInstaller)
============================================

ERRO: Parametro invalido: --outro-parametro

Use: --com-sqlite, --com-env-vazio ou --com-env
Execute 'scripts\construir.bat' sem parametros para ver as opcoes.

Pressione qualquer tecla para continuar...
```
