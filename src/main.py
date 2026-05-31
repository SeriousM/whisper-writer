import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor, QIcon
from ui.ui_manager import UIManager
from application_controller import ApplicationController
from event_bus import EventBus
from config_manager import ConfigManager


class _NullStream:
    """Stand-in for sys.stdout/stderr when running as a --windowed PyInstaller exe.
    Some libs (tqdm, huggingface_hub) call .write/.flush and crash on None."""
    def write(self, *a, **kw):
        return 0
    def flush(self):
        pass
    def isatty(self):
        return False
    def fileno(self):
        raise OSError('no fileno in windowed mode')


def _ensure_std_streams():
    if sys.stdout is None:
        sys.stdout = _NullStream()
    if sys.stderr is None:
        sys.stderr = _NullStream()


def _resource_path(*parts) -> str:
    """Find a bundled resource both in dev tree and in a PyInstaller bundle."""
    candidates = []
    base = getattr(sys, '_MEIPASS', None)
    if base:
        candidates.append(os.path.join(base, *parts))
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, '..', *parts))
    candidates.append(os.path.join(os.getcwd(), *parts))
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(*parts)


def _set_windows_app_id():
    """Tell Windows this is its own app so the taskbar uses our icon, not Python's."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('WhisperWriter.App.1')
    except Exception:
        pass


def _apply_dark_theme(app: QApplication):
    """Apply a consistent dark palette across the whole app."""
    app.setStyle('Fusion')
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Button, QColor(60, 60, 63))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 80, 80))
    palette.setColor(QPalette.ColorRole.Link, QColor(64, 156, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(140, 140, 140))
    # Disabled state
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(120, 120, 120))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(120, 120, 120))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(120, 120, 120))
    app.setPalette(palette)


def main():
    _ensure_std_streams()
    _set_windows_app_id()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName('WhisperWriter')
    # Set the app icon for window decorations and Windows taskbar
    icon_path = _resource_path('assets', 'ww-logo.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    _apply_dark_theme(app)

    event_bus = EventBus()
    ConfigManager.initialize(event_bus)
    ui_manager = UIManager(event_bus)

    controller = ApplicationController(ui_manager, event_bus)

    exit_code = controller.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
