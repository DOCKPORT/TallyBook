#!/bin/bash
# Get the absolute directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Explicitly use the virtual environment the user is actually using
VENV_PYTHON="/home/dockport/DOCK-HQ/DEV/venv/bin/python"

# Fallback check if the above doesn't exist
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="$DIR/../venv/bin/python"
fi

# Final fallback
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

# Run the project
$VENV_PYTHON TallyBook.py
