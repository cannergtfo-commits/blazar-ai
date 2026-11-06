@echo off
REM Blazar AI job runner — manual only. Drains queue\ then exits and unloads the model.
cd /d "%~dp0"
if exist paused.flag (
  echo paused.flag is set — remove it to run.
  pause
  exit /b 1
)
"C:\Users\canne\AppData\Local\Programs\Python\Python312\python.exe" "%~dp0runner.py" %*
set RC=%ERRORLEVEL%
echo.
echo Done. Exit code %RC%. Model unload is handled by the runner.
exit /b %RC%
