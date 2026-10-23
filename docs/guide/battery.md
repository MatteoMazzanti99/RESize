# Battery storage

Stores the surplus of a PV and/or wind plant for the hours when the plant produces less than
you consume.

| First step | A middle step | Results |
|---|---|---|
| ![](../screenshots/battery_start.png) | ![](../screenshots/battery_middle.png) | ![](../screenshots/battery_results.png) |

## The steps

1. **Plant and load.** The PV and/or wind plant and the load profile (home, office, industry or
   flat).
2. **Site and profiles.** A real NASA POWER year of hourly data or an invented one.
3. **The battery.** Three starting points: a capacity you choose, the smallest battery for a
   target self-sufficiency, or the best net present value. Round-trip efficiency, depth of
   discharge, state of health, C-rate and life (cycles or calendar).
4. **Prices and costs.**
5. **Results and checks.**

## What you get

Self-sufficiency and self-consumption with and without the battery, imports and exports,
cycles per year, life, payback, NPV, cost of storage (LCOS), CO2, a summer and a winter week
hour by hour, and curves of self-sufficiency and NPV against the size that show why a bigger
battery is not always better.

## Assumptions to remember

With the default prices (about 550 euro/kWh, buying at 0.25 and selling at 0.08 euro/kWh) the
net present value is often negative: the gain of a battery is the margin between the price you
pay and the price you are paid for the surplus. The check says so. The load is a typical shape,
not your meter data. The hourly dispatch is recomputed by a second implementation in the
[cross-checks](../validation/README.md).
