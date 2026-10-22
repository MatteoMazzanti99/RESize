# RESize

**A step-by-step tutor for sizing renewable energy systems.**

RESize guides MSc students (and engineers doing a first-pass design) through the sizing of
renewable energy plants. At every step it shows the formula, the assumptions and the
reasoning, so you learn *why* a choice is made, not just the number that comes out.

> **Status:** pre-alpha (v0.1 in development). Interfaces and results may change.

## Quick start

```bash
pip install -e ".[gui]"
resize            # opens the PV sizing wizard
resize-cli pv-power --demand-kwh 4800 --irradiation 1600 --pr 0.75
```

The wizard guides you through site and solar resource (PVGIS or manual input), demand,
module/inverter datasheet values, then shows the design, automatic checks and a PDF report.
Next to the main values a round **?** button explains the step, and on the results page a
**Why?** panel shows each formula with *your own numbers* substituted in. The same worked
examples are included in the PDF report.

## Roadmap

| Version | Content |
|---|---|
| v0.1 | Guided photovoltaic wizard (resource data, strings, inverter, losses, yield) + PDF report |
| v0.2 | "Why?" panels (done), rule-based design checker (done), Italian interface, optional AI tutor |
| v0.3 | Wind module + technology comparison (LCOE, payback, avoided CO2) |
| v0.4 | Green hydrogen: PEM electrolyser coupled to PV/wind |

## Design principles

- **Works without AI.** Explanations and the design checker are deterministic and offline.
- **AI is optional.** Bring your own API key (stored in the OS keyring) or a local model; or
  copy the project summary into any chatbot.
- **Core is a library.** `resize_energy.core` has no GUI dependency: use it from scripts and notebooks.
- **Validated.** Results are benchmarked against PVGIS / SAM; benchmarks live in `docs/validation/`.

## Repository layout

```
src/resize_energy/
  core/     calculation library (no GUI)
  gui/      desktop interface (PySide6)
  tutor/    explanations, design checker, optional AI backends
  report/   PDF/DOCX export
tests/
docs/
.github/workflows/   CI and release builds (installers for Windows, macOS, Linux)
```

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,gui,pv]"
pytest
```

## Disclaimer

RESize is a tool for **preliminary and educational sizing**. It is not a substitute for
detailed engineering design, and results must not be used for executive projects without
independent verification. See [DISCLAIMER.md](DISCLAIMER.md).

## License

MIT, see [LICENSE](LICENSE).
