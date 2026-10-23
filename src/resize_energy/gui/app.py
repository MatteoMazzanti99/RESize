"""Entry point of the RESize desktop application."""

from __future__ import annotations

import sys


def _walk_through(window, app) -> int:
    """Run every technology flow with its default values, up to the results page."""
    for tech in ("pv", "wind"):
        window._start(tech)
        for _ in range(3):
            window._next()
            app.processEvents()
        results = window.pages[-1]
        if window.index != len(window.pages) - 1 or "Design checks" not in results.html:
            print(f"self-test: the {tech} flow did not reach its results", flush=True)
            return 1
        window._restart()
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the app. ``--self-test`` builds the main window, then exits (used by CI/releases)."""
    args = sys.argv if argv is None else argv
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("The GUI needs PySide6. Install it with: pip install 'resize-energy[gui]'")
        return 1

    from resize_energy.gui.brand import logo_icon
    from resize_energy.gui.main_window import MainWindow
    from resize_energy.gui.theme import apply_theme

    app = QApplication(args)
    app.setApplicationName("RESize")
    apply_theme(app)
    app.setWindowIcon(logo_icon())
    window = MainWindow()
    print("main window built", flush=True)
    if "--self-test" in args:
        window.show()
        app.processEvents()
        code = _walk_through(window, app)
        print("RESize self-test OK" if code == 0 else "RESize self-test FAILED", flush=True)
    else:
        window.show()
        code = app.exec()
    # Destroy widgets before the QApplication: the reverse order can crash at interpreter exit.
    window.deleteLater()
    app.processEvents()
    del window
    return code


if __name__ == "__main__":
    sys.exit(main())
