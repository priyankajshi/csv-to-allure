#!/bin/bash
set -e

# Ensure PyInstaller is installed
pip install -r requirements.txt

# Clean previous builds
rm -rf build dist *.spec

# Build the executable
# --onefile: Create a single executable file
# --name: Name of the output file
# --hidden-import: Explicitly import hidden dependencies if needed
pyinstaller --onefile --name migration src/main.py

echo "Build complete! Executable is located at dist/migration"
