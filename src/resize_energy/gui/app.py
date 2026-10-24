"""Entry point of the RESize desktop application."""

from __future__ import annotations

import sys


def _walk_through(window, app) -> int:
    """Run every technology flow with its default values, up to the results page."""
    from resize_energy.core.turbine_library import load_library

    if len(load_library()) < 10:
        print("self-test: the turbine library is missing from the build", flush=True)
        return 1
    markers = {"pv": "Design checks", "wind": "Design checks", "biomass": "Design checks", "hydrogen": "Design checks", "battery": "Design checks", "solar": "Design checks", "compare": "Which is better"}
    for tech, marker in markers.items():
        window._start(tech)
        for _ in range(len(window.pages) - 2):
            window._next()
            app.processEvents()
        results = window.pages[-1]
        if window.index != len(window.pages) - 1 or marker not in results.html:
            print(f"self-test: the {tech} flow did not reach its results", flush=True)
            return 1
        if tech in ("pv", "wind", "solar") and "Which values to check" not in results.html:
            print(f"self-test: the {tech} results lack the list of values to check", flush=True)
            return 1
        if tech in ("pv", "wind") and "Net present value" not in results.html:
            print(f"self-test: the {tech} results lack the economics", flush=True)
            return 1
        if tech in ("pv", "wind", "biomass", "hydrogen", "battery", "solar"):
            try:
                wb = results._workbook()
            except ImportError:
                wb = None
            if wb is None or "Check" not in wb.sheetnames:
                print(f"self-test: the {tech} Excel workbook was not built", flush=True)
                return 1
        if tech != "compare" and (results.banner.picture is None
                                  or results.chart_images["chart:flow_banner"].isNull()):
            print(f"self-test: the {tech} energy-flow picture is missing", flush=True)
            return 1
        if not results.chart_images or any(i.isNull() for i in results.chart_images.values()):
            print(f"self-test: the {tech} charts were not drawn", flush=True)
            return 1
        if not _formulas_drawn(results):
            print(f"self-test: the {tech} formulas were not drawn", flush=True)
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
    if len(window.pages[-1].chart_images) < 4:
        print("self-test: the comparison charts were not drawn", flush=True)
        return 1
    window._restart()
    for check in (_versions_check, _solar_cooling_check, _country_check, _step_art_check):
        code = check(window, app)
        if code:
            return code
    return _project_roundtrip(window, app)


def _versions_check(window, app) -> int:
    """Keep a PV version, change the demand, come back: the report compares and explains."""
    from resize_energy.gui import versions_ui

    window._start("pv")
    for _ in range(len(window.pages) - 2):
        window._next()
        app.processEvents()
    results = window.results
    if not versions_ui.keep(results):
        print("self-test: could not keep a version", flush=True)
        return 1
    window.load.demand.set_value(9000)
    results.initializePage()
    if "Compared with version A" not in results.html:
        print("self-test: the comparison with version A is missing", flush=True)
        return 1
    results._explained = versions_ui.explain(results)
    results._compose()
    ok = ("Why did it change?" in results.html and window.load.demand.value() == 9000
          and "Annual electricity demand" in results.html)
    window._restart()
    if not ok:
        print("self-test: the explanation of the changes failed", flush=True)
        return 1
    return 0


def _solar_cooling_check(window, app) -> int:
    """Solar thermal with cooling added: three cooling technologies are compared."""
    window._start("solar")
    load = window.sol_load
    load.use_cooling.setChecked(True)
    for key in ("absorption", "desiccant"):
        getattr(load, f"compare_{key}").setChecked(True)
    for _ in range(len(window.pages) - 2):
        window._next()
        app.processEvents()
    results = window.sol_results
    ok = (window.index == len(window.pages) - 1 and "Cooling technologies" in results.html
          and "solar_chillers" in {k.split(":")[-1] for k in results.chart_images})
    window._restart()
    if not ok:
        print("self-test: the solar cooling comparison did not appear", flush=True)
        return 1
    return 0


def _formulas_drawn(results) -> bool:
    """Every 'Why?' topic of the results page gives a formula picture that can be loaded."""
    import re

    from resize_energy.gui.formula_image import formula_image
    from resize_energy.tutor.why_html import explanation_html

    for key in results.topic_order:
        html = explanation_html(key, None, math=True)
        names = re.findall(r'src="(chart:fx_[0-9a-f]+)"', html)
        if not names:
            return False
        for name in names:
            image = formula_image(name)
            if image is None or image.isNull() or image.width() < 10:
                return False
    return True


def _country_check(window, app) -> int:
    """Pick Italy on the PV cost page: prices and emissions follow, flagged as a preset."""
    from resize_energy.core.countries import get_country
    from resize_energy.gui import country

    country.forget_choice()
    window._start("pv")
    costs = window.pv_costs
    index = costs.country.findData("IT")
    costs.country.setCurrentIndex(index)
    costs.country_bar._picked(index)
    italy = get_country("IT")
    ok = (abs(costs.retail.value() - italy.electricity_eur_kwh) < 1e-6
          and abs(costs.ef.value() - italy.grid_kg_co2_kwh) < 1e-6
          and "Italy" in costs.retail.provenance())
    # coordinates of Turin agree with Italy; those of Sydney do not
    ok = ok and costs.country_bar.check_site() == ""
    window.site.lat.set_value(-33.9)
    window.site.lon.set_value(151.2)
    ok = ok and "Australia" in costs.country_bar.check_site() and costs.country_bar.warning.isVisibleTo(costs)
    window.site.lat.set_value(45.07)
    window.site.lon.set_value(7.69)
    # the choice follows to the battery page, which was still on its own defaults
    window._start("battery")
    battery = window.bat_costs
    battery.initializePage()
    ok = ok and abs(battery.retail.value() - italy.electricity_eur_kwh) < 1e-6
    country.forget_choice()
    window._restart()
    if not ok:
        print("self-test: the country preset did not fill the costs", flush=True)
        return 1
    return 0


def _step_art_check(window, app) -> int:
    """The input steps show their small illustration; the home page shows none."""
    window._start("pv")
    shown = window.header_art.key
    window._next()
    second = window.header_art.key
    window._restart()
    if shown != "sun_path" or second != "load_profile":
        print(f"self-test: step illustrations wrong ({shown}, {second})", flush=True)
        return 1
    return 0


def _project_roundtrip(window, app) -> int:
    """Save a hydrogen project, change a value, reopen the file and find the saved value."""
    import tempfile
    from pathlib import Path

    window._start("hydrogen")
    window.h2_goal.demand.set_value(54321)
    window.h2_plant.days.set_value(7)
    window.h2_goal.wind.setChecked(True)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "test.resize"
        window.save_to(path)
        window._restart()
        window._start("hydrogen")
        window.h2_goal.demand.set_value(1000)
        window.h2_goal.wind.setChecked(False)
        problems = window.open_from(path)
        app.processEvents()
        ok = (window.h2_goal.demand.value() == 54321 and window.h2_plant.days.value() == 7
              and window.h2_goal.wind.isChecked()
              and window.index == len(window.pages) - 1 and not problems)
    if not ok:
        print(f"self-test: reopening a saved project failed ({problems})", flush=True)
        return 1
    window._restart()
    return 0


def _settle(app, seconds: float = 0.6) -> None:
    """Let fades and pending deletions finish, so that a picture shows the page at rest."""
    import time

    from PySide6.QtCore import QEvent

    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        time.sleep(0.02)


def _screenshots(window, app, folder: str) -> None:
    """Save a picture of the home page and of the first and last step of every flow, and of
    the 'Why?' panel with a formula."""
    from pathlib import Path

    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    window.resize(1240, 820)
    _settle(app)
    window.grab().save(str(out / "home.png"))
    window.home.hero.set_height(330)
    _settle(app, 0.3)
    window.grab().save(str(out / "home_half.png"))
    window.home.hero.set_height(440)
    _settle(app, 0.3)
    window.grab().save(str(out / "home_open.png"))
    window.home.hero.set_height(210)
    _settle(app, 0.3)
    zone = window.home.zone
    for key in ("pv", "hydrogen", "biomass"):
        zone.add(key)
    _settle(app, 0.5)  # let the icons drift for a moment
    window.grab().save(str(out / "home_compare.png"))
    zone.clear()
    for tech in ("pv", "wind", "biomass", "hydrogen", "battery", "solar", "compare"):
        window._start(tech)
        _settle(app)
        window.grab().save(str(out / f"{tech}_start.png"))
        for _ in range(len(window.pages) - 2):
            window._next()
            _settle(app, 0.4)
            if window.index == 3:
                window.grab().save(str(out / f"{tech}_middle.png"))
        _settle(app, 1.0)
        window.grab().save(str(out / f"{tech}_results.png"))
        topics = getattr(window.pages[-1], "topics", None)
        if topics is not None and topics.count() > 2:
            topics.setCurrentRow(2)                  # a topic with a formula, in the Why? panel
            _settle(app, 0.5)
            window.grab().save(str(out / f"{tech}_why.png"))
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
