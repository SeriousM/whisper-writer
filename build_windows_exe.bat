@echo off
REM =====================================================
REM Build WhisperWriter Windows Executable (cmd.exe)
REM Requires: mise (https://mise.run) OR Python 3.12 on PATH
REM =====================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo [STEP 1/4] Ensuring Python 3.12 is available...

REM Prefer mise-installed Python if available
set "PY="
if exist "%LOCALAPPDATA%\mise\installs\python\3.12.13\python.exe" (
    set "PY=%LOCALAPPDATA%\mise\installs\python\3.12.13\python.exe"
) else (
    where mise >nul 2>nul
    if !errorlevel! equ 0 (
        echo Installing Python 3.12 via mise...
        mise use python@3.12 --global
        if exist "%LOCALAPPDATA%\mise\installs\python\3.12.13\python.exe" (
            set "PY=%LOCALAPPDATA%\mise\installs\python\3.12.13\python.exe"
        )
    )
)

REM Fallback: any Python 3.12 on PATH
if "!PY!"=="" (
    where py >nul 2>nul && (
        for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "PY=%%P"
    )
)
if "!PY!"=="" (
    where python >nul 2>nul && set "PY=python"
)

if "!PY!"=="" (
    echo [ERROR] No Python 3.12 found. Install mise from https://mise.run or Python 3.12 from python.org
    exit /b 1
)

echo Using Python: !PY!
"!PY!" --version
echo.

echo [STEP 2/4] Installing PyInstaller and dependencies...
"!PY!" -m pip install --upgrade pip --quiet
if errorlevel 1 exit /b 1
"!PY!" -m pip install pyinstaller PyQt6 PyYAML numpy scipy soundfile webrtcvad pynput PyAudio cffi faster-whisper==1.0.3 "setuptools<81" --quiet
if errorlevel 1 exit /b 1
echo.

echo [STEP 3/4] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist WhisperWriter.spec del /q WhisperWriter.spec
echo.

echo [STEP 4/4] Building Windows executable (this takes 1-2 minutes)...
REM NOTE: PyInstaller module name is capitalized
"!PY!" -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name WhisperWriter ^
    --icon assets/ww-logo.ico ^
    --paths src ^
    --add-data "assets;assets" ^
    --add-data "src/config_schema.yaml;." ^
    --collect-all faster_whisper ^
    --collect-all ctranslate2 ^
    --collect-all tokenizers ^
    --collect-all onnxruntime ^
    --collect-all pkg_resources ^
    --collect-all huggingface_hub ^
    --hidden-import pkg_resources ^
    src/main.py
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)
echo.

if exist dist\WhisperWriter.exe (
    echo =============================================
    echo [SUCCESS] Build completed!
    echo Output: dist\WhisperWriter.exe
    echo =============================================
    echo.
    echo Run it with: dist\WhisperWriter.exe
) else (
    echo [ERROR] Build finished but no exe found in dist\
    exit /b 1
)

endlocal
