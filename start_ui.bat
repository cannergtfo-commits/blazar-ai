@echo off
cd /d "%~dp0"
echo Starting blazar-ai...
echo Opening http://localhost:7860 in your browser...
start "" "http://localhost:7860"
python ui\app.py
pause
