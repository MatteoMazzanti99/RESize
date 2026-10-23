# Green hydrogen

An electrolyser fed by PV, wind and/or the grid, simulated hour by hour for a year.

| First step | A middle step | Results |
|---|---|---|
| ![](../screenshots/hydrogen_start.png) | ![](../screenshots/hydrogen_middle.png) | ![](../screenshots/hydrogen_results.png) |

## Two ways in

- **From a hydrogen demand.** The electrolyser and the renewable plants are sized for it.
- **From a plant you already have.** How much hydrogen it can make.

## The steps

1. **Goal and sources.** The demand or the plant, and which sources to use (PV, wind, grid, or
   any combination).
2. **Site and profiles.** A button downloads one real year of hourly wind and radiation from
   NASA POWER. Offline, an invented year with the same yearly totals is used and the report
   says so.
3. **Electrolyser and storage.** Efficiency, minimum load, compression and storage, water.
   Optional deeper models: efficiency that depends on the load, stack ageing with replacement,
   a tank sized hour by hour, and grid purchases in the cheapest hours of a price profile.
4. **Costs and emissions.**
5. **Results and checks.**

## What you get

Hydrogen per year, full-load hours, curtailment, compression work, storage volume, water, stack
life, the **cost of hydrogen (LCOH)** with its breakdown and the **carbon intensity** against
the EU renewable-hydrogen threshold (about 3.4 kg CO2/kg) and against hydrogen from natural
gas. Two sensitivity pictures show which input moves the cost most.

## Assumptions to remember

Costs and emission factors are round placeholders. The electrolyser runs renewables first, off below its
minimum load, with an optional grid top-up limited to a number of full-load hours. See the [cross-checks](../validation/README.md): the LCOH of a grid-only plant
is recomputed by hand.
