# Validation

Benchmarks of RESize results, one file per module, with inputs, reference outputs and deviations.

- [PV sizing](pv.md): electrical limits vs independent hand calculation, yearly energy vs PVGIS
  for six European sites. Regenerate with `python validation/validate_pv.py`
  (also runs on GitHub: *PV validation* workflow).

- [Wind sizing](wind.md): formulas by hand, yearly energy against an independent integration,
  NASA POWER sanity check. Regenerate with `python validation/validate_wind.py`.

- Cross-checks of all technologies: `python validation/validate_cross.py` (runs on GitHub in the
  *PV validation* workflow, with pvlib and PyWake installed; the report is attached to the run
  as `cross-report.md`). Last results:
  - **Wind wakes**: two aligned turbines match an independent closed-form Jensen to rounding;
    against PyWake's NOJ model the wake loss differs by 0.05 to 1.5 percentage points on four
    layouts (e.g. 12 turbines 5D x 7D: 5.4 % PyWake, 5.2 % RESize).
  - **PV**: sun position within 0.9 degrees of pvlib; monthly shape of the invented year within
    1-2 percentage points (RMS) of the PVGIS typical year; battery self-sufficiency on the
    invented year within about 1 point of the real year at Torino, Palermo and Berlin.
  - **Biogas** substrate yields are below the Buswell limits; **hydrogen** and **battery**
    recomputed by hand or by a second implementation agree to rounding.
  - Not done: measured plants, commercial tools (WAsP, WindPRO, PVsyst, HOMER).

Planned: comparison with NREL SAM and with measured plant data.
