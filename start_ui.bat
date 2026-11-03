@echo off
setlocal
title Blazar AI
cd /d "%~dp0"

set "PY="
for %%V in (313 312 311 310) do (
    if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
)
if not defined PY (
    py -3 -c "import sys" >nul 2>&1 && for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)"') do set "PY=%%P"
)
if not defined PY set "PY=python"

set "OLLAMA=ollama"
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
curl -s -o nul http://localhost:11434/api/tags
if errorlevel 1 (
    echo Starting Ollama...
    start "" /min "%OLLAMA%" serve
    timeout /t 3 /nobreak >nul
)

echo Starting Blazar AI at http://localhost:7860 ...
start "" cmd /c "timeout /t 6 /nobreak >nul & start http://localhost:7860"
"%PY%" ui\app.py
pause
