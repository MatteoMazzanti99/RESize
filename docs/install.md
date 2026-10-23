# Install

## Download (recommended)

Get the installer for your system from the
[Releases page](https://github.com/MatteoMazzanti99/RESize/releases).

| System | File | First start |
|---|---|---|
| Windows | `RESize-windows.zip` | Unzip and run `RESize.exe`. Windows may warn about an unknown publisher (the app is not code-signed): *More info*, then *Run anyway*. |
| macOS | `RESize-macos.zip` | Unzip, right-click `RESize.app`, choose *Open* the first time (not notarized). |
| Linux | `RESize-linux.tar.gz` | Extract and run `RESize/RESize`. It needs the usual Qt libraries (for example `libxkbcommon-x11-0` and `libxcb-cursor0`). |

Installers are built automatically by GitHub Actions each time a version tag is published.

## With Python

You need Python 3.10 or newer.

```bash
pip install -e ".[gui]"     # from a clone of the repository
resize                      # opens the desktop app
resize-cli pv-power --demand-kwh 4800 --irradiation 1600 --pr 0.75
```

The calculation library `resize_energy.core` has no GUI dependency: you can use it from
scripts and notebooks.

## Internet access

RESize works offline with values you type. Some buttons use public data when you press them:
**PVGIS** (solar irradiation), **NASA POWER** (wind speed and hourly weather). If you are
offline the app says so and you can type the value instead.
