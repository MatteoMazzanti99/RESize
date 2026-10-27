# Technology comparison

Put two or more technologies side by side for the same job.

| First step | Results |
|---|---|
| ![](../screenshots/compare_start.png) | ![](../screenshots/compare_results.png) |

## How to start

On the home screen **drag two or more technology cards into the Compare zone** (PV, wind,
biomass, green hydrogen, hydropower, geothermal, solar thermal, ground-source heat pump) and
press **Compare**. After a short clash you land on a **Versus**
screen where the bars of each round (cost of energy, payback, net present value, CO2) fill up
like life bars; the full report is in the second tab.

## Electricity, heat or both

Next to the Compare button a drop-down lets you choose **what** to compare, and it only offers
what the technologies you dropped make possible: a kind of energy needs at least two
technologies that deliver it.

| Kind | Technologies | Reference |
|---|---|---|
| Electricity | PV, wind, biomass (biogas CHP), hydrogen, hydropower, geothermal (power plant) | the grid (hydrogen: natural-gas hydrogen) |
| Heat | biomass (boiler), geothermal (doublet and heat network), solar thermal, ground-source heat pump | heat from a gas boiler |

Biomass and geothermal make both, so with them in the zone you can also choose **electricity
and heat**: the steps then ask for both demands and the results page has a selector to switch
between the two comparisons. Hydropower and wind, for example, can only be compared on
electricity; solar thermal and the heat pump only on heat.

In a heat comparison every plant is sized for the same yearly heat, peak load and share to
cover. Running costs include the wood of the boiler and the electricity of the pumps and of the
heat pump (retail price, grid emission factor). The solar field is sized on a flat, hot-water
type load, and a heating-only borehole field cools the ground: when it is too large for the
ground it is left out of the comparison, with a note saying why.

## The steps

1. **Site and demand.** One site and one yearly demand: every technology is sized for the same
   energy.
2. **Plant assumptions.** Only the chosen technologies are asked here.
3. **Costs and prices.**
4. **Comparison.**

## What you get

Cost of energy (LCOE), simple and discounted payback, net present value and avoided CO2, with
*Why?* panels for every formula and a PDF report. Electricity technologies are compared with
the grid; hydrogen is compared, on its heating value, with hydrogen made from natural gas.
Sensitivity pictures tell you whether the ranking survives when the capital costs or the
discount rate move.

## Assumptions to remember

Prices, lifetimes and emission factors are round placeholders. The model is an annual balance
(no hourly match for the electricity, no incentives or taxes), biogas heat is not credited and
the hydrogen plant runs on an invented hourly year (use the [hydrogen](hydrogen.md) flow for
real hourly data).
