"""'Why?' texts of the ground-source (borehole heat exchanger) module."""

from __future__ import annotations

BHE_EXPLANATIONS: dict[str, dict[str, str]] = {
    "bhe.loads": {
        "title": "Heat taken from and given to the ground",
        "formula": "Q_g,h = P_h (1 - 1/COP);    Q_g,c = -P_c (1 + 1/EER);    "
                   "Q_a = [E_h (1 - 1/COP_ms) - E_c (1 + 1/EER_ms)] / 8760",
        "why": (
            "The ground does not supply all the heat of the building: the compressor of the heat "
            "pump supplies the rest. If the pump delivers P_h to the building with a COP, the "
            "ground gives P_h (1 - 1/COP). In summer the pump takes P_c from the building and "
            "rejects P_c (1 + 1/EER) into the ground: the compressor heat goes there too. The "
            "peak values (design COP and EER) set the length needed for the coldest and the "
            "hottest hour. The yearly average Q_a uses the seasonal values and is the net heat "
            "left in the ground: positive when more heat is taken out than put in, negative when "
            "the ground is warmed up year after year. A field whose Q_a is far from zero drifts "
            "in temperature and needs more length."
        ),
        "assumptions": (
            "Two design points (the peak of heating and the peak of cooling) and two yearly "
            "energies; the heat pump is a black box with fixed COP and EER, whatever the "
            "temperature of the fluid. Domestic hot water is not included."
        ),
        "reference": "Kavanaugh and Rafferty (1997), ch. 2 and 4.",
    },
    "bhe.length": {
        "title": "Length of the boreholes (ASHRAE method)",
        "formula": "L = [Q_a R_ga + Q_g (R_b + PLF R_gm + R_gd F_sc)] / "
                   "[T_g - (T_in + T_out)/2 - T_p]",
        "why": (
            "The ground is seen as three heat pulses acting one after the other: the net load of "
            "ten years (Q_a, through the ground resistance of ten years R_ga), the heat of the "
            "design month (Q_g times the part-load factor PLF, through R_gm) and the heat of the "
            "design day (through R_gd). To these the borehole adds its own resistance R_b, and "
            "the short circuit between the two legs of the U-tube adds a few percent (F_sc). The "
            "sum is the temperature drop per metre of borehole for each watt; dividing by the "
            "temperature difference you can afford between the ground and the mean fluid "
            "(T_g - T_fluid - T_p) gives the length. It is done for heating and for cooling and "
            "the larger length wins. In cooling the loads and the denominator are both negative, "
            "so the length stays positive."
        ),
        "assumptions": (
            "Constant ground properties, one uniform heat flux for each pulse, fluid temperatures "
            "fixed by you (not iterated against the heat pump's COP), no groundwater flow and no "
            "hourly simulation: for a large field use a dynamic simulation."
        ),
        "reference": "Kavanaugh and Rafferty (1997), ch. 3.",
    },
    "bhe.ground": {
        "title": "Resistance of the ground to the three pulses",
        "formula": "G = 0.0758 ln(Fo) + 0.1009;    Fo = 4 alpha tau / D_b^2;    "
                   "R_ga = (G_f - G_1)/lambda,  R_gm = (G_1 - G_2)/lambda,  R_gd = G_2/lambda",
        "why": (
            "How much the ground around the borehole warms or cools for each watt per metre "
            "depends on how long the heat has been flowing: the Fourier number Fo compares that "
            "time with the time the heat needs to cross the borehole radius. The function G, a "
            "fit of the cylindrical source, turns Fo into a temperature rise. The three "
            "resistances come from differences of G at three times: ten years, ten years plus a "
            "month, and ten years plus a month plus six hours, so that each pulse counts only for "
            "its own duration. A ground that conducts heat well (large lambda) or has a larger "
            "diffusivity alpha gives smaller resistances and shorter boreholes."
        ),
        "assumptions": (
            "The line fit of G is meant for Fo above about 1: for very short times it is "
            "extrapolated and never goes below zero. Pulse lengths are the classic 10 years, 30 "
            "days and 6 hours."
        ),
        "reference": "Kavanaugh and Rafferty (1997); Ingersoll et al. (1954).",
    },
    "bhe.borehole": {
        "title": "Resistance of the borehole and the flow in the pipes",
        "formula": "R_b = R_pp + R_gr;    R_pp = [ln(d_e/d_i)/(2 pi lambda_p) + 1/(pi d_i h_i)]/N;    "
                   "Re = 4 m / (pi d_i mu)",
        "why": (
            "Between the fluid and the wall of the borehole the heat crosses three things: the "
            "film of fluid on the inside of the pipe (the heat-transfer coefficient h_i, which "
            "depends on the flow), the wall of the plastic pipe and the grout that fills the "
            "borehole. The first two make R_pp, shared between the N legs of the U-tube; the "
            "grout makes R_gr and depends on the distance between the legs. A turbulent flow "
            "(Re above about 2300) gives a much larger h_i than a laminar one, so a small flow "
            "in a large pipe pays with a longer borehole. R_b is typically 0.08-0.15 m K/W."
        ),
        "assumptions": (
            "Dittus-Boelter for turbulent flow and a constant Nusselt number of 4.36 for laminar "
            "flow; a single U-tube with the two legs at a fixed distance; the casing resistance "
            "is zero. The flow in each borehole is the total flow divided by their number."
        ),
        "reference": "Kavanaugh and Rafferty (1997); Incropera et al. (2011).",
    },
    "bhe.penalty": {
        "title": "Temperature penalty of the neighbouring boreholes",
        "formula": "T_p = (Q_a / L) / (4 pi lambda) * mean over the boreholes of "
                   "sum_j E1(d_ij^2 / (4 alpha t))",
        "why": (
            "Boreholes close to each other share the same ground. If year after year more heat "
            "is taken out than put in, the ground between the boreholes slowly cools (or warms in "
            "a cooling-dominated climate) and every borehole works against a worse ground "
            "temperature. RESize treats each borehole as a line source and adds, for each pair, "
            "the temperature change at the neighbour after the pulse time; the mean over the "
            "field is the penalty T_p. As T_p depends on the number of boreholes, and the length "
            "depends on T_p, the design is iterated (and damped) until the number of boreholes "
            "and the length stop changing. A balanced field has a penalty close to zero."
        ),
        "assumptions": (
            "Constant net load for the pulse time, boreholes as infinite lines, rectangular grid "
            "filled row by row. The alternative 'storage' option uses a formula used in teaching: "
            "the ground column around the borehole stores the net yearly energy, T_p1 = Q / "
            "(S_vc d_s^2 L), weighted by the number of neighbours (N4 + 0.5 N3 + 0.25 N2 + 0.1 N1)/N; "
            "it is very conservative when the imbalance is large."
        ),
        "reference": "Kavanaugh and Rafferty (1997); Ingersoll et al. (1954).",
    },
    "bhe.field": {
        "title": "Number and depth of the boreholes",
        "formula": "N = ceil(L / L_max);    depth = L / N;    area = N d_s^2",
        "why": (
            "The total length is split among boreholes no deeper than the limit you set (drilling "
            "rules, equipment and cost usually stop at 100-200 m, sometimes 400 m): N is the "
            "total length divided by the maximum depth, rounded up, and the real depth is the "
            "total divided by N. The boreholes stand on a grid at the spacing d_s (6-8 m is "
            "typical; closer ones interfere more), so the field needs about N d_s^2 of land. "
            "If the land is not enough, the answer is deeper boreholes or a smaller load, not a "
            "denser field."
        ),
        "assumptions": (
            "Equal boreholes on a rectangular grid, nearly square unless you fix the number of "
            "columns; every borehole has the same flow. A real layout must respect property "
            "lines, buildings, services and the minimum distance from them."
        ),
        "reference": "Kavanaugh and Rafferty (1997), ch. 3.",
    },
    "bhe.economics": {
        "title": "Cost of the field",
        "formula": "CAPEX = L * c_drill;    annual cost = CAPEX * CRF + O&M",
        "why": (
            "Most of the cost of the ground side of a heat pump is drilling, paid per metre "
            "of borehole including pipes, grout and connection. The total length therefore "
            "sets the CAPEX; spread over the life with the capital recovery factor and added to "
            "the maintenance, it gives the yearly cost of the field. Comparing it with the "
            "peak power (metres per kW) lets you judge the design: 15-25 m per kW of heating "
            "load is a common order of magnitude."
        ),
        "assumptions": (
            "One price per metre whatever the depth, ground and number of boreholes; the heat "
            "pump, the manifold, the trenches and the interior system are not included."
        ),
        "reference": "Short, Packey and Holt (1995); the price per metre is a placeholder of RESize.",
    },
}

BHE_TOPIC_ORDER: tuple[str, ...] = (
    "bhe.loads", "bhe.length", "bhe.ground", "bhe.borehole", "bhe.penalty", "bhe.field",
    "bhe.economics",
)
