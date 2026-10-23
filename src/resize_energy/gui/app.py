"""Entry point of the RESize desktop application."""

from __future__ import annotations

import sys


def _walk_through(window, app) -> int:
    """Run every technology flow with its default values, up to the results page."""
    from resize_energy.core.turbine_library import load_library

    if len(load_library()) < 10:
        print("self-test: the turbine library is missing from the build", flush=True)
        return 1
    markers = {"pv": "Design checks", "wind": "Design checks", "biomass": "Design checks", "hydrogen": "Design checks", "compare": "Which is better"}
    for tech, marker in markers.items():
        window._start(tech)
        for _ in range(len(window.pages) - 2):
            window._next()
            app.processEvents()
        results = window.pages[-1]
        if window.index != len(window.pages) - 1 or marker not in results.html:
            print(f"self-test: the {tech} flow did not reach its results", flush=True)
            return 1
        window._restart()
    # the comparison of all four technologies, as started from the Compare zone
    window._start_compare(["pv", "wind", "biomass", "hydrogen"])
    for _ in range(len(window.pages) - 2):
        window._next()
        app.processEvents()
    if window.index != len(window.pages) - 1 or "Biomass" not in window.pages[-1].html:
        print("self-test: the four-technology comparison did not reach its results", flush=True)
        return 1
    window._restart()
    return 0


def _screenshots(window, app, folder: str) -> None:
    """Save a picture of the home page and of the first and last step of every flow."""
    from pathlib import Path

    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    window.resize(1240, 820)
    app.processEvents()
    window.grab().save(str(out / "home.png"))
    zone = window.home.zone
    for key in ("pv", "hydrogen", "biomass"):
        zone.add(key)
    for _ in range(25):  # let the icons drift for a moment
        app.processEvents()
    window.grab().save(str(out / "home_compare.png"))
    zone.clear()
    for tech in ("pv", "wind", "biomass", "hydrogen", "compare"):
        window._start(tech)
        app.processEvents()
        window.grab().save(str(out / f"{tech}_1.png"))
        for _ in range(len(window.pages) - 2):
            window._next()
            app.processEvents()
            if window.index == 3:
                window.grab().save(str(out / f"{tech}_3.png"))
        app.processEvents()
        window.grab().save(str(out / f"{tech}_4.png"))
        window._restart()


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
        if "--screenshots" in args:
            _screenshots(window, app, args[args.index("--screenshots") + 1])
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
