@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

if not exist "%PROJECT_ROOT%venv\Scripts\python.exe" (
  echo [ERROR] Python virtual environment not found at:
  echo         %PROJECT_ROOT%venv\Scripts\python.exe
  echo.
  echo Run setup first, then try again.
  pause
  exit /b 1
)

echo Launching SOC Copilot...
"%PROJECT_ROOT%venv\Scripts\python.exe" "%PROJECT_ROOT%launch_ui.py"

if errorlevel 1 (
  echo.
  echo [ERROR] SOC Copilot exited with an error.
  pause
)

endlocal
