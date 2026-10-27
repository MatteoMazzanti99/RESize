# Ground-source heat pump (borehole heat exchangers)

A first sizing of a field of **vertical closed-loop boreholes** for a ground-source heat pump,
with the **ASHRAE (Kavanaugh and Rafferty) length method**: how many metres of borehole, how
many boreholes, how deep, and how much land.

## What you give

1. **Loads and heat pump.** Yearly energy and peak power for heating and for cooling (leave one
   at zero for a heating-only or cooling-only building), the share of the energy used in the
   design month, design and seasonal COP and EER, and the fluid temperatures in heating and
   in cooling.
2. **Ground and borehole.** Ground temperature, conductivity, density and specific heat; borehole
   and pipe diameters, distance between the two pipes, pipe and grout conductivity,
   short-circuit factor; properties of the antifreeze fluid.
3. **Field and costs.** Spacing, maximum depth of one borehole, land available, number of
   columns (or "about square"), the way the temperature penalty is computed, drilling cost,
   O&M, life, discount rate.
4. **Results and checks.**

## How it works

1. **Loads on the ground.** Heating gives the ground `Q_g,h = P_h (1 - 1/COP)`; cooling puts
   `P_c (1 + 1/EER)` into it. The yearly net load `Q_a` uses the seasonal COP and EER.
2. **Ground resistances.** The ground is three heat pulses (10 years, one month, six hours).
   `G = 0.0758 ln(Fo) + 0.1009` gives `R_ga`, `R_gm` and `R_gd`.
3. **Borehole resistance.** `R_b = R_pp + R_gr` from the pipes, the film of fluid (which depends
   on the Reynolds number) and the grout.
4. **Length** for heating and for cooling, `L = [Q_a R_ga + Q_g (R_b + PLF R_gm + R_gd F_sc)] /
   (T_g - T_fluid - T_p)`; the larger one governs.
5. **Number of boreholes** `N = ceil(L / maximum depth)`, and the **temperature penalty** `T_p`
   of the neighbours, which depends on `N`: the design is iterated until `N` and `L` stop
   changing.

The penalty has two options. The default treats each borehole as a line source and sums the
effect of the others (exponential integral). The alternative is the "stored energy per column"
formula used in some courses: `T_p1 = Q / (S_vc d_s^2 L)` weighted by the number of neighbours;
it is very conservative if the yearly balance of the ground is far from zero.

## What you get

Length for heating and for cooling, the governing case, number and depth of boreholes, grid and
land needed, temperature penalty, borehole and ground resistances, Reynolds number, drilling cost
and design checks (laminar flow, imbalance of the ground, spacing, land, depth for permits), with
charts and the full list of formulas with your own numbers.

## Simplifications

- Uniform ground and no groundwater flow; one U-tube; equal boreholes on a rectangular grid.
- Fluid temperatures are inputs, not iterated against the performance of the heat pump.
- Three pulses, not an hourly simulation: for a large field use a dynamic simulation and a
  thermal response test.
- The price per metre is a RESize placeholder, and only the drilling is costed (not the heat
  pump, the manifold or the building system).
- Not in the technology comparison: the heat pump does not make energy by itself.
