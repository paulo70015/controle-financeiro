@echo off
REM setup_hooks.bat - Instala os hooks Git do projeto
REM Executar uma vez após clonar o repositório.

echo ============================================
echo  Instalando hooks Git do projeto...
echo ============================================

git config core.hooksPath .githooks

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Hooks instalados com sucesso!
    echo Os hooks em .githooks\ serao executados a cada commit.
    echo.
) else (
    echo.
    echo [ERRO] Falha ao configurar hooks. Verifique se esta em um repo git.
    echo.
)

pause
