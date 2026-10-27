"""'Why?' texts of the wind module (merged into ``EXPLANATIONS``)."""

from __future__ import annotations

WIND_EXPLANATIONS: dict[str, dict[str, str]] = {
    "wind.resource": {
        "title": "Wind resource: mean speed at a reference height",
        "formula": "v_mean = (1/T) * integral of v(t) dt   [m/s, at height h_ref]",
        "why": (
            "Energy in the wind grows with the cube of its speed, so the mean wind speed is the "
            "single most important number of a wind project: a site with 7 m/s mean can give "
            "about 50 % more energy than one with 6 m/s, with the same turbine. Mean speeds "
            "come from a measurement campaign on a mast (best), from a wind atlas or from "
            "reanalysis data (good for a first estimate), and are always tied to a height."
        ),
        "assumptions": (
            "A long-term average is used. A single year can differ by several percent, and "
            "atlas values are smoothed: local terrain can change them noticeably."
        ),
        "reference": "Global Wind Atlas (DTU / World Bank); NASA POWER (WS50M); IEC 61400-12-1.",
    },
    "wind.weibull": {
        "title": "Wind speed distribution: Weibull",
        "formula": "F(v) = 1 - exp(-(v/A)^k),   v_mean = A * Gamma(1 + 1/k)",
        "why": (
            "The mean alone is not enough: a turbine produces nothing below cut-in, saturates "
            "above rated speed, and the power depends on v^3, so the shape of the distribution "
            "matters. A Weibull curve with shape k and scale A describes it well. k near 2 "
            "(the Rayleigh case) is typical of inland sites; k of 3 or more means steady "
            "winds (trade winds); k near 1.5 means gusty, variable winds."
        ),
        "assumptions": (
            "One distribution for the whole year, no daily or seasonal pattern and no wind "
            "direction. k = 2 is a common first guess when no data are available."
        ),
        "reference": "Burton et al., Wind Energy Handbook, ch. 2.",
    },
    "wind.shear": {
        "title": "Wind shear: speed at hub height",
        "formula": "v(h) = v_ref * (h / h_ref)^alpha",
        "why": (
            "Friction with the ground slows the wind near the surface, so it blows faster "
            "higher up. The power law with exponent alpha describes this: about 0.10 over "
            "open water, 0.14 on open flat land, 0.20-0.30 over forest or towns. Taller towers "
            "capture more energy but cost more: this formula tells you how much more."
        ),
        "assumptions": (
            "A single exponent between the two heights, neutral atmospheric stability. "
            "The exponent should be measured on site when the project is serious."
        ),
        "reference": "Burton et al., Wind Energy Handbook; IEC 61400-1 (normal wind profile).",
    },
    "wind.air_density": {
        "title": "Air density",
        "formula": "rho = p / (R * T),   p = 101325 * (1 - 2.25577e-5 * z)^5.25588,   R = 287.05",
        "why": (
            "The power in the wind is 0.5 * rho * A * v^3, so thinner air means less power. "
            "Power curves are published at sea-level standard density, 1.225 kg/m3. At 1500 m "
            "the density is about 17 % lower, and in hot climates it drops further. The "
            "calculation corrects the power curve to the density of your site."
        ),
        "assumptions": (
            "Standard atmosphere pressure vs elevation and the yearly mean temperature. "
            "Humidity is neglected (a small effect)."
        ),
        "reference": "ISO 2533 (standard atmosphere); IEC 61400-12-1 (density normalisation).",
    },
    "wind.power_curve": {
        "title": "Turbine power curve",
        "formula": (
            "P = 0 for v < v_cut-in;  P = P_rated * (v^3 - v_ci^3) / (v_r^3 - v_ci^3) up to "
            "v_rated;  P = P_rated up to v_cut-out;  P = 0 above"
        ),
        "why": (
            "Four speeds define a turbine: cut-in (it starts producing), rated (it reaches "
            "full power; above it the blades pitch to hold the power constant), cut-out (it "
            "stops to protect itself). Between cut-in and rated the power follows the cube of "
            "the speed. The curve is the link between wind climate and energy: the same wind "
            "gives very different energy with different curves."
        ),
        "assumptions": (
            "Either a smooth generic curve or, if you pick a turbine from the library, its "
            "tabulated curve (read by linear interpolation). Library curves are mostly "
            "theoretical; a measured curve (IEC 61400-12-1) is better, and the curve is "
            "corrected for air density in the same simple way in both cases."
        ),
        "reference": "IEC 61400-12-1; NREL turbine-models (power curve archive); manufacturer datasheet.",
    },
    "wind.cp_betz": {
        "title": "Power coefficient and the Betz limit",
        "formula": "Cp = P / (0.5 * rho * A * v^3);   Cp <= 16/27 = 0.593 (Betz)",
        "why": (
            "A turbine cannot extract all the kinetic energy of the wind: the air has to keep "
            "moving behind the rotor. Betz showed that the best possible share is 16/27, about "
            "59 %. Real machines reach a peak Cp of 0.40-0.50; at rated wind speed the blades "
            "already pitch away, so Cp there is typically 0.25-0.40. Computing Cp from "
            "datasheet values is a quick test: if you get a value above 0.5, a number is wrong."
        ),
        "assumptions": "Cp computed at rated speed and at your site's air density.",
        "reference": "Betz (1926); Burton et al., Wind Energy Handbook, ch. 3.",
    },
    "wind.annual_energy": {
        "title": "Annual energy of one turbine",
        "formula": "E = 8760 * sum_i P(v_i) * [F(v_i + dv/2) - F(v_i - dv/2)]",
        "why": (
            "The probability of each wind speed (from the Weibull distribution) is multiplied "
            "by the power the turbine gives at that speed, and the products are summed over "
            "all speeds. The result is the expected power averaged over the year; times 8760 "
            "hours it gives the energy. Speeds are binned every 0.1 m/s from 0 to 40 m/s."
        ),
        "assumptions": (
            "Gross energy at the turbine terminals: no wake, availability or electrical losses "
            "yet. Those are applied in the next step."
        ),
        "reference": "Burton et al., Wind Energy Handbook; IEC 61400-12-1 (AEP).",
    },
    "wind.losses": {
        "title": "Availability and other losses",
        "formula": "E_net = E_gross * availability * (1 - other losses)",
        "why": (
            "A real plant does not deliver the gross energy. Turbines stop for maintenance "
            "and faults (availability, typically 96-98 %). Wakes of upwind turbines reduce the "
            "wind seen by the others (a few % to 15 %), and there are electrical losses, icing, "
            "noise or bird curtailment, grid limits. First-pass designs often use 10-15 % in "
            "total for 'other losses'."
        ),
        "assumptions": (
            "Two single numbers. A wake model (Jensen, Park) and a layout are needed for a "
            "bankable estimate."
        ),
        "reference": "Burton et al., Wind Energy Handbook; EWEA, Wind Energy: The Facts.",
    },
    "wind.capacity_factor": {
        "title": "Capacity factor and full-load hours",
        "formula": "CF = E / (P_rated * 8760);   full-load hours = E / P_rated",
        "why": (
            "The capacity factor is the average power divided by the rated power. It is the "
            "quickest way to judge a design: onshore plants are usually between 25 and 40 %, "
            "good offshore sites exceed 45 %. A value below 20 % suggests a poor site or a "
            "turbine too big for the wind; above 50 % is rarely realistic and means that an "
            "input should be checked."
        ),
        "assumptions": "Yearly averages; the hourly production profile is not modelled.",
        "reference": "IEA Wind TCP annual reports; IRENA Renewable Power Generation Costs.",
    },
    "wind.number_of_turbines": {
        "title": "Number of turbines",
        "formula": "N = ceil(coverage * E_demand / E_net,turbine)",
        "why": (
            "The yearly energy of one turbine fixes how many are needed to supply a share of "
            "the demand. Turbines come in whole units, so the delivered energy is usually a bit "
            "above the target; for a small demand, a single large turbine can supply many "
            "times what is needed."
        ),
        "assumptions": (
            "Identical turbines, all with the same wind. Self-consumption, grid export and "
            "storage are not evaluated."
        ),
    },
    "wind.spacing": {
        "title": "Turbine spacing and land use",
        "formula": "Area = N * (crosswind spacing x downwind spacing) * D^2",
        "why": (
            "A turbine leaves a wake of slower, more turbulent air behind it. Placing turbines "
            "too close lowers the energy of those downstream and increases fatigue loads. "
            "Rules of thumb: 3-5 diameters across the prevailing wind and 5-9 along it for "
            "moderate wake loss (wider if the wind is very directional). The spacing also "
            "tells you how much land is needed, although most of it can keep its use "
            "(agriculture)."
        ),
        "assumptions": (
            "Regular rectangular layout. Real layouts follow terrain, roads, setbacks and "
            "the wind rose."
        ),
        "reference": "Burton et al., Wind Energy Handbook, ch. 8; local planning rules.",
    },
    "wind.wake": {
        "title": "Wake losses: the Jensen (Park) model",
        "formula": "deficit = (1 - sqrt(1 - Ct)) * (r0 / (r0 + k x))^2;  v = v0 * (1 - sqrt(sum of deficits^2))",
        "why": (
            "Behind a turbine there is a cone of slower air that widens as it goes downwind: "
            "its radius grows by k metres for every metre of distance (k = 0.075 on land, "
            "about 0.04 at sea where the air is less turbulent). The speed deficit is "
            "largest right behind the rotor and decays with the square of the cone radius. "
            "A turbine only suffers when the cone overlaps its rotor, fully or partly. With "
            "several upwind turbines the deficits are combined as the root of the sum of "
            "squares. The energy is then recomputed with the reduced speed through the power "
            "curve, for every wind direction and every speed. The sum, compared with the "
            "energy without wakes, is the array efficiency: the wake loss is what is missing."
        ),
        "assumptions": (
            "Top-hat wake, a generic thrust curve (0.8 below rated speed), one wind-speed "
            "distribution for all directions, flat terrain, neutral stability. Real farms also "
            "have turbulence effects, blockage and terrain: the Jensen model is a first-pass "
            "tool (typically within a few points of the loss of real onshore farms)."
        ),
        "reference": "Jensen, A note on wind generator interaction, Risoe-M-2411 (1983); Katic et al., EWEC 1986.",
    },
    "wind.rose": {
        "title": "Wind rose and layout across the prevailing wind",
        "formula": "share(sector) = hours from the sector / total hours;    "
                   "energy(sector) ~ share * (mean speed of the sector)^3",
        "why": (
            "The wind does not blow equally from all directions, and the wakes only matter "
            "when a turbine stands behind another one for the wind that is blowing. The wind "
            "rose says how often the wind comes from each of twelve 30-degree sectors and how "
            "strong it is there. RESize builds it from the hourly wind speed and direction of "
            "NASA POWER (three years, 50 m); you can also describe it by hand with a "
            "prevailing direction and a concentration (0 = all directions equal, 1-2 = a "
            "typical site). A strong wind counts more: the energy of the wind goes with the "
            "cube of its speed, so a direction that blows less often but harder can matter "
            "more than a frequent weak one. If the wind comes mostly from one side, the rows "
            "go across that direction with a large distance along it; when the wind turns by "
            "90 degrees a row becomes a line of turbines one behind the other and the loss in "
            "that sector is large."
        ),
        "assumptions": (
            "Three years of reanalysis data (about 50 km grid) at 50 m: it shows the main "
            "directions but not the effect of hills, valleys or the coast, and three years "
            "can differ from the long-term rose. A measurement mast or the Global Wind Atlas "
            "is better for a real project. Every sector uses the same Weibull shape k, scaled "
            "to the mean speed of the sector."
        ),
        "reference": "NASA POWER hourly data (MERRA-2); Burton et al., Wind Energy Handbook, ch. 8; Global Wind Atlas wind roses.",
    },
    "wind.layout": {
        "title": "Turbines placed by the program inside your site",
        "formula": "minimise  loss = sum over sectors of w_s * (1 - mean over turbines of "
                   "(1 - sqrt(sum of deficits^2))^3);    distance between turbines >= m * D",
        "why": (
            "Instead of a regular grid you can give the program the area you have (width, "
            "length and direction of a rectangle, or the real boundary of the land from a KML "
            "or GeoJSON file, with zones to avoid and a setback) and the closest two turbines "
            "may stand "
            "(typically 3 rotor diameters, D). The program then decides where each turbine "
            "goes. It starts from an even pattern and moves one turbine at a time to a new "
            "spot: a move is kept when the wake loss falls, and sometimes also when it rises "
            "a little, early in the search, so the layout does not get stuck in a bad "
            "arrangement (simulated annealing). The loss it minimises counts every wind "
            "direction by the energy that it carries, so the turbines spread out along the "
            "directions that matter and may stand close together across them. Because the "
            "area is limited, turbines usually end up near its edges and spread out. The "
            "result is then evaluated with the full wake model, and the map shows where each "
            "turbine stands and how much of its energy it keeps."
        ),
        "assumptions": (
            "Only the boundary and the exclusion zones you give are respected (a plain "
            "rectangle has none): roads, houses, protected areas and terrain not drawn there "
            "must be checked on the ground. The search uses a simple estimate of the wake "
            "loss (fixed thrust coefficient), so the best layout of the full model could be "
            "slightly different; the search is repeatable but it does not prove that no better "
            "layout exists. The number of turbines comes from your demand, not from the area. "
            "Noise, shadow, cables and access are not considered."
        ),
        "reference": "Mosetti, Poloni and Diviacco (1994); Kirkpatrick, Gelatt and Vecchi (1983).",
    },
}

WIND_TOPIC_ORDER: tuple[str, ...] = (
    "wind.resource",
    "wind.weibull",
    "wind.shear",
    "wind.air_density",
    "wind.power_curve",
    "wind.cp_betz",
    "wind.annual_energy",
    "wind.losses",
    "wind.capacity_factor",
    "wind.number_of_turbines",
    "wind.spacing",
    "wind.wake",
    "wind.rose",
    "wind.layout",
    "wind.economics",
    "wind.sensitivity",
)
