import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from ui.ui_manager import UIManager
from application_controller import ApplicationController
from event_bus import EventBus
from config_manager import ConfigManager


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
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    _apply_dark_theme(app)

    event_bus = EventBus()
    ConfigManager.initialize(event_bus)
    ui_manager = UIManager(event_bus)

    controller = ApplicationController(ui_manager, event_bus)

    exit_code = controller.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
