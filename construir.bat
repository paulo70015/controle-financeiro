@echo off
title Controle Financeiro - Construtor Windows
cd /d "%~dp0"

setlocal enabledelayedexpansion

set "PYTHON_CMD=python"

echo ============================================
echo  Controle Financeiro - Gerador de Executavel
echo  Windows (PyInstaller)
echo ============================================
echo.

:: ------------------------------------------------------------
:: PASSO 0: Validar parametro
:: ------------------------------------------------------------
echo [PASSO 0] Validando parametro...
echo   Parametro recebido: "%1"

if "%1"=="" (
    echo.
    echo ERRO: Parametro obrigatorio nao fornecido^^!
    echo.
    echo Escolha um modo de build:
    echo.
    echo   construir.bat --com-sqlite
    echo     ^> Modo STANDALONE com SQLite local
    echo     ^> Funciona imediatamente, sem configuracao
    echo     ^> Ideal para compartilhar
    echo     ^> Cada usuario tem seu proprio banco local
    echo.
    echo   construir.bat --com-env
    echo     ^> Modo Supabase COM suas credenciais embutidas
    echo     ^> NAO compartilhe - acessa SEU banco Supabase
    echo     ^> Ideal para uso pessoal em outro computador
    echo.
    pause
    endlocal
    exit /b 1
)

echo [OK] Parametro valido.

:: ------------------------------------------------------------
:: PASSO 1: Interpretar modo de build
:: ------------------------------------------------------------
echo.
echo [PASSO 1] Interpretando modo de build...

set BUILD_MODE=
set SQLITE_MODE=0

if "%1"=="--com-sqlite" (
    set BUILD_MODE=standalone-sqlite
    set SQLITE_MODE=1
    echo   Modo: STANDALONE com SQLite
) else if "%1"=="--com-env" (
    set BUILD_MODE=pessoal-supabase
    echo   Modo: PESSOAL com Supabase ^(credenciais do .env^)
    echo.
    echo   [AVISO] Build com suas credenciais Supabase - NAO compartilhe^^!
) else (
    echo ERRO: Parametro invalido: %1
    echo.
    echo Use: --com-sqlite ou --com-env
    echo Execute 'construir.bat' sem parametros para ver as opcoes.
    echo.
    pause
    endlocal
    exit /b 1
)

echo   BUILD_MODE=!BUILD_MODE!
echo   SQLITE_MODE=!SQLITE_MODE!
echo [OK] Modo definido.

:: ------------------------------------------------------------
:: PASSO 2: Verificar Python
:: ------------------------------------------------------------
echo.
echo [PASSO 2] Verificando Python...

where "%PYTHON_CMD%" >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado no PATH^^!
    echo   Caminho testado: %PYTHON_CMD%
    echo.
    echo   Instale o Python em https://python.org e marque "Add to PATH"
    echo   Ou ajuste a variavel PYTHON_CMD no topo deste script.
    pause
    endlocal
    exit /b 1
)

"%PYTHON_CMD%" --version
if errorlevel 1 (
    echo ERRO: Python falhou ao executar^^!
    pause
    endlocal
    exit /b 1
)
echo [OK] Python encontrado.

:: ------------------------------------------------------------
:: PASSO 3: Instalar dependencias
:: ------------------------------------------------------------
echo.
echo [PASSO 3] Instalando dependencias de build...

echo   ^>^> pip install --upgrade pip
"%PYTHON_CMD%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [AVISO] pip ja esta atualizado ou houve erro menor ^(continuando^).
)

echo   ^>^> pip install pacotes...
"%PYTHON_CMD%" -m pip install pyinstaller flask supabase psycopg2-binary python-dotenv pillow pystray
if errorlevel 1 (
    echo ERRO: Falha ao instalar dependencias.
    pause
    endlocal
    exit /b 1
)
echo [OK] Dependencias instaladas.

:: ------------------------------------------------------------
:: PASSO 4: Verificar .env (se for modo supabase)
:: ------------------------------------------------------------
echo.
echo [PASSO 4] Verificando arquivo de configuracao...

if "!BUILD_MODE!"=="pessoal-supabase" (
    echo   Modo Supabase: checando .env...
    if not exist ".env" (
        echo.
        echo ========================================
        echo  ERRO: Arquivo .env nao encontrado^^!
        echo ========================================
        echo.
        echo Para build com --com-env, crie o .env a partir do modelo:
        echo.
        echo   copy .env.example .env
        echo.
        echo Depois edite o .env com suas credenciais Supabase.
        echo.
        pause
        endlocal
        exit /b 1
    )
    echo   [OK] .env encontrado.
) else (
    echo   Modo SQLite: sem necessidade de .env
)

echo [OK] Configuracao verificada.

:: ------------------------------------------------------------
:: PASSO 5: Preparar .env_embutido
:: ------------------------------------------------------------
echo.
echo [PASSO 5] Preparando ambiente embutido...

echo   SQLITE_MODE=!SQLITE_MODE!

if "!SQLITE_MODE!"=="1" (
    echo   ^>^> Criando .env_embutido para SQLite...
    echo DB_MODE=sqlite > ".env_embutido"
    if not exist ".env_embutido" (
        echo ERRO: Falha ao criar .env_embutido para modo SQLite^^!
        pause
        endlocal
        exit /b 1
    )
    echo   [OK] .env_embutido criado ^(SQLite^).
) else (
    echo   ^>^> Copiando .env para .env_embutido...
    copy /Y ".env" ".env_embutido"
    if not exist ".env_embutido" (
        echo ERRO: Falha ao copiar .env para .env_embutido^^!
        pause
        endlocal
        exit /b 1
    )
    echo   [OK] .env_embutido criado ^(credenciais Supabase^).
)

echo   [OK] Ambiente embutido preparado.

:: ------------------------------------------------------------
:: PASSO 6: Gerar executavel
:: ------------------------------------------------------------
echo.
echo [PASSO 6] Gerando executavel com PyInstaller...
echo   Comando: "%PYTHON_CMD%" -m PyInstaller --onefile --noconsole ...
echo   ^(Aguardar alguns minutos...^)
echo.

"%PYTHON_CMD%" -m PyInstaller --onefile --noconsole --name "ControleFinanceiro" --add-data "index.html;." --add-data "partials;partials" --add-data "static;static" --add-data ".env_embutido;." --hidden-import flask --hidden-import PIL --hidden-import pystray --hidden-import PIL.Image --hidden-import PIL.ImageDraw --hidden-import PIL.ImageFont --hidden-import postgrest --hidden-import dotenv --hidden-import supabase --collect-submodules financeiro app.py

set EXIT_CODE=!ERRORLEVEL!
echo.
echo   Codigo de saida do PyInstaller: !EXIT_CODE!

if !EXIT_CODE! neq 0 (
    echo ERRO: PyInstaller falhou com codigo !EXIT_CODE!.
    echo   Verifique as mensagens de erro acima.
    echo.
    echo   Dica comum: tente rodar sem --noconsole para ver erros:
    echo     "%PYTHON_CMD%" -m PyInstaller --onefile --name "ControleFinanceiro" --add-data "index.html;." --add-data "partials;partials" --add-data "static;static" --add-data ".env_embutido;." --hidden-import flask --hidden-import PIL --hidden-import pystray --hidden-import PIL.Image --hidden-import PIL.ImageDraw --hidden-import PIL.ImageFont --hidden-import postgrest --hidden-import dotenv --hidden-import supabase --collect-submodules financeiro app.py
    pause
    endlocal
    exit /b 1
)

:: ------------------------------------------------------------
:: PASSO 7: Limpeza
:: ------------------------------------------------------------
echo.
echo [PASSO 7] Limpando arquivos temporarios...

if exist ".env_embutido" (
    del /Q ".env_embutido"
    echo   ^>^> .env_embutido deletado.
)

echo [OK] Limpeza concluida.

:: ------------------------------------------------------------
:: PASSO 8: Verificar resultado
:: ------------------------------------------------------------
echo.
echo [PASSO 8] Verificando executavel gerado...

if exist "dist\ControleFinanceiro.exe" (
    echo   [OK] Executavel encontrado em: dist\ControleFinanceiro.exe
    echo.
    if "!BUILD_MODE!"=="pessoal-supabase" (
        echo ========================================
        echo   ATENCAO: Executavel com suas credenciais!
        echo ========================================
        echo NAO compartilhe este arquivo.
        echo Ele acessa SEU banco Supabase diretamente.
        echo Use apenas para uso pessoal.
    )
    if "!BUILD_MODE!"=="standalone-sqlite" (
        echo ========================================
        echo   SUCESSO: Executavel standalone criado!
        echo ========================================
        echo Este executavel pode ser compartilhado.
        echo Funciona imediatamente, sem configuracao.
        echo Cada usuario tera seu proprio banco local.
        echo O banco sera criado automaticamente na primeira execucao.
    )
) else (
    echo AVISO: Executavel nao encontrado em dist\
    echo   Verifique se houve erro na saida do PyInstaller acima.
)

echo.
echo ============================================
echo  Build concluido!
echo ============================================
echo.

pause
endlocal
