# Borehole field (ASHRAE length method)

Checks of `core/bhe.py` and `core/bhe_design.py` (run by `tests/test_bhe.py`).

| What | Reference | RESize | Deviation |
|---|---|---|---|
| Thermal diffusivity, ground 1.7 W/(m K), 2200 kg/m3, 1091 J/(kg K) | 7.083e-7 m2/s (by hand) | 7.0827e-7 | rounding |
| Ground resistances R_ga / R_gm / R_gd, borehole 150 mm | 0.2141 / 0.2138 / 0.1040 m K/W (independent Fourier numbers) | same | rounding |
| Grout resistance, d_e 32 mm, spacing 45.2 mm, D_b 150 mm, 1 W/(m K) | 0.0446 m K/W (hand evaluation of the formula) | 0.0446 | < 0.001 |
| Length after the temperature penalty, cooling | 8387.6 m at penalty 0 -> 8873.7 m at -0.783 K (university report) | ratio 1.0580 vs 1.0579 | 0.01 % |
| Exponential integral E1 | 1.822924, 0.219384, 0.024915 (tables) | same | < 1e-5 |

The report quoted is a master's course project (Politecnico di Torino, Geothermal Energy, A.Y.
2024/25); its building loads are only in graphs, so a full end-to-end comparison of the 23
boreholes of the report was not possible. The denominator `T_g - T_fluid - T_p` of the length
formula, and with it the iteration, reproduces the numbers of the report; the penalty itself
is computed there with the "stored energy per column" formula (option `storage` in RESize).

Not done: comparison with a dynamic simulation (EED, GLHEPro, TRNSYS) or a measured field.
