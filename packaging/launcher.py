"""Entry script used by PyInstaller (kept outside the package so imports stay absolute)."""

import sys

from resize_energy.gui.app import main

if __name__ == "__main__":
    sys.exit(main())
