"""Entry point of the RESize desktop application."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("The GUI needs PySide6. Install it with: pip install 'resize-energy[gui]'")
        return 1

    from resize_energy.gui.wizard import PVWizard

    app = QApplication(sys.argv)
    app.setApplicationName("RESize")
    wizard = PVWizard()
    wizard.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
