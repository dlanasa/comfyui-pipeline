@echo off
:: ============================================================
:: build_test_railway_exe.bat
:: Builds test_railway.exe using PyInstaller
:: Run this from D:\ComfyUI\_study\
:: ============================================================

echo.
echo === ComfyUI Pipeline — Build test_railway.exe ===
echo.

:: Activate the local venv
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] No .venv found in current directory.
    echo Make sure you run this from D:\ComfyUI\_study\
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat

:: Install PyInstaller if needed
echo Installing PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)

:: Clean previous build
if exist "dist\test_railway.exe" (
    echo Removing previous build...
    del /f /q "dist\test_railway.exe"
)
if exist "build\test_railway" (
    rmdir /s /q "build\test_railway"
)

echo.
echo Building test_railway.exe - this may take a minute...
echo.

:: Build the exe
pyinstaller --noconfirm --onefile --console ^
    --name test_railway ^
    --hidden-import requests ^
    --hidden-import urllib3 ^
    --hidden-import certifi ^
    --hidden-import charset_normalizer ^
    --hidden-import dotenv ^
    test_railway.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed. See output above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  BUILD COMPLETE
echo  Output: dist\test_railway.exe
echo ============================================================
echo.
echo The exe auto-detects ngrok URL and auto-creates output directory.
echo Make sure ComfyUI and ngrok are running before double-clicking!
echo.
pause
