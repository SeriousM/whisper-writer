#!/bin/bash
# =====================================================
# Build WhisperWriter Windows Executable
# Uses mise to install Python 3.12, then PyInstaller to build
# Works in Git Bash / MSYS2 / WSL on Windows
# =====================================================
set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

echo "[STEP 1/4] Ensuring mise + Python 3.12 are installed..."
if ! command -v mise &> /dev/null; then
    curl https://mise.run | bash -s
    export PATH="$HOME/.local/bin:$PATH"
fi
mise use python@3.12 --global

# Locate the actual mise python.exe (Git Bash path)
MISE_PY=""
for candidate in \
    "/c/Users/$USER/AppData/Local/mise/installs/python/3.12.13/python.exe" \
    "/c/Users/$USERNAME/AppData/Local/mise/installs/python/3.12.13/python.exe" \
    "$HOME/.local/share/mise/installs/python/3.12.13/bin/python" \
    "$(mise which python 2>/dev/null)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        MISE_PY="$candidate"
        break
    fi
done

if [ -z "$MISE_PY" ]; then
    echo "ERROR: Could not find mise-installed Python 3.12"
    exit 1
fi
echo "Using Python: $MISE_PY"
echo ""

echo "[STEP 2/4] Installing PyInstaller + dependencies..."
"$MISE_PY" -m pip install --upgrade pip --quiet
"$MISE_PY" -m pip install pyinstaller PyQt6 PyYAML numpy scipy soundfile \
    webrtcvad pynput PyAudio cffi faster-whisper==1.0.3 "setuptools<81" --quiet
echo ""

echo "[STEP 3/4] Cleaning previous build artifacts..."
rm -rf build dist WhisperWriter.spec
echo ""

echo "[STEP 4/4] Building Windows executable (this takes 1-2 minutes)..."
# NOTE: PyInstaller module name is 'PyInstaller' (capitalized)
"$MISE_PY" -m PyInstaller \
    --onefile \
    --windowed \
    --name WhisperWriter \
    --icon assets/ww-logo.ico \
    --paths src \
    --add-data "assets;assets" \
    --add-data "src/config_schema.yaml;." \
    --collect-all faster_whisper \
    --collect-all ctranslate2 \
    --collect-all tokenizers \
    --collect-all onnxruntime \
    --collect-all pkg_resources \
    --hidden-import pkg_resources \
    src/main.py

echo ""
echo "============================================="
if [ -f dist/WhisperWriter.exe ]; then
    SIZE=$(du -h dist/WhisperWriter.exe | cut -f1)
    echo "[SUCCESS] Build completed!"
    echo "Output: dist/WhisperWriter.exe ($SIZE)"
    echo "============================================="
    echo ""
    echo "Run it with: ./dist/WhisperWriter.exe"
    echo "Or copy it to any Windows machine - no install needed."
else
    echo "[ERROR] Build failed - no exe found in dist/"
    exit 1
fi
