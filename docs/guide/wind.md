# Wind

Sizes a wind plant from the wind resource: the speed at hub height, the energy of one turbine,
the number of turbines for your demand, the layout with wake losses, and the economics.

| First step | A middle step | Results |
|---|---|---|
| ![](../screenshots/wind_start.png) | ![](../screenshots/wind_middle.png) | ![](../screenshots/wind_results.png) |

## The five steps

1. **Site and wind resource.** *Get mean wind speed from NASA POWER* (a smooth long-term value
   at 50 m) or type a mast or atlas value, with the Weibull shape `k`, the shear exponent and
   the air density inputs (elevation, temperature). *Get the wind rose* downloads three years of
   hourly wind speed and direction (NASA POWER, 50 m) and builds the rose: how often the wind
   comes from each of twelve 30-degree sectors and how strong it is there.
2. **Demand and losses.** Yearly demand, the share to cover, availability and other losses.
3. **Turbine and layout.** Choose a turbine from the **library of 55 real machines** with
   tabulated power curves (from the open NREL turbine-models repository) or type the datasheet
   values. Then choose who decides where the turbines stand: a **regular grid** with the spacing
   you set (and an optional wake model), or **the program places the turbines** inside the
   rectangle of land you give (width, length, direction) **or inside the real boundary of your land**
   loaded from a KML, KMZ or GeoJSON file (draw it as a polygon in Google Earth, QGIS or geojson.io),
   with optional **exclusion zones** (houses, roads, wetlands: more polygons from a file) and a
   **setback** kept from the boundary and the zones, at a minimum distance of your choice.
   In the second case it searches the layout that loses the least energy to the wakes of your
   wind rose. The layout map is drawn on a **satellite picture** of the place (the latitude and
   longitude you typed are the centre of the map); it needs internet and can be switched off. The
   picture is Esri World Imagery, shown with its credit; for a public or commercial use check its
   terms.
4. **Costs and savings.** Installed cost per kW, maintenance, prices, discount rate, emissions.
5. **Results and checks.**

## What you get

Mean speed at hub height, Weibull scale, air density, capacity factor, energy per turbine,
number of turbines, land use, and with the wake model the wake loss, the efficiency of every
turbine and of every wind direction. With the wind rose you also get the **wind rose picture**,
and when the program places the turbines a **map of the site** with every turbine, the wake
cones of the prevailing wind and the share of energy that each turbine keeps, together with the
wake loss of a regular grid of the same turbines for comparison. Then cost of energy, payback, NPV, CO2 and sensitivity.

## Assumptions to remember

The wind rose comes from a reanalysis with a grid of about 50 km: it shows the main directions
but not hills or the coast, and three years can differ from the long-term rose. The program
places turbines in a plain rectangle: it knows nothing about terrain, roads, houses, protected
areas or cables, so check the positions on the ground. The search uses a fast estimate of the
wake loss and the result is then evaluated with the full model; it is repeatable but does not
prove that no better layout exists.

Many curves of the library are reference or theoretical designs, not manufacturer-certified
data: for a real project use the manufacturer's curve and a measured resource. When the wake
model is on, "other losses" should no longer include wakes (3-6 % is more usual). The
economics use the yearly energy and the same simple annuity model as the other modules.

Validation: formulas by hand, an independent integration of the power curve and a PyWake
comparison of the wake model, see [Wind validation](../validation/wind.md) and
[all cross-checks](../validation/README.md).
