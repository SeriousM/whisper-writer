"""
Local model downloader for transcription backends.

Stores models in a portable `models/` folder next to the executable when
frozen by PyInstaller, otherwise next to the project root. Falls back to
~/.whisper-writer/models when neither is writable.
"""
import os
import sys
import shutil
import zipfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable, Optional, Dict, List


# ---------------------------------------------------------------------------
# Known model catalogues
# ---------------------------------------------------------------------------

# Faster Whisper models hosted by Systran on HuggingFace
FASTER_WHISPER_REPOS: Dict[str, str] = {
    'tiny':        'Systran/faster-whisper-tiny',
    'tiny.en':     'Systran/faster-whisper-tiny.en',
    'base':        'Systran/faster-whisper-base',
    'base.en':     'Systran/faster-whisper-base.en',
    'small':       'Systran/faster-whisper-small',
    'small.en':    'Systran/faster-whisper-small.en',
    'medium':      'Systran/faster-whisper-medium',
    'medium.en':   'Systran/faster-whisper-medium.en',
    'large':       'Systran/faster-whisper-large-v3',
    'large-v1':    'Systran/faster-whisper-large-v1',
    'large-v2':    'Systran/faster-whisper-large-v2',
    'large-v3':    'Systran/faster-whisper-large-v3',
}

# Vosk models from https://alphacephei.com/vosk/models
# (kept conservative — only widely useful sizes)
VOSK_MODELS: Dict[str, str] = {
    'vosk-model-small-en-us-0.15':  'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip',
    'vosk-model-en-us-0.22':        'https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip',
    'vosk-model-en-us-0.22-lgraph': 'https://alphacephei.com/vosk/models/vosk-model-en-us-0.22-lgraph.zip',
    'vosk-model-small-de-0.15':     'https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip',
    'vosk-model-de-0.21':           'https://alphacephei.com/vosk/models/vosk-model-de-0.21.zip',
    'vosk-model-small-fr-0.22':     'https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip',
    'vosk-model-small-es-0.42':     'https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip',
    'vosk-model-small-ru-0.22':     'https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip',
    'vosk-model-small-cn-0.22':     'https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip',
    'vosk-model-small-ja-0.22':     'https://alphacephei.com/vosk/models/vosk-model-small-ja-0.22.zip',
}


ProgressCB = Callable[[int, int, str], None]  # (current, total, message)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def get_models_dir() -> Path:
    """Return the base directory for downloaded models. Portable when possible."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle — store next to the exe so it's portable
        base = Path(sys.executable).parent / 'models'
    else:
        # Dev mode — alongside the repo
        base = Path(__file__).resolve().parent.parent / 'models'

    try:
        base.mkdir(parents=True, exist_ok=True)
        # Test writability
        probe = base / '.write_test'
        probe.touch()
        probe.unlink()
        return base
    except (OSError, PermissionError):
        # Fallback to user dir
        fallback = Path.home() / '.whisper-writer' / 'models'
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def faster_whisper_dir(model_name: str) -> Path:
    return get_models_dir() / 'faster-whisper' / model_name


def vosk_dir(model_name: str) -> Path:
    return get_models_dir() / 'vosk' / model_name


# ---------------------------------------------------------------------------
# Downloaders
# ---------------------------------------------------------------------------

def _http_download(url: str, dest: Path, progress: Optional[ProgressCB] = None,
                   label: str = '') -> None:
    """Download URL to dest path with optional progress callback."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'whisper-writer/1.0'})
    with urllib.request.urlopen(req) as response:
        total = int(response.headers.get('Content-Length', 0))
        downloaded = 0
        chunk = 1024 * 64
        with open(dest, 'wb') as f:
            while True:
                buf = response.read(chunk)
                if not buf:
                    break
                f.write(buf)
                downloaded += len(buf)
                if progress:
                    progress(downloaded, total, label or f'Downloading {dest.name}')


def download_faster_whisper(model_name: str,
                            progress: Optional[ProgressCB] = None) -> Path:
    """
    Download a Faster Whisper model snapshot to a local folder.
    Returns the local directory containing the model files.
    """
    if model_name not in FASTER_WHISPER_REPOS:
        raise ValueError(f"Unknown faster_whisper model: {model_name}")

    target = faster_whisper_dir(model_name)
    if (target / 'model.bin').exists() or (target / 'config.json').exists():
        if progress:
            progress(1, 1, f'Model already present at {target}')
        return target

    try:
        from huggingface_hub import snapshot_download
    except ImportError as e:
        raise RuntimeError(
            'huggingface_hub is required to download Faster Whisper models. '
            'Install it with: pip install huggingface_hub'
        ) from e

    repo_id = FASTER_WHISPER_REPOS[model_name]
    if progress:
        progress(0, 0, f'Downloading {repo_id} from HuggingFace...')

    # Force tqdm off (no TTY in --windowed PyInstaller exe)
    os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
    os.environ['TQDM_DISABLE'] = '1'

    target.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(target),
        # Skip optional ONNX/TF files to keep size down
        ignore_patterns=['*.onnx', '*.h5', '*.msgpack', '*.ot', '*.bin.index.json'],
    )

    if progress:
        progress(1, 1, f'Done: {target}')
    return target


def download_vosk(model_name: str,
                  progress: Optional[ProgressCB] = None) -> Path:
    """
    Download and extract a Vosk model zip to a local folder.
    Returns the local directory containing the unpacked model.
    """
    if model_name not in VOSK_MODELS:
        raise ValueError(f"Unknown vosk model: {model_name}")

    target = vosk_dir(model_name)
    # Vosk model is "ready" if it contains the standard subdirs
    if (target / 'am').exists() and (target / 'conf').exists():
        if progress:
            progress(1, 1, f'Model already present at {target}')
        return target

    url = VOSK_MODELS[model_name]
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        _http_download(url, tmp_path, progress, label=f'Downloading {model_name}')

        if progress:
            progress(0, 0, f'Extracting {model_name}...')

        # Extract to parent, then rename top-level folder to model_name
        with zipfile.ZipFile(tmp_path) as zf:
            # The zip usually contains a single top-level dir named after the model
            top_dirs = {Path(n).parts[0] for n in zf.namelist() if n}
            extract_to = target.parent
            zf.extractall(extract_to)

        # If extracted dir name differs from target, rename it
        if len(top_dirs) == 1:
            extracted = target.parent / list(top_dirs)[0]
            if extracted != target and extracted.exists():
                if target.exists():
                    shutil.rmtree(target)
                extracted.rename(target)

        if progress:
            progress(1, 1, f'Done: {target}')
        return target
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Convenience: list locally installed models
# ---------------------------------------------------------------------------

def list_local_faster_whisper() -> List[str]:
    root = get_models_dir() / 'faster-whisper'
    if not root.exists():
        return []
    return sorted([d.name for d in root.iterdir() if d.is_dir()])


def list_local_vosk() -> List[str]:
    root = get_models_dir() / 'vosk'
    if not root.exists():
        return []
    return sorted([d.name for d in root.iterdir() if d.is_dir()])
