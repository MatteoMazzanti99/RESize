"""Entry point of the RESize desktop application."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Run the app. ``--self-test`` builds the main window, then exits (used by CI/releases)."""
    args = sys.argv if argv is None else argv
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("The GUI needs PySide6. Install it with: pip install 'resize-energy[gui]'")
        return 1

    from resize_energy.gui.brand import logo_icon
    from resize_energy.gui.theme import apply_theme
    from resize_energy.gui.wizard import MainWindow

    app = QApplication(args)
    app.setApplicationName("RESize")
    apply_theme(app)
    app.setWindowIcon(logo_icon())
    window = MainWindow()
    if "--self-test" in args:
        window.show()
        app.processEvents()
        print("RESize self-test OK")
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
