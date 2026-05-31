# Project state

Snapshot of the Windows-build work done so far on this fork.

## What works

- **Portable Windows `.exe`** built with PyInstaller (one-file, no console window).
- **Dark theme** applied app-wide via Qt Fusion style + custom `QPalette`.
- **Local model download** inside the Settings window for both local backends:
  - **Faster Whisper** — pulled from the official `Systran/faster-whisper-*` repos on HuggingFace.
  - **Vosk** — zip archives from `alphacephei.com/vosk/models`, auto-extracted.
- **Portable model storage** — models land in `models/<backend>/<name>/` next to the `.exe` (falls back to `~/.whisper-writer/models` if that folder isn't writable).
- **Backends auto-pick local models** when `model_path` is empty.
- **Windows taskbar icon** uses the WhisperWriter logo (via `SetCurrentProcessExplicitAppUserModelID`).
- **GitHub Actions workflow** (manual dispatch) builds the same exe on `windows-latest` and optionally publishes a draft release.

## Build entry points

| File | Use when |
|---|---|
| `build_windows_exe.sh` | Building locally in Git Bash / MSYS2 / WSL (uses `mise` for Python 3.12). |
| `build_windows_exe.bat` | Building locally in `cmd.exe` / Explorer double-click. |
| `.github/workflows/build-windows-exe.yml` | "Build Windows Executable" → "Run workflow" in the Actions tab. Optional inputs: `tag_name`, `create_release`. |

All three use the same proven PyInstaller invocation:

```
python -m PyInstaller
  --onefile --windowed
  --name WhisperWriter
  --icon assets/ww-logo.ico
  --paths src
  --add-data "assets;assets"
  --add-data "src/config_schema.yaml;."
  --collect-all faster_whisper
  --collect-all ctranslate2
  --collect-all tokenizers
  --collect-all onnxruntime
  --collect-all pkg_resources
  --collect-all huggingface_hub
  --hidden-import pkg_resources
  src/main.py
```

Plus the dependency pin `setuptools<81` (newer setuptools dropped `pkg_resources`, which `webrtcvad` still imports).

## Why each flag exists

| Flag | Reason |
|---|---|
| Module name `PyInstaller` (capitalised) | Lowercase `pyinstaller` is the dist name, the Python module is `PyInstaller`. |
| `--paths src` | `src/main.py` does `from ui.ui_manager import ...` — siblings need to be on `sys.path`. |
| `--add-data "assets;assets"` | Logo + sound files looked up at runtime. |
| `--add-data "src/config_schema.yaml;."` | Loaded by `ConfigManager.initialize()`. |
| `--collect-all faster_whisper / ctranslate2 / tokenizers / onnxruntime` | Native ML runtime DLLs that PyInstaller's static analysis misses. |
| `--collect-all pkg_resources` + `--hidden-import pkg_resources` | `webrtcvad` imports `pkg_resources` at module top. |
| `--collect-all huggingface_hub` | Used by the model downloader inside the bundled exe. |

## Windows-specific source changes

| File | Change |
|---|---|
| `src/main.py` | Adds `_NullStream` so `sys.stdout/stderr` aren't `None` in `--windowed` mode (otherwise tqdm/huggingface_hub crashes). Sets the QApplication icon. Calls `SetCurrentProcessExplicitAppUserModelID` for taskbar grouping. Applies dark Fusion theme. |
| `src/output_manager.py` | `import fcntl` is now guarded by `sys.platform != 'win32'` — `fcntl` is Unix-only and is only used by the Linux `UinputBackend`. |
| `src/config_manager.py` | `config_schema.yaml` is resolved against `sys._MEIPASS`, the module dir, and the legacy `src/` path — works in dev, frozen exe, and any CWD. |
| `src/transcription_backend/faster_whisper_backend.py` | When `model_path` is empty, looks for a previously-downloaded folder under `models/faster-whisper/<model>/` before falling back to the online HuggingFace cache. |
| `src/transcription_backend/vosk_backend.py` | When `model_path` is empty, uses `model_downloader.vosk_dir(model_name)`; raises a helpful error if the user hasn't downloaded it yet. |
| `src/model_downloader.py` | New module: catalogues + downloaders for both backends, portable models dir, progress callback. |
| `src/ui/settings_window.py` | New "Download model" button in the Backend group (only shown for `faster_whisper` / `vosk`). Runs the download on a `QThread` with a `QProgressDialog`. |
| `src/ui/base_window.py`, `main_window.py`, `status_window.py` | Dark colour scheme tweaks coordinated with the palette in `main.py`. |
| `src/config_schema.yaml` | Vosk gained a `model` dropdown (small/large variants in EN/DE/FR/ES/RU/CN/JA). `model_path` default cleared so the auto-resolution kicks in. |

## How to ship a release

1. **GitHub Actions** → "Build Windows Executable" → "Run workflow".
2. Tick **Create a GitHub Release** and set `tag_name`, e.g. `v1.0.2-windows`.
3. After the run, find the draft release on the Releases page, write notes, hit Publish.

The artifact is also uploaded under the run as `WhisperWriter-windows` (30-day retention) so you can grab it without making a release.

## Known follow-ups / nice-to-haves

- The `.exe` is ~150 MB because we bundle the full PyQt6 Qt6 runtime plus ML libs. Could shave it down with `--exclude-module` for unused Qt modules (QtWebEngine etc., if they're even getting pulled in).
- Faster Whisper GPU support (`device=cuda`) needs CUDA/cuDNN DLLs which aren't bundled. Right now the exe is CPU-only out of the box.
- No code-signing → SmartScreen will warn on first launch. Sign with an EV certificate (or at least `signtool` with a normal cert) before wide distribution.
- The Vosk catalogue in `model_downloader.py` is hand-maintained. Could fetch it dynamically from `https://alphacephei.com/vosk/models/model-list.json`.
- The `models/` directory next to the `.exe` is created automatically on first download; document this in the README so users know where the data goes.
