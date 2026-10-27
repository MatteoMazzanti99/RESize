"""Colour themes (light and graphite dark), style sheet and contrast helpers.

Everything except :func:`apply_theme` is plain Python (no Qt), so it is unit-tested.
"""

from __future__ import annotations

LIGHT: dict[str, str] = {
    "bg": "#F4F7FA",          # window background (cool light grey)
    "sidebar": "#FFFFFF",     # left navigation
    "surface": "#FFFFFF",     # panels, text areas
    "surface2": "#EAF0F6",    # raised elements, hover
    "border": "#C3CCD9",
    "text": "#0F1B2D",
    "muted": "#556377",
    "accent": "#0A7452",      # green, readable as text on white
    "accent_hover": "#085F43",
    "accent_text": "#FFFFFF", # text on top of the accent colour
    "accent_tint": "#E6F5EE", # card background for the active technology
    "warning": "#8F5600",
    "error": "#B3261E",
    "info": "#1F5FBF",
    "heat": "#B45309",        # heat tags (orange)
    "heat_bg": "#FDF0E1",
}

DARK: dict[str, str] = {
    "bg": "#141516", "sidebar": "#1A1B1D", "surface": "#1E2023", "surface2": "#2A2C30",
    "border": "#44474E", "text": "#ECEDEF", "muted": "#A0A3AB", "accent": "#34D399",
    "accent_hover": "#6EE7B7", "accent_text": "#04140E", "accent_tint": "#17332A",
    "warning": "#F5B941", "error": "#FF8A80", "info": "#6CB4FF",
    "heat": "#FDBA74", "heat_bg": "#3A2616",
}
THEMES: dict[str, dict[str, str]] = {"light": LIGHT, "dark": DARK}
THEME_LABELS = {"light": "Light", "dark": "Dark (graphite)"}

# The palette in use. The keys never change, so modules can keep the reference; the values
# are those of the theme chosen at start-up (see :func:`use_theme`).
COLORS: dict[str, str] = dict(LIGHT)
current_theme = "light"


def use_theme(name: str) -> str:
    """Make ``name`` the palette in use (unknown names fall back to light). Returns the name."""
    global current_theme
    name = name if name in THEMES else "light"
    COLORS.clear()
    COLORS.update(THEMES[name])
    current_theme = name
    from resize_energy.report.html_report import set_screen_palette

    set_screen_palette(COLORS, dark=name == "dark")
    return name


def screen_doc_css() -> str:
    """Style for the HTML shown inside text browsers, in the palette in use."""
    return (
        f"body {{ color: {COLORS['text']}; }} "
        f"h3 {{ color: {COLORS['accent']}; }} "
        f"code {{ background-color: {COLORS['surface2']}; color: {COLORS['accent_hover']}; }} "
        f"a {{ color: {COLORS['info']}; }}"
    )


FONT_FAMILY = '"Poppins", "Segoe UI", "Inter", "SF Pro Text", "Helvetica Neue", Arial, sans-serif'

SCREEN_DOC_CSS = screen_doc_css()   # of the light palette; use screen_doc_css() after use_theme


def _linear(channel: int) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    """WCAG relative luminance of '#RRGGBB'."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG contrast ratio between two '#RRGGBB' colours (1 to 21)."""
    a, b = luminance(foreground), luminance(background)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


_QSS = """
* { font-family: __FONT__; }
QWidget { background-color: {bg}; color: {text}; font-size: 10pt; }
QMainWindow, QDialog { background-color: {bg}; }
QLabel { background: transparent; }
QToolTip { background-color: {surface2}; color: {text}; border: 1px solid {border}; padding: 4px; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }

QWidget#sidebar { background-color: {sidebar}; border-right: 1px solid {surface2}; }
QWidget#sidebar QLabel { background: transparent; }
QLabel#brandName { font-size: 17pt; font-weight: 700; }
QLabel#brandTagline { color: {muted}; font-size: 9pt; }
QLabel#sidebarNote { color: {muted}; font-size: 8.5pt; }

QLabel#pageTitle { font-size: 20pt; font-weight: 700; }
QLabel#pageSubtitle { color: {muted}; font-size: 10.5pt; }
QLabel#overline { color: {accent}; font-size: 9pt; font-weight: 700; }
QLabel#headline { font-size: 26pt; font-weight: 700; }
QLabel#lead { color: {muted}; font-size: 11.5pt; }
QLabel#hint { color: {muted}; }
QLabel#sectionTitle { font-size: 12pt; font-weight: 700; }

QFrame#card { background-color: {surface}; border: 1px solid {surface2}; border-radius: 16px; }
QFrame#card:hover { border: 1px solid {border}; }
QFrame#cardActive { background-color: {surface}; border: 1px solid {border}; border-radius: 16px; }
QFrame#cardActive:hover { background-color: {accent_tint}; border: 1px solid {accent}; }
QFrame#dropZone { background-color: {surface}; border: 2px dashed {border}; border-radius: 18px; }
QFrame#dropZone[dragOver="true"] { background-color: {accent_tint}; border: 2px dashed {accent}; }
QFrame#cardDim { background-color: {bg}; border: 1px dashed {border}; border-radius: 16px; }
QFrame#cardDim QLabel#cardTitle { color: {text}; }
QLabel#cardTitle { font-size: 12pt; font-weight: 700; }
QLabel#cardText { color: {muted}; }
QLabel#cardIcon { background-color: {accent_tint}; color: {accent}; border-radius: 12px; font-size: 13pt; font-weight: 700; }
QLabel#pillOn { background-color: {accent_tint}; color: {accent}; border-radius: 10px; padding: 2px 10px; font-size: 8.5pt; font-weight: 700; }
QLabel#pillOff { background-color: {surface2}; color: {muted}; border-radius: 10px; padding: 2px 10px; font-size: 8.5pt; }

QPushButton { background-color: {surface}; color: {text}; border: 1px solid {border}; border-radius: 18px; padding: 8px 20px; font-weight: 500; }
QPushButton:hover { border-color: {accent}; }
QPushButton:pressed { background-color: {surface2}; }
QPushButton:disabled { color: {muted}; border-color: {surface2}; }
QPushButton[variant="primary"] { background-color: {accent}; color: {accent_text}; border: 1px solid {accent}; font-weight: 700; padding: 9px 26px; }
QPushButton[variant="primary"]:hover { background-color: {accent_hover}; border-color: {accent_hover}; }
QPushButton[variant="primary"]:disabled { background-color: {surface2}; color: {muted}; border-color: {surface2}; }
QPushButton[variant="ghost"] { background-color: transparent; border: 1px solid {border}; }
QWidget#segmented { background-color: {surface2}; border: 1px solid {border}; border-radius: 18px; }
QPushButton[variant="segment"] { background-color: transparent; border: none; border-radius: 15px; padding: 6px 16px; color: {muted}; font-weight: 600; }
QPushButton[variant="segment"]:hover:!checked:enabled { color: {text}; background-color: transparent; border: none; }
QPushButton[variant="segment"]:checked { background-color: {accent}; color: {accent_text}; }
QPushButton[variant="segment"]:disabled { color: {border}; background-color: transparent; border: none; }
QLabel#pillElec { background-color: {surface2}; color: {info}; border-radius: 10px; padding: 2px 10px; font-size: 8.5pt; font-weight: 700; }
QLabel#pillHeat { background-color: {heat_bg}; color: {heat}; border-radius: 10px; padding: 2px 10px; font-size: 8.5pt; font-weight: 700; }
QLabel#pillTag { background-color: {surface2}; color: {muted}; border-radius: 10px; padding: 2px 10px; font-size: 8.5pt; font-weight: 700; }
QFrame#livePanel { background-color: {surface}; border: 1px solid {border}; border-radius: 14px; }
QFrame#kpiTile { background-color: {surface}; border: 1px solid {border}; border-radius: 14px; }
QLabel#kpiLabel { color: {muted}; font-size: 8.5pt; }
QLabel#kpiValue { color: {text}; font-size: 19pt; font-weight: 700; }
QLabel#kpiUnit { color: {accent}; font-size: 8.5pt; font-weight: 600; }
QPushButton#whyButton { border-radius: 12px; padding: 0px; min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px; color: {accent}; font-weight: 700; }

QLineEdit, QComboBox { background-color: {surface}; color: {text}; border: 1px solid {border}; border-radius: 10px; padding: 5px 8px; selection-background-color: {accent}; selection-color: {accent_text}; }
QLineEdit:focus, QComboBox:focus { border: 1px solid {accent}; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background-color: {surface}; color: {text}; border: 1px solid {border}; selection-background-color: {surface2}; selection-color: {text}; }
QCheckBox { background: transparent; spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid {muted}; border-radius: 5px; background-color: {surface}; }
QCheckBox::indicator:hover { border-color: {accent}; }
QCheckBox::indicator:checked { background-color: {accent}; border-color: {accent}; __CHECK__ }

QGroupBox { background: transparent; border: 1px solid {border}; border-radius: 14px; margin-top: 14px; padding: 14px 10px 8px 10px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 14px; padding: 0 6px; color: {muted}; font-weight: 700; }

QTextBrowser { background-color: {surface}; color: {text}; border: 1px solid {surface2}; border-radius: 14px; padding: 8px; selection-background-color: {accent}; selection-color: {accent_text}; }
QListWidget { background-color: {surface}; border: 1px solid {surface2}; border-radius: 14px; padding: 4px; outline: none; }
QListWidget::item { padding: 6px 8px; border-radius: 6px; }
QListWidget::item:hover { background-color: {surface2}; }
QListWidget::item:selected { background-color: {accent_tint}; color: {accent}; }

QSplitter::handle { background-color: {bg}; width: 8px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: {border}; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: {muted}; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: {border}; border-radius: 4px; min-width: 28px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

QMessageBox { background-color: {bg}; }
"""


CHECK_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18">'
             '<path d="M4.5 9.5 L7.5 12.5 L13.5 5.5" fill="none" stroke="#FFFFFF" stroke-width="2.4" '
             'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def _check_icon_file() -> str | None:
    """Write the tick image once and return its path (QSS needs a file), or None."""
    import tempfile
    from pathlib import Path

    try:
        path = Path(tempfile.gettempdir()) / "resize_energy_check.svg"
        path.write_text(CHECK_SVG, encoding="utf-8")
        return path.as_posix()
    except OSError:
        return None


def build_stylesheet(check_icon: str | None = None) -> str:
    """The application style sheet with every colour placeholder filled in."""
    qss = _QSS.replace("__FONT__", FONT_FAMILY)
    qss = qss.replace("__CHECK__", f'image: url("{check_icon}");' if check_icon else "")
    for name, value in COLORS.items():
        qss = qss.replace("{" + name + "}", value)
    return qss


def load_fonts() -> int:
    """Register the Poppins files shipped with the app; returns how many were loaded."""
    from importlib.resources import files

    from PySide6.QtGui import QFontDatabase

    loaded = 0
    for entry in files("resize_energy").joinpath("data", "fonts").iterdir():
        if entry.name.endswith(".ttf") and QFontDatabase.addApplicationFont(str(entry)) >= 0:
            loaded += 1
    return loaded


def apply_theme(app, name: str | None = None) -> None:
    """Use the Fusion style, the palette (for native dialogs), Poppins and the style sheet.

    ``name`` ("light" or "dark") is also remembered by the caller; left out, the saved choice
    is used."""
    use_theme(name or saved_theme())
    from PySide6.QtGui import QColor, QPalette

    load_fonts()

    app.setStyle("Fusion")
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: COLORS["bg"],
        QPalette.ColorRole.WindowText: COLORS["text"],
        QPalette.ColorRole.Base: COLORS["surface"],
        QPalette.ColorRole.AlternateBase: COLORS["surface2"],
        QPalette.ColorRole.Text: COLORS["text"],
        QPalette.ColorRole.Button: COLORS["surface2"],
        QPalette.ColorRole.ButtonText: COLORS["text"],
        QPalette.ColorRole.Highlight: COLORS["accent"],
        QPalette.ColorRole.HighlightedText: COLORS["accent_text"],
        QPalette.ColorRole.ToolTipBase: COLORS["surface2"],
        QPalette.ColorRole.ToolTipText: COLORS["text"],
        QPalette.ColorRole.PlaceholderText: COLORS["muted"],
        QPalette.ColorRole.Link: COLORS["info"],
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(build_stylesheet(_check_icon_file()))


def saved_theme() -> str:
    """The theme chosen last time ("light" when none or when settings cannot be read)."""
    try:
        from PySide6.QtCore import QSettings

        value = QSettings("RESize", "RESize").value("theme", "light")
        return value if value in THEMES else "light"
    except Exception:  # noqa: BLE001 - a settings problem must never stop the app
        return "light"


def save_theme(name: str) -> None:
    """Remember the theme for the next start."""
    try:
        from PySide6.QtCore import QSettings

        QSettings("RESize", "RESize").setValue("theme", name if name in THEMES else "light")
    except Exception:  # noqa: BLE001
        pass
