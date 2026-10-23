# Biomass

Three pathways in one module: a **solid biomass boiler** (heat), an **ORC cogeneration** plant
(heat and power) and a **biogas** plant (digester and gas engine).

| First step | A middle step | Results |
|---|---|---|
| ![](../screenshots/biomass_start.png) | ![](../screenshots/biomass_middle.png) | ![](../screenshots/biomass_results.png) |

## The steps

1. **Pathway and demand.** Pick the pathway, then enter the heat (boiler, ORC) or electricity
   (biogas) you need and the share to cover.
2. **Fuel or substrate.** Pick from the library (wood chips, pellets, logs, straw; cattle and
   pig slurry, maize and grass silage, biowaste): moisture, heating value, methane yield.
   These are typical handbook values.
3. **Plant and emissions.** Efficiencies, storage and emission factors.
4. **Results and checks.**

## What you get

- Solid fuels and ORC: plant power from the heat load duration curve, fuel per year from
  moisture and heating value, silo size, truck loads and ash.
- Biogas: substrate mix, methane yield, digester volume and retention time, organic loading
  rate, heat balance after heating the digester, crop land and digestate.
- Design checks and the *Why?* panels for every formula.

## Assumptions to remember

The values of fuels and substrates are typical handbook figures: replace them with your
supplier's specification or a laboratory methane potential test. Substrate yields are
checked against the Buswell theoretical limits in the
[cross-checks](../validation/README.md). The module has no cost step yet; the biogas CHP
appears in the [comparison](compare.md) with the same economic assumptions as the other
technologies.
