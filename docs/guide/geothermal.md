# Geothermal (hydrothermal)

A first sizing of a geothermal plant on hot water from wells, with two pathways.

- **Heat:** a doublet (production and injection well) and a heat exchanger feed a heat network.
  Sized on the heat load-duration curve, like the biomass boiler; wells are added in pairs.
- **Electricity:** a **binary** plant (below about 180 degC) or a **flash** plant (above),
  sized on the electricity demand.

## What you give

1. **Pathway and resource.** Temperature and flow of a well, ambient temperature, ground
   gradient, pump pressure and efficiency, availability.
2. **Plant and demand.** Heat demand, peak load and coverage, return temperature (heat) or
   electricity demand, reinjection temperature and plant type (power).
3. **Prices and costs.** Drilling cost per metre and surface equipment (heat), cost per kW of
   net power (power), O&M, life, prices and emissions.
4. **Results and checks.**

## What you get

Number of well pairs and their depth, net power or delivered heat, pumping electricity and the
seasonal performance factor (SPF), coverage of the demand, LCOE, payback, NPV and CO2 avoided,
with charts of the load and the energy (heat) or of the power and the temperatures (power).

## Simplifications

- The temperature and flow of the wells are **your hypothesis**: only a test well or a
  geological study gives them. Exploration cost and risk, failed wells and stimulation are not
  included, and the reservoir does not decline or cool down.
- The binary efficiency is a fit of ten plants (MIT 2006) valid for 103-166 degC; outside this
  range it is an extrapolation.
- The drilling cost (1500 euro/m) comes from a 2004 dollar value; the surface cost per kW of
  heat and the O&M share are RESize's typical values without a source.
- Geothermal is not in the technology comparison and has no Excel export yet.
