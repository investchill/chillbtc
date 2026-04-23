@echo off
REM Launcher Windows - double-cliquable depuis l'Explorateur.
REM Installe uv au premier lancement si necessaire, puis lance ChillBTC.

setlocal

REM Force UTF-8 partout : cmd.exe en code page 65001, Python en UTF-8 mode.
REM Sans ca, cp1252 par defaut ne sait pas afficher les caracteres du CLI
REM (fleches, emojis, bordures) et le Python crash sur UnicodeEncodeError.
chcp 65001 >nul 2>&1
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "SCRIPT_DIR=%~dp0"
set "CODE_DIR=%SCRIPT_DIR%..\code"

echo.
echo   ================================================================
echo     ChillBTC -- BTC posé. Un coup d'œil par mois.
echo   ================================================================
echo.

REM S'assure que %USERPROFILE%\.local\bin est dans le PATH (install par defaut d'uv)
if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

REM 1. Installe uv si absent
where uv >nul 2>&1
if errorlevel 1 (
    echo   ^> Premier lancement detecte.
    echo   ^> Installation de uv ^(gestionnaire Python, ~5 Mo^)...
    echo.
    powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    where uv >nul 2>&1
    if errorlevel 1 (
        echo.
        echo   [ERREUR] Installation de uv echouee.
        echo            Installe manuellement depuis https://docs.astral.sh/uv/
        echo            puis relance ce script.
        pause
        exit /b 1
    )
    echo.
    echo   [OK] uv installe.
    echo.
)

REM 2. uv sync (1ere fois : telecharge Python + deps, 30 s - 2 min selon connexion)
if not exist "%CODE_DIR%\.venv" (
    echo   ^> Installation de Python et des dependances...
    echo     ^(pandas, numpy, matplotlib, requests -- ~80 Mo a telecharger^)
    echo     Cette etape ne se fait qu'une seule fois.
    echo.
)

cd /d "%CODE_DIR%"
uv run chillbtc %*

if errorlevel 1 (
    echo.
    echo   [Une erreur s'est produite. Verifie les messages ci-dessus.]
    pause
)

endlocal
