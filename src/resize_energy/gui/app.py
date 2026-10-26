"""Entry point of the RESize desktop application."""

from __future__ import annotations

import sys


def _walk_through(window, app) -> int:
    """Run every technology flow with its default values, up to the results page."""
    from resize_energy.core.turbine_library import load_library

    if len(load_library()) < 10:
        print("self-test: the turbine library is missing from the build", flush=True)
        return 1
    markers = {"pv": "Design checks", "wind": "Design checks", "biomass": "Design checks", "hydrogen": "Design checks", "battery": "Design checks", "solar": "Design checks", "hydro": "Design checks", "geothermal": "Design checks", "compare": "Which is better"}
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
    for check in (_versions_check, _solar_cooling_check, _country_check, _step_art_check,
                  _wind_layout_check):
        code = check(window, app)
        if code:
            return code
    return _project_roundtrip(window, app)


def _demo_rose():
    from resize_energy.core.wind_rose import rose_from_series

    speeds = [5.0 + (i % 7) for i in range(8760)]
    dirs = [(250.0 + 55.0 * ((i * 37) % 100) / 100.0 - 20.0) % 360.0 for i in range(8760)]
    return rose_from_series(speeds, dirs, (2019,))


def _wind_layout_check(window, app) -> int:
    """Wind with a wind rose and turbines placed by the program in a site: map and rose drawn,
    and the rose survives saving and opening a project."""
    from resize_energy.gui import project_io

    window._start("wind")
    window.wind_site._rose = _demo_rose()
    window.wind_site._rose_changed()
    window.wind_turbine.layout_mode.setCurrentIndex(1)
    for _ in range(len(window.pages) - 2):
        window._next()
        app.processEvents()
    results = window.pages[-1]
    if "placed by the program" not in results.html or window.index != len(window.pages) - 1:
        print("self-test: the wind layout flow did not reach its results", flush=True)
        return 1
    for name in ("chart:wind_layout_map", "chart:wind_rose_polar"):
        image = results.chart_images.get(name)
        if image is None or image.isNull():
            print(f"self-test: the wind chart {name} was not drawn", flush=True)
            return 1
    state = project_io.capture(window.wind_site)
    window.wind_site._rose = None
    project_io.restore(window.wind_site, state)
    if window.wind_site.rose() is None:
        print("self-test: the wind rose was not restored from the project", flush=True)
        return 1
    if _satellite_render_failed():
        return 1
    window._restart()
    return 0


def _satellite_render_failed() -> bool:
    """A map with an aerial picture must show it through QtSvg (tiles are embedded JPEGs)."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    from resize_energy.core.satellite import Satellite, Tile
    from resize_energy.report.layout_art import layout_svg

    tile = QImage(256, 256, QImage.Format.Format_RGB32)
    tile.fill(QColor(30, 140, 40))
    raw = QByteArray()
    buf = QBuffer(raw)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    tile.save(buf, "JPEG")
    sat = Satellite((Tile(-2000.0, 2000.0, 4000.0, bytes(raw)),))
    svg = layout_svg("t", [(0.0, 0.0), (400.0, 100.0)], 100.0, [0.9, 0.95],
                     [(-500, -300), (500, -300), (500, 300), (-500, 300)], 270.0, 0.075,
                     satellite=sat)
    img = QImage(460, 390, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    painter = QPainter(img)
    renderer = QSvgRenderer(svg.encode())
    renderer.render(painter)
    painter.end()
    foot = img.pixelColor(300, 380)          # the legend strip must stay white
    if foot.green() < 240 or foot.red() < 240:
        print(f"self-test: the satellite picture spills over the legend (pixel {foot.name()})",
              flush=True)
        return True
    px = img.pixelColor(60, 60)
    if not (px.green() > px.red() + 40 and px.green() > px.blue() + 40):
        print(f"self-test: the satellite tile was not drawn by QtSvg (pixel {px.name()})",
              flush=True)
        return True
    return False


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
    window.home.hero.stop_opening()      # fixed sizes for the pictures
    window.home.hero.set_height(210)
    window.resize(1240, 820)
    _settle(app)
    window.grab().save(str(out / "home.png"))
    window.home.hero.set_height(330)
    _settle(app, 0.3)
    window.grab().save(str(out / "home_half.png"))
    window.home.hero.set_height(520)
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
    for tech in ("pv", "wind", "biomass", "hydrogen", "battery", "solar", "hydro", "geothermal", "compare"):
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
    # wind with a wind rose and the turbines placed by the program
    window._start("wind")
    window.wind_site._rose = _demo_rose()
    window.wind_site._rose_changed()
    window.wind_turbine.layout_mode.setCurrentIndex(1)
    for _ in range(len(window.pages) - 2):
        window._next()
        _settle(app, 0.4)
    _settle(app, 1.0)
    window.grab().save(str(out / "wind_layout_results.png"))
    browser = window.pages[-1].browser
    window.resize(1240, 1500)                      # tall enough to see a whole picture
    _settle(app, 0.5)
    for phrase, name in (("placed inside the site", "wind_layout_map"),
                         ("Petals point to where", "wind_layout_rose")):
        found = browser.document().find(phrase)
        if found.isNull():
            continue
        browser.setTextCursor(found)
        browser.ensureCursorVisible()
        bar = browser.verticalScrollBar()
        bar.setValue(max(0, bar.value() + 160))    # show the picture above its caption
        _settle(app, 0.4)
        window.grab().save(str(out / f"{name}.png"))
    window.resize(1240, 820)
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
