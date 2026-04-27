@echo off
title Controle Financeiro - Log
cd /d "%~dp0"

echo ============================================
echo  Controle Financeiro v1.3.0
echo  Log de inicializacao: %DATE% %TIME%
echo ============================================
echo.

:: Verificar Python
echo [1/4] Verificando Python...
python --version
if errorlevel 1 (
    echo ERRO: Python nao encontrado no PATH!
    echo Instale o Python em https://python.org e marque "Add to PATH"
    pause
    exit /b 1
)
echo OK.
echo.

:: Verificar dependencias
echo [2/4] Verificando dependencias...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Flask nao encontrado. Instalando dependencias...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERRO: Falha ao instalar Flask.
        pause
        exit /b 1
    )
)
python -c "import supabase" >nul 2>&1
if errorlevel 1 (
    echo Supabase nao encontrado. Instalando dependencias do banco...
    python -m pip install supabase postgrest python-dotenv psycopg2-binary
)
echo OK.
echo.

:: Verificar arquivos essenciais
echo [3/4] Verificando arquivos...
if not exist "app.py" (
    echo ERRO: app.py nao encontrado na pasta %~dp0
    pause
    exit /b 1
)
if not exist "index.html" (
    echo ERRO: index.html nao encontrado na pasta %~dp0
    pause
    exit /b 1
)
if not exist ".env" (
    echo .env ........... ausente ^(usando SQLite padrao^)
) else (
    echo .env ........... OK
)
echo app.py ......... OK
echo index.html ..... OK
echo.

:: Iniciar servidor
echo [4/4] Iniciando servidor em http://localhost:8080
echo.
echo ============================================
echo  LOGS DO SERVIDOR ABAIXO
echo  Pressione Ctrl+C para encerrar
echo ============================================
echo.

python app.py --show-console

echo.
echo Servidor encerrado.
pause
