# RESize

**A step-by-step tutor for sizing renewable energy systems.**

RESize guides MSc students (and engineers doing a first-pass design) through the sizing of
renewable energy plants. At every step it shows the formula, the assumptions and the
reasoning, so you learn *why* a choice is made, not just the number that comes out.

> **Status:** early release. Photovoltaic, wind, biomass and green hydrogen are available. Interfaces and results may change.

![RESize home screen](docs/images/home.png)

## Download

Get the installer for your system from the
[Releases page](https://github.com/MatteoMazzanti99/RESize/releases):

| System | File | Notes |
|---|---|---|
| Windows | `RESize-windows.zip` | Unzip, run `RESize.exe`. Windows may warn about an unknown publisher (the app is not code-signed): *More info > Run anyway*. |
| macOS | `RESize-macos.zip` | Unzip, right-click `RESize.app` > *Open* the first time (not notarized). |
| Linux | `RESize-linux.tar.gz` | Extract, run `RESize/RESize`. Needs the usual Qt libraries (e.g. `libxkbcommon-x11-0`, `libxcb-cursor0`). |

Prefer Python? See *Quick start* below.

## How it looks

| 1. Site and solar resource | 2. Electricity demand |
|---|---|
| ![Site step](docs/images/step1-site.png) | ![Demand step](docs/images/step2-demand.png) |
| **3. Module and inverter** | **4. Results, checks and Why?** |
| ![Components step](docs/images/step3-components.png) | ![Results step](docs/images/step4-results.png) |

Validation against PVGIS, independent integrations and hand calculations:
[docs/validation](docs/validation/README.md).

## Wind module

Start it from the home screen (**Start a wind project**). Steps: site and wind resource
(NASA POWER or your own data, Weibull distribution, shear, air density), demand and losses,
turbine and layout, results. You get the capacity factor, the energy of one turbine, the number
of turbines to cover the demand, land use, design checks, **Why?** panels with your numbers and
a PDF report, like the photovoltaic flow.

The turbine step offers a **library of 55 real turbines** (onshore utility scale and small
distributed machines) with tabulated power curves, taken from the open
[NREL turbine-models](https://github.com/NREL/turbine-models) repository (BSD-3-Clause, see
`THIRD_PARTY_NOTICES.md`). Many of those curves are reference or theoretical designs, not
manufacturer-certified data: for a real project use the manufacturer's curve and a measured
wind resource. Editing a value switches back to the generic curve.


## Biomass module

Start it from the home screen (**Start a biomass project**) and pick the pathway:

- **Solid biomass boiler** (heat only) and **ORC cogeneration** (heat and power), sized on the
  heat demand with a load duration curve: plant power for the share of heat you want to cover,
  fuel per year from moisture and heating value, silo size, truck loads and ash.
- **Biogas**: digester and CHP engine sized on the electricity demand, with substrate mix,
  methane yield, digester volume and retention time, organic loading rate, heat balance
  (after heating the digester), crop land and digestate.

Every step has **Why?** panels with your numbers, design checks and a PDF report. Fuel and
substrate values are typical handbook figures: replace them with your supplier's specification
or a laboratory methane potential test.

## Green hydrogen module

Start it from the home screen (**Start a green hydrogen project**). Two ways in: from a
**hydrogen demand** (electrolyser and renewable plants are sized for it) or from a
**renewable plant you already have** (how much hydrogen it can make). The electricity can come
from PV, wind, the grid or any combination.

The calculation runs hour by hour over a year: renewables first, electrolyser off below its
minimum load, optional grid top-up limited to a number of full-load hours. You get the
hydrogen per year, full-load hours, curtailment, compression work, storage volume, water, stack
life, the **cost of hydrogen (LCOH)** with its breakdown and the **carbon intensity** compared
with the EU renewable-hydrogen threshold (about 3.4 kg CO2/kg) and with hydrogen from natural
gas. A button downloads one real year of hourly wind and radiation from NASA POWER; offline an
invented year with the same yearly totals is used and the report says so. Costs and emission
factors are round placeholders to replace with quotes.

## Technology comparison

The **Compare technologies** button on the home screen sizes a photovoltaic and a wind plant
for the same site and demand and puts them side by side: cost of energy (LCOE), simple and
discounted payback, net present value and avoided CO2, with **Why?** panels for every
formula and a PDF report. Prices, lifetimes and emission factors are round placeholders to
replace with local quotes; the model is an annual balance (no hourly match, no storage,
no incentives or taxes).

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

## AI tutor (optional)

On the results page, **Ask the AI tutor...** opens a chat that knows your inputs, results and
design checks. It teaches rather than just answering: it explains the reasoning and may ask a
question to check your understanding. Three ways to use it, none required:

| Option | What you need |
|---|---|
| Anthropic (Claude) | your own API key from console.anthropic.com |
| OpenAI-compatible service | your own key, the service address and a model name |
| Ollama (local model) | [Ollama](https://ollama.com) running on your computer; no key, nothing leaves your PC |
| Any chatbot | the **Copy project for any chatbot** button, then paste the summary where you like |

Open **Settings...** in the tutor window to choose. The key is never written to a file: it can
be remembered in your system keyring (`pip install "resize-energy[ai]"`), read from the
`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` environment variable, or kept only for the session. Your
project values are sent to the provider you choose; each question typically costs a few cents
or less. AI answers can be wrong: the formulas in the **Why?** panel are the reference.

## Roadmap

| Version | Content |
|---|---|
| v0.1 | Guided photovoltaic wizard (resource data, strings, inverter, losses, yield) + PDF report |
| v0.2 | "Why?" panels (done), rule-based design checker (done), optional AI tutor (done), Italian interface |
| v0.3 | Wind module (done: resource, Weibull, turbine yield, layout, checks, report) + technology comparison (done: LCOE, payback, NPV, avoided CO2) |
| v0.4 | Biomass module (done: boiler, ORC cogeneration, biogas) + green hydrogen (done: PEM electrolyser fed by PV, wind and/or grid, hourly dispatch, LCOH, carbon) |

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
