# Solar thermal and adsorption cooling

Collectors and a storage tank for **hot water**, and optionally **cooling** with an adsorption
chiller driven by the heat of the collectors.

| First step | A middle step | Results |
|---|---|---|
| ![](../screenshots/solar_start.png) | ![](../screenshots/solar_middle.png) | ![](../screenshots/solar_results.png) |

## What is an adsorption chiller?

A chiller that makes chilled water from **hot water** instead of electricity. Inside, water
evaporates at low pressure and takes heat from the chilled-water circuit (the cooling); a solid
such as silica gel adsorbs the vapour. When the solid is saturated, 60-90 degC water from the
solar collectors dries it again, driving the vapour to a condenser cooled by a tower or dry
cooler; two beds alternate so the machine works continuously. The thermal COP is about
0.5-0.65 at best (1 kWh of cold for about 2 kWh of heat) and falls when the drive water is
cooler, until the machine stops at about 55-60 degC. It makes sense because the sun is
strongest exactly when the cooling is needed, and it keeps the collectors busy in summer, when
the hot-water demand is low.

## The steps

1. **What you need.** Litres of hot water per day and its temperature; cooling needed per year
   (0 if none). Either or both.
2. **Site and sun.** Irradiation on the collector plane (PVGIS or by hand), mean air
   temperature and summer-winter swing.
3. **Collectors and tank.** Flat plate, evacuated tube or unglazed, with the efficiency
   coefficients (`eta0`, `a1`, `a2`; take them from the Solar Keymark certificate); the area
   you choose, or the area that reaches a **target solar fraction**; tank litres per m2; and
   the chiller's COP, drive temperatures and size.
4. **Costs and prices.** Collectors, tank, chiller, fixed costs, the price of the heat you
   replace and of electricity.
5. **Results and checks.**

## What you get

The solar fraction (hot water, cooling and overall), heat dumped by overheating, the real
average COP of the chiller, a winter and a summer week of the tank temperature, the solar
fraction and the energy per m2 against the collector area, payback, NPV, cost of solar energy
(LCOH), CO2 avoided and the sensitivity of the NPV.

## How it is calculated

One year, hour by hour, with a synthetic but physical weather (clear-sky shape times random
cloudy days, scaled to your yearly irradiation) and one mixed tank: the collector adds heat
`eta x G x area`, the hot-water draw and the chiller take heat from the tank, the tank loses
heat to the room, and above 95 degC the excess is dumped. Hot water that finds the tank colder
than the set point is preheated and the backup boiler adds the rest. Cooling is a load that
follows the outside temperature during working hours.

## Assumptions to remember

No stratification, no detailed hydraulics, no frost or boiling model, heat rejection of the
chiller assumed adequate. Prices and coefficients are round typical values. Without incentives
hot water often has a payback of 10-20 years in central Europe, and solar cooling is rarely
competitive: the checks and the sensitivity say so for your numbers.

Validation: the hourly loop is recomputed by a second plain implementation (agreement to
rounding) and compared with the f-chart method, see [cross-checks](../validation/README.md).
