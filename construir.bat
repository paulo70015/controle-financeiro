@echo off
title Controle Financeiro - Construtor Windows
cd /d "%~dp0"

set "PYTHON_CMD=python"

echo ============================================
echo  Controle Financeiro - Gerador de Executavel
echo  Windows (PyInstaller)
echo ============================================
echo.

:: Verificar se parametro foi fornecido
if "%1"=="" (
    echo ERRO: Parametro obrigatorio nao fornecido!
    echo.
    echo Escolha um modo de build:
    echo.
    echo   construir.bat --com-sqlite
    echo     ^> Modo STANDALONE com SQLite local
    echo     ^> Funciona imediatamente, sem configuracao
    echo     ^> Ideal para compartilhar
    echo     ^> Cada usuario tem seu proprio banco local
    echo.
    echo   construir.bat --com-env-vazio
    echo     ^> Modo Supabase SEM credenciais
    echo     ^> Usuario precisa criar .env com suas credenciais
    echo     ^> Ideal para compartilhar quando quer que cada um use seu Supabase
    echo.
    echo   construir.bat --com-env
    echo     ^> Modo Supabase COM suas credenciais embutidas
    echo     ^> NAO compartilhe - acessa SEU banco Supabase
    echo     ^> Ideal para uso pessoal em outro computador
    echo.
    pause
    exit /b 1
)

:: Processar parametro
set INCLUIR_ENV=
set BUILD_MODE=

if "%1"=="--com-sqlite" (
    set INCLUIR_ENV=.env.sqlite
    set BUILD_MODE=standalone-sqlite
    echo [INFO] Build STANDALONE com SQLite - banco local embutido
    echo.
) else if "%1"=="--com-env-vazio" (
    set INCLUIR_ENV=.env.example
    set BUILD_MODE=compartilhar-supabase
    echo [INFO] Build Supabase SEM credenciais - seguro para compartilhar
    echo.
) else if "%1"=="--com-env" (
    set INCLUIR_ENV=.env
    set BUILD_MODE=pessoal-supabase
    echo [AVISO] Build com suas credenciais Supabase - NAO compartilhe!
    echo.
) else (
    echo ERRO: Parametro invalido: %1
    echo.
    echo Use: --com-sqlite, --com-env-vazio ou --com-env
    echo Execute 'construir.bat' sem parametros para ver as opcoes.
    echo.
    pause
    exit /b 1
)

call "%PYTHON_CMD%" --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado no PATH!
    echo Instale o Python em https://python.org e marque "Add to PATH"
    pause
    exit /b 1
)
echo [OK] Python encontrado.

echo.
echo [1/3] Instalando dependencias de build...
call "%PYTHON_CMD%" -m pip install --upgrade pip >nul
call "%PYTHON_CMD%" -m pip install pyinstaller flask supabase psycopg2-binary python-dotenv pillow pystray >nul
if errorlevel 1 (
    echo ERRO: Falha ao instalar dependencias.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas.

echo.
echo [2/3] Gerando executavel com PyInstaller...

echo Preparando ambiente embutido...
copy /Y "%INCLUIR_ENV%" ".env_embutido" >nul

:: Gerar BUILD_NUMBER se nao existir (para que a versao exiba o build)
if not exist "BUILD_NUMBER" (
    echo [INFO] BUILD_NUMBER nao encontrado, gerando...
    call "%PYTHON_CMD%" gerar_build.py
)

call "%PYTHON_CMD%" -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name "ControleFinanceiro" ^
    --add-data "index.html;." ^
    --add-data "partials;partials" ^
    --add-data "static;static" ^
    --add-data ".env_embutido;." ^
    --add-data "BUILD_NUMBER;." ^
    --hidden-import flask ^
    --hidden-import PIL ^
    --hidden-import pystray ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageDraw ^
    --hidden-import PIL.ImageFont ^
    --hidden-import postgrest ^
    --hidden-import dotenv ^
    --hidden-import supabase ^
    --collect-submodules financeiro ^
    app.py

del /Q ".env_embutido" >nul

if errorlevel 1 (
    echo ERRO: Falha ao gerar executavel.
    pause
    exit /b 1
)
echo [OK] Executavel gerado.

echo.
echo [3/3] Preparando pasta de distribuicao...
if exist "dist\ControleFinanceiro.exe" (
    echo Executavel criado em: dist\ControleFinanceiro.exe
    echo.
    if "%BUILD_MODE%"=="pessoal-supabase" (
        echo ========================================
        echo   ATENCAO: Executavel com suas credenciais!
        echo ========================================
        echo NAO compartilhe este arquivo.
        echo Ele acessa SEU banco Supabase diretamente.
        echo Use apenas para uso pessoal.
    ) else if "%BUILD_MODE%"=="standalone-sqlite" (
        echo ========================================
        echo   SUCESSO: Executavel standalone criado!
        echo ========================================
        echo Este executavel pode ser compartilhado.
        echo Funciona imediatamente, sem configuracao.
        echo Cada usuario tera seu proprio banco local.
        echo O banco sera criado automaticamente na primeira execucao.
    ) else if "%BUILD_MODE%"=="compartilhar-supabase" (
        echo ========================================
        echo   SUCESSO: Executavel seguro criado!
        echo ========================================
        echo Este executavel pode ser compartilhado.
        echo O usuario precisara criar um arquivo .env com:
        echo   SUPABASE_URL=https://seu-projeto.supabase.co
        echo   SUPABASE_KEY=sua_chave_publica
        echo.
        echo Use .env.example como modelo.
    )
) else (
    echo AVISO: Executavel nao encontrado em dist\
)

echo.
echo [LIMPEZA] Removendo arquivos temporarios...
if exist "build" rmdir /S /Q "build"
if exist "ControleFinanceiro.spec" del /Q "ControleFinanceiro.spec"
echo [OK] Apenas o executavel em dist\ foi mantido.

echo.
echo ============================================
echo  Build concluido!
echo ============================================
pause
