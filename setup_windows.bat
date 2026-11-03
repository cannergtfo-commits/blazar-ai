@echo off
setlocal
title Blazar AI - Installer
color 0B
cd /d "%~dp0"
echo ============================================
echo   Blazar AI - One-click Installer
echo ============================================
echo.

call :findpy
if not defined PY (
    echo Python not found. Installing Python 3.12 via winget...
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    call :refreshpath
    call :findpy
)
if not defined PY (
    echo ERROR: Python could not be installed. Install it from https://python.org and run this again.
    pause
    exit /b 1
)
echo [OK] Python: %PY%

call :findollama
if not defined OLLAMA (
    echo Ollama not found. Installing via winget...
    winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
    call :refreshpath
    call :findollama
)
if defined OLLAMA (
    echo [OK] Ollama: %OLLAMA%
    for %%D in ("%OLLAMA%") do set "PATH=%%~dpD;%PATH%"
) else (
    echo WARNING: Ollama not found. Install from https://ollama.com - chat needs it.
)

echo.
"%PY%" setup.py
echo.
echo ============================================
echo   Done! Double-click "Blazar AI" on your Desktop
echo   (or start_ui.bat in this folder).
echo ============================================
pause
exit /b 0

:findpy
set "PY="
for %%V in (313 312 311 310) do (
    if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
)
if not defined PY (
    py -3 -c "import sys" >nul 2>&1 && for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)"') do set "PY=%%P"
)
if not defined PY (
    python -c "import sys;assert sys.version_info>=(3,10)" >nul 2>&1 && for /f "delims=" %%P in ('python -c "import sys;print(sys.executable)"') do set "PY=%%P"
)
exit /b 0

:findollama
set "OLLAMA="
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not defined OLLAMA for /f "delims=" %%O in ('where ollama 2^>nul') do if not defined OLLAMA set "OLLAMA=%%O"
exit /b 0

:refreshpath
for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul ^| find "Path"') do set "UPATH=%%B"
for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul ^| find "Path"') do set "MPATH=%%B"
set "PATH=%MPATH%;%UPATH%;%PATH%"
exit /b 0
