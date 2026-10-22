"""Entry point of the desktop application (placeholder window for now)."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
    except ImportError:
        print("The GUI needs PySide6. Install it with: pip install 'resize-energy[gui]'")
        return 1

    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("RESize")
    label = QLabel("RESize: renewable energy sizing tutor (pre-alpha)")
    label.setMargin(24)
    window.setCentralWidget(label)
    window.resize(640, 360)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
