# Wind

Sizes a wind plant from the wind resource: the speed at hub height, the energy of one turbine,
the number of turbines for your demand, the layout with wake losses, and the economics.

| First step | A middle step | Results |
|---|---|---|
| ![](../screenshots/wind_start.png) | ![](../screenshots/wind_middle.png) | ![](../screenshots/wind_results.png) |

## The five steps

1. **Site and wind resource.** *Get mean wind speed from NASA POWER* (a smooth long-term value
   at 50 m) or type a mast or atlas value, with the Weibull shape `k`, the shear exponent and
   the air density inputs (elevation, temperature).
2. **Demand and losses.** Yearly demand, the share to cover, availability and other losses.
3. **Turbine and layout.** Choose a turbine from the **library of 55 real machines** with
   tabulated power curves (from the open NREL turbine-models repository) or type the datasheet
   values. Spacing across and along the wind, and an optional **wake model**: Jensen wakes over
   a wind rose for a grid of staggered rows.
4. **Costs and savings.** Installed cost per kW, maintenance, prices, discount rate, emissions.
5. **Results and checks.**

## What you get

Mean speed at hub height, Weibull scale, air density, capacity factor, energy per turbine,
number of turbines, land use, and with the wake model the wake loss, the efficiency of every
turbine and of every wind direction. Then cost of energy, payback, NPV, CO2 and sensitivity.

## Assumptions to remember

Many curves of the library are reference or theoretical designs, not manufacturer-certified
data: for a real project use the manufacturer's curve and a measured resource. When the wake
model is on, "other losses" should no longer include wakes (3-6 % is more usual). The
economics use the yearly energy and the same simple annuity model as the other modules.

Validation: formulas by hand, an independent integration of the power curve and a PyWake
comparison of the wake model, see [Wind validation](../validation/wind.md) and
[all cross-checks](../validation/README.md).
