@echo off
:: =============================================================================
:: Dev environment setup + optional PyInstaller build
:: =============================================================================

set VENV_DIR=.venv
set PYTHON=py -3.11

:: ── Check Python 3.11 is available ───────────────────────────────────────────
echo Checking for Python 3.11...
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11 not found. Install it from https://python.org or via:
    echo         winget install Python.Python.3.11
    exit /b 1
)
echo [OK] Found Python 3.11

:: ── Create venv if it doesn't exist ──────────────────────────────────────────
if exist %VENV_DIR%\Scripts\activate.bat (
    echo [OK] Venv already exists, skipping creation.
) else (
    echo Creating virtual environment in %VENV_DIR%...
    %PYTHON% -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
    echo [OK] Venv created.
)

:: ── Activate and install dependencies ────────────────────────────────────────
echo Installing dependencies from requirements.txt...
call %VENV_DIR%\Scripts\activate.bat
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    exit /b 1
)
echo [OK] Dependencies installed.

:: ── Optionally build the exe ──────────────────────────────────────────────────
echo.
set /p BUILD="Build .exe with PyInstaller now? [y/N]: "
if /i "%BUILD%"=="y" (
    echo Building exe...
    pyinstaller --onefile --name build_and_deploy build_and_deploy.py
    if errorlevel 1 (
        echo [ERROR] PyInstaller build failed.
        exit /b 1
    )
    echo [OK] Exe created at dist\build_and_deploy.exe
) else (
    echo Skipping build. Run manually with:
    echo   pyinstaller --onefile --name build_and_deploy build_and_deploy.py
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo === Setup complete ===
echo To activate your venv in a new terminal:
echo   .venv\Scripts\activate
echo To run the script directly:
echo   python build_and_deploy.py
echo To deactivate the venv:
echo   deactivate
