#!/bin/bash
# Double-click to start Bear Pomodoro on macOS (experimental). Installs Pillow on first run.
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install it from https://www.python.org/downloads/ and try again."
  read -n 1 -s -r -p "Press any key to close"; exit 1
fi
python3 -c "import PIL" >/dev/null 2>&1 || python3 -m pip install -r requirements.txt || { echo "Install failed."; read -n 1 -s -r -p "Press any key"; exit 1; }
nohup python3 bear_pomodoro.py >/dev/null 2>&1 &
