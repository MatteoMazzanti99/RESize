# Validation

Benchmarks of RESize results, one file per module, with inputs, reference outputs and deviations.

- [PV sizing](pv.md): electrical limits vs independent hand calculation, yearly energy vs PVGIS
  for six European sites. Regenerate with `python validation/validate_pv.py`
  (also runs on GitHub: *PV validation* workflow).

- [Wind sizing](wind.md): formulas by hand, yearly energy against an independent integration,
  NASA POWER sanity check. Regenerate with `python validation/validate_wind.py`.

Planned: comparison with NREL SAM and with measured plant data.
