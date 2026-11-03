@echo off
title Blazar AI Installer
color 0B

echo ========================================
echo   Blazar AI Installer
echo ========================================
echo.
echo This will install everything and download the AI model.
echo The model download can take 30-90 minutes depending on your internet speed.
echo.
echo Press any key to start...
pause >nul

:: Progress popup - Starting
powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Starting install...\n\nThis can take 30-90 minutes mainly for the model download.\n\nA console window will show live progress.','Blazar AI Installer','OK','Information')"

echo.
echo [1/5] Installing Python packages...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install packages.
    pause
    exit /b 1
)

echo.
echo [2/5] Checking Ollama...
ollama list >nul 2>&1
if errorlevel 1 (
    echo Ollama not found. Please install from https://ollama.com and run 'ollama serve'
    pause
    exit /b 1
)

echo.
echo [3/5] Downloading the AI model (~18 GB)...
echo This is the long part. Progress will show below.
echo.
powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Downloading the AI model now (~18 GB).\n\nThis usually takes 30-90 minutes.\n\nWatch the console window for live download progress.','Blazar AI - Model Download','OK','Information')"

ollama pull qwen3:30b-a3b

echo.
echo [4/5] Creating optimized model...
if exist Modelfile.cpu (
    ollama create qwen3-30b-cpu -f Modelfile.cpu
)

echo.
echo [5/5] Creating folders and desktop shortcut...
python setup.py

echo.
echo ========================================
echo   Install complete!
echo ========================================
echo.
echo A shortcut was placed on your Desktop.
echo Double-click "blazar-ai.bat" to launch.
echo.
powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Install complete!\n\nDouble-click the blazar-ai shortcut on your Desktop to start.','Blazar AI Ready','OK','Information')"

pause
