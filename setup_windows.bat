@echo off
title Blazar AI — Smart Installer
color 0B
cd /d "%~dp0"

echo ============================================
echo   Blazar AI — Smart Installer
echo ============================================
echo.
echo Checking what is already installed...
echo.

:: --- Check Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Installing via winget...
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    echo.
    echo IMPORTANT: Close this window and open a NEW Command Prompt, then re-run this installer.
    echo (PATH needs to refresh after Python install)
    pause
    exit /b 1
) else (
    echo [OK] Python found:
    python --version
)

:: --- Check Ollama ---
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Ollama not found. Installing via winget...
    winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
    echo.
    echo IMPORTANT: Close this window and open a NEW Command Prompt, then re-run this installer.
    echo (PATH needs to refresh after Ollama install)
    pause
    exit /b 1
) else (
    echo [OK] Ollama found:
    ollama --version
)

echo.
echo All prerequisites look good. Starting full setup...
echo.
python setup.py

echo.
echo ============================================
echo   Installer finished
echo ============================================
echo.
echo Look for the "Start Blazar AI.bat" or desktop shortcut.
echo Double-click it to launch the workspace at http://localhost:7860
echo.
pause
