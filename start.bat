@echo off
rem Double-click to start Bear Pomodoro. Installs Pillow on first run.
cd /d "%~dp0"
where pythonw >nul 2>nul
if errorlevel 1 (
  echo Python 3 was not found. Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during setup, then double-click this file again.
  pause
  exit /b 1
)
python -c "import PIL" >nul 2>nul
if errorlevel 1 (
  echo Installing Pillow, one moment...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Install failed. Check your network and try again.
    pause
    exit /b 1
  )
)
start "" pythonw bear_pomodoro.py
