# Hydropower (run-of-river)

A first sizing of a **run-of-river** plant: no reservoir, the turbine uses the water of the
river that falls between an intake and a powerhouse.

## What you give

1. **Site and river.** Gross head, mean flow, Q95 (the flow exceeded 95 % of the time),
   environmental flow, the flow the turbine is designed for (as the share of time the river
   exceeds it) and, optionally, your yearly electricity demand.
2. **Penstock and turbine.** Length, design velocity (or diameter), roughness, local losses;
   the turbine type (or let RESize choose it from head and flow) and the efficiencies.
3. **Prices and costs.** Cost per kW, O&M, life, discount rate, prices, grid emission factor.
4. **Results and checks.**

## What you get

The flow-duration curve built from the mean flow and Q95, the design flow and rated power, the
penstock diameter and head loss, the turbine type and its minimum flow, the yearly energy and
capacity factor, LCOE, payback, NPV and CO2 avoided, plus a chart of the energy and power against
the design flow. Every step has a "Why?" with formula, assumptions and sources.

## Simplifications

- The flow-duration curve is **log-normal**, fitted to the mean flow and Q95: a snow-fed or
  karst river can differ. Use measured daily flows to check it.
- Efficiencies are constant for each turbine type; partial-load efficiency is covered by a
  single "operating losses" share (default 5 %, a RESize choice).
- One typical year; no floods, ice, water hammer or cavitation checks.
- The cost is proportional to the rated power. The default (6600 euro/kW) is the upper part of
  the NREL ATB range for new run-of-river plants, in USD and not converted: ask for quotes.
- Hydropower is not in the technology comparison and has no Excel export yet.
