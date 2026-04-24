@echo off
:: ============================================================
:: build_test_remote_exe.bat
:: Builds test_remote_vN.exe using PyInstaller
:: Run this from D:\ComfyUI\_study\
:: ============================================================

echo.
echo === ComfyUI Pipeline — Build test_remote.exe ===
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

:: Auto-detect next version by scanning dist\ for existing test_remote_vN.exe files
set NEXT_VER=1
if exist dist\ (
    for /l %%i in (1,1,99) do (
        if exist "dist\test_remote_v%%i.exe" set NEXT_VER=%%i
    )
    set /a NEXT_VER=NEXT_VER+1
)

echo   Detected next version : v%NEXT_VER%
echo   Output will be        : dist\test_remote_v%NEXT_VER%.exe
echo.

:: Clean previous build artifacts (not the exe itself)
if exist "build\test_remote" (
    rmdir /s /q "build\test_remote"
)

echo Building test_remote_v%NEXT_VER%.exe - this may take a minute...
echo.

:: Build the exe
pyinstaller --noconfirm --onefile --console ^
    --name test_remote_v%NEXT_VER% ^
    --hidden-import requests ^
    --hidden-import urllib3 ^
    --hidden-import certifi ^
    --hidden-import charset_normalizer ^
    test_remote.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed. See output above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  BUILD COMPLETE
echo  Output: dist\test_remote_v%NEXT_VER%.exe
echo ============================================================
echo.
echo Share dist\test_remote_v%NEXT_VER%.exe with remote users.
echo They just double-click it — no Python needed!
echo.
echo Make sure start_comfyui.py and start_ngrok.py are running
echo on the GPU machine before users run the exe.
echo.
pause
