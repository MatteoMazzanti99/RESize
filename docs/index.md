# RESize

**A step-by-step tutor for sizing renewable energy systems.**

RESize guides MSc students and engineers doing a first-pass design through the sizing of
renewable plants. At every step it shows the formula, the assumptions and the reasoning, with
*your own numbers* plugged in, so you learn why a choice is made and not only the number that
comes out.

![Home screen](screenshots/home.png)

## What you can size

| Technology | You give | You get |
|---|---|---|
| [Photovoltaic](guide/pv.md) | demand, site, module and inverter | strings, inverter match, yearly yield, cost and payback |
| [Wind](guide/wind.md) | wind resource, turbine, layout | capacity factor, number of turbines, wake losses, cost |
| [Biomass](guide/biomass.md) | heat or electricity demand, fuel | boiler, ORC or biogas plant, fuel supply, digester |
| [Green hydrogen](guide/hydrogen.md) | hydrogen demand or a plant you own | electrolyser, hours, storage, cost and carbon of hydrogen |
| [Battery storage](guide/battery.md) | PV and/or wind plant, load | self-sufficiency, cycles, payback, best size |
| [Solar thermal](guide/solar-thermal.md) | hot water and/or cooling demand | collectors, tank, adsorption chiller, solar fraction |
| [Comparison](guide/compare.md) | the same yearly energy | cost of energy, payback, NPV and CO2 side by side |

## Start here

1. [Install](install.md) the app (a download for Windows, macOS and Linux).
2. Read [how to read the results](guide/concepts.md): the *Why?* panels, the design checks, the
   report, saving projects and the optional AI tutor.
3. Open the guide of the technology you need.

!!! warning "Preliminary design only"
    RESize is a teaching tool and a first-pass sizing aid. It is not a substitute for detailed
    engineering design, site measurements or a bankable energy yield study. See the
    [disclaimer](https://github.com/MatteoMazzanti99/RESize/blob/main/DISCLAIMER.md) and the
    [validation](validation/README.md) page to know how far to trust each number.
