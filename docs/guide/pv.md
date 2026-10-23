# Photovoltaic

Sizes a grid-connected PV plant from your yearly demand: the array, the string layout against
the inverter limits, the yearly energy, and what it costs and saves.

| First step | A middle step | Results |
|---|---|---|
| ![](../screenshots/pv_start.png) | ![](../screenshots/pv_middle.png) | ![](../screenshots/pv_results.png) |

## The five steps

1. **Site and solar resource.** Latitude, longitude, tilt and azimuth. *Get irradiation from
   PVGIS* fills the yearly irradiation on the tilted plane (and an implied performance ratio);
   offline, type your own value.
2. **Electricity demand.** Yearly demand, the share the PV should cover and the performance
   ratio (PR) that groups all the losses (typically 0.75-0.85). An optional **shading** block
   takes the height and direction of a nearby obstacle and computes the share of the year's
   energy it takes.
3. **Module and inverter.** Datasheet values: the module's power, voltages, current and
   temperature coefficients; the inverter's maximum DC voltage, MPPT window and current.
4. **Costs and savings.** Installed cost per kWp, maintenance, lifetime, discount rate, the
   price you pay for electricity and the price paid for the surplus, and the emission factors.
5. **Results and checks.**

## What you get

- Target peak power, admissible modules per string (from the coldest-day open-circuit voltage
  and the hottest-day MPPT limit), chosen layout, DC/AC ratio, array area and yearly energy.
- Month-by-month production against your demand, and the effect of a battery of one day of
  consumption (the [battery](battery.md) module sizes it properly).
- Cost of energy, simple and discounted payback, net present value, CO2 avoided, a cash-flow
  curve and the sensitivity pictures.
- Design checks on string voltages, MPPT window, current limits, DC/AC ratio, shading and the
  winter gap.

## Assumptions to remember

The yearly energy is `power x irradiation x PR`: it does not simulate the hours. The share
used on site is `min(production, demand)` over the year, so the saving is optimistic where
production and consumption do not coincide; the battery view shows the hourly picture.
Prices are placeholders, there are no incentives or taxes.

Validation: yearly energy against PVGIS for six European sites, see
[PV validation](../validation/pv.md).
