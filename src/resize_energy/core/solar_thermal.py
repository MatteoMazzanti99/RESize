"""Solar thermal collectors, hot-water store and adsorption cooling: physics and hourly model.

Pure calculation, no GUI. One year is simulated hour by hour with a single, fully mixed
store. The weather is a synthetic but physical year (clear-sky shape times daily cloudiness)
scaled to the annual irradiation on the collector plane that the user supplies (for example
from PVGIS), plus a seasonal and daily temperature wave.

Simplifications, on purpose: one store temperature (no stratification), constant flow,
incidence-angle effects folded into the collector's zero-loss efficiency, no piping losses
(a single factor covers them), no freezing or boiling of the fluid except a hard stagnation
limit.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

HOURS = 8760
WATER_KWH_PER_L_K = 0.001163        # specific heat of water, kWh per litre and kelvin
T_STAGNATION = 95.0                 # store limit: above this the plant dumps the heat [degC]


@dataclass(frozen=True)
class CollectorType:
    name: str
    eta0: float            # zero-loss efficiency (on aperture area)
    a1: float              # first-order heat-loss coefficient [W/(m2 K)]
    a2: float              # second-order coefficient [W/(m2 K2)]
    cost_per_m2: float     # installed, euro per m2 of aperture (indicative)


COLLECTORS: dict[str, CollectorType] = {
    "unglazed": CollectorType("Unglazed (pool)", 0.88, 15.0, 0.0, 120.0),
    "flat": CollectorType("Flat plate (glazed)", 0.78, 3.6, 0.015, 380.0),
    "tube": CollectorType("Evacuated tube", 0.74, 1.3, 0.006, 520.0),
}


def collector_efficiency(c: CollectorType, t_mean_c: float, t_amb_c: float, g_w_m2: float) -> float:
    """Steady-state efficiency eta = eta0 - a1 dT/G - a2 dT^2/G (never below zero)."""
    if g_w_m2 <= 0:
        return 0.0
    dt = t_mean_c - t_amb_c
    return max(0.0, c.eta0 - c.a1 * dt / g_w_m2 - c.a2 * dt * dt / g_w_m2)


@dataclass(frozen=True)
class Weather:
    g_w_m2: tuple[float, ...]       # irradiance on the collector plane
    t_amb_c: tuple[float, ...]


def synthetic_weather(lat_deg: float, annual_kwh_m2: float, t_mean_c: float, t_season_amp_c: float,
                      t_day_amp_c: float = 5.0, seed: int = 11) -> Weather:
    """A physical, invented year whose irradiation on the collector plane is ``annual_kwh_m2``."""
    if annual_kwh_m2 <= 0:
        raise ValueError("the annual irradiation must be > 0")
    rng = random.Random(seed)
    phi = math.radians(lat_deg)
    south = 1.0 if lat_deg >= 0 else -1.0
    g: list[float] = []
    amb: list[float] = []
    for day in range(365):
        decl = math.radians(23.45) * math.sin(2 * math.pi * (284 + day + 1) / 365)
        clouds = min(1.0, max(0.12, rng.gauss(0.62, 0.30)))
        # coldest around 20 January in the northern hemisphere
        season = -math.cos(2 * math.pi * (day - 20) / 365) * south
        t_day = t_mean_c + t_season_amp_c * season
        for hour in range(24):
            omega = math.radians(15.0 * (hour + 0.5 - 12.0))
            cos_z = (math.sin(phi) * math.sin(decl)
                     + math.cos(phi) * math.cos(decl) * math.cos(omega))
            g.append(max(0.0, cos_z) * clouds)
            amb.append(t_day + t_day_amp_c * clouds * math.cos(2 * math.pi * (hour - 15) / 24))
    k = annual_kwh_m2 * 1000.0 / sum(g)
    return Weather(tuple(v * k for v in g), tuple(amb))


def mains_temperature(day: int, t_mean_c: float, t_season_amp_c: float) -> float:
    """Cold-water temperature: follows the ground, damped and delayed against the air."""
    return max(4.0, t_mean_c - 0.5 * t_season_amp_c * math.cos(2 * math.pi * (day - 50) / 365))


DAILY_DRAW_SHAPE = (0, 0, 0, 0, 0, 1, 4, 6, 4, 2, 1, 1, 2, 1, 1, 1, 1, 2, 4, 6, 5, 3, 1, 0)
_DRAW_SUM = float(sum(DAILY_DRAW_SHAPE))


def dhw_demand_kwh(day: int, hour: int, litres_per_day: float, t_use_c: float,
                   t_mean_c: float, t_season_amp_c: float) -> float:
    """Heat needed in this hour to bring the water drawn from the mains to ``t_use_c``."""
    cold = mains_temperature(day, t_mean_c, t_season_amp_c)
    return litres_per_day * DAILY_DRAW_SHAPE[hour] / _DRAW_SUM * WATER_KWH_PER_L_K * max(
        0.0, t_use_c - cold)


def cooling_load_profile(weather: Weather, annual_kwh: float, balance_c: float = 18.0
                         ) -> tuple[float, ...]:
    """Hourly cooling demand [kWh]: proportional to how far the air is above the balance
    temperature, during working hours (8-20 h)."""
    if annual_kwh <= 0:
        return (0.0,) * HOURS
    raw = [max(0.0, weather.t_amb_c[t] - balance_c) if 8 <= t % 24 < 20 else 0.0
           for t in range(HOURS)]
    total = sum(raw)
    if total <= 0:
        return (0.0,) * HOURS
    return tuple(annual_kwh * r / total for r in raw)


@dataclass(frozen=True)
class ChillerType:
    key: str
    name: str
    cop_nominal: float          # thermal COP at the nominal drive temperature
    t_drive_min_c: float        # below this the machine does not work
    t_drive_nominal_c: float
    parasitic: float            # electricity per kWh of cold (pumps, fans, cooling tower)
    cost_per_kw: float          # euro per kW of cooling, with heat rejection (indicative)


# Typical catalogue values for small and medium machines, to replace with a datasheet.
CHILLERS: dict[str, ChillerType] = {
    "adsorption": ChillerType("adsorption", "Adsorption chiller (silica gel / water)",
                              0.55, 60.0, 80.0, 0.03, 1100.0),
    "absorption": ChillerType("absorption", "Absorption chiller (LiBr / water, single effect)",
                              0.70, 75.0, 90.0, 0.04, 800.0),
    "desiccant": ChillerType("desiccant", "Desiccant cooling (open cycle, air)",
                             0.60, 50.0, 70.0, 0.10, 1000.0),
}


def chiller_cop(cop_nom: float, t_drive_c: float, t_min_c: float, t_nom_c: float) -> float:
    """Thermal COP of a heat-driven chiller at the drive temperature of the hot water.

    Zero below the minimum temperature, rising linearly to ``cop_nom`` at the nominal one
    (a straight line is a fair summary of the catalogue curves of silica-gel/water machines).
    """
    if t_drive_c < t_min_c:
        return 0.0
    if t_drive_c >= t_nom_c:
        return cop_nom
    return cop_nom * (0.45 + 0.55 * (t_drive_c - t_min_c) / max(1e-9, t_nom_c - t_min_c))


adsorption_cop = chiller_cop        # the first chiller of RESize was an adsorption one


@dataclass(frozen=True)
class SolarSystem:
    area_m2: float
    collector: CollectorType
    store_litres: float
    store_ua_w_k: float
    loop_loss: float = 0.08          # share of the collector heat lost in pipes and pump
    t_room_c: float = 18.0
    flow_delta_t_c: float = 6.0      # collector outlet minus store temperature while running
    # --- loads ---
    dhw_litres_per_day: float = 0.0
    t_use_c: float = 55.0
    cooling_kwh_per_year: float = 0.0
    # --- adsorption chiller ---
    chiller_kw_cooling: float = 0.0
    cop_nominal: float = 0.55
    t_drive_min_c: float = 60.0
    t_drive_nominal_c: float = 80.0
    chiller_parasitic: float = 0.03  # kWh electricity per kWh of cooling (pumps, fans, tower)
    compressor_cop: float = 3.0      # of the conventional chiller that would otherwise run


@dataclass(frozen=True)
class SolarRun:
    collector_kwh: float             # heat delivered by the collector loop into the store
    heat_demand_kwh: float           # hot-water demand
    heat_solar_kwh: float            # covered by the sun
    heat_backup_kwh: float
    cooling_demand_kwh: float
    cooling_solar_kwh: float         # cold produced by the adsorption chiller
    chiller_heat_kwh: float          # hot water consumed by the chiller
    cooling_backup_kwh: float
    store_loss_kwh: float
    wasted_kwh: float                # dumped at the stagnation limit
    hours_stagnation: int
    hours_below_drive: int           # cooling wanted but the store too cold for the chiller
    monthly_collector_kwh: tuple[float, ...]
    monthly_heat_solar_kwh: tuple[float, ...]
    monthly_heat_demand_kwh: tuple[float, ...]
    monthly_cooling_solar_kwh: tuple[float, ...]
    monthly_cooling_demand_kwh: tuple[float, ...]
    store_temp_week: dict[str, tuple[float, ...]]   # "winter"/"summer" -> 168 hourly values
    cop_nominal: float = 0.55
    t_start_c: float = 0.0
    t_end_c: float = 0.0
    store_capacity_kwh_k: float = 0.0

    @property
    def heat_fraction(self) -> float:
        return self.heat_solar_kwh / self.heat_demand_kwh if self.heat_demand_kwh > 0 else 0.0

    @property
    def cooling_fraction(self) -> float:
        return (self.cooling_solar_kwh / self.cooling_demand_kwh
                if self.cooling_demand_kwh > 0 else 0.0)

    @property
    def useful_thermal_kwh(self) -> float:
        """Heat that replaced a boiler: hot water plus the heat that drove the chiller."""
        return self.heat_solar_kwh + self.chiller_heat_kwh

    @property
    def solar_fraction(self) -> float:
        """Share of the heat asked of the plant that is solar, counting the cold as the heat
        a boiler-driven chiller of the nominal COP would need (cold / COP)."""
        need = self.heat_demand_kwh + self.cooling_demand_kwh / self.cop_nominal
        got = self.heat_solar_kwh + self.cooling_solar_kwh / self.cop_nominal
        return got / need if need > 0 else 0.0


_MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
_MONTH_OF_DAY = tuple(m for m, n in enumerate(_MONTH_DAYS) for _ in range(n))


def simulate(system: SolarSystem, weather: Weather, t_mean_c: float, t_season_amp_c: float
             ) -> SolarRun:
    """Hour-by-hour energy balance of the collector loop, the store and the loads."""
    s = system
    if s.area_m2 < 0 or s.store_litres <= 0:
        raise ValueError("the collector area cannot be negative and the store must be > 0 L")
    cap = s.store_litres * WATER_KWH_PER_L_K          # kWh per kelvin
    cooling = cooling_load_profile(weather, s.cooling_kwh_per_year)
    m_col, m_hs, m_hd, m_cs, m_cd = ([0.0] * 12 for _ in range(5))
    t_store = max(20.0, t_mean_c)
    t_start = t_store
    col = heat_dem = heat_sol = cool_dem = cool_sol = ch_heat = loss = wasted = 0.0
    stag = below = 0
    weeks = {"winter": (15 * 24, []), "summer": (196 * 24, [])}
    chiller_heat_cap = (s.chiller_kw_cooling / s.cop_nominal) if s.cop_nominal > 0 else 0.0
    for t in range(HOURS):
        day, hour = divmod(t, 24)
        m = _MONTH_OF_DAY[day]
        g, ta = weather.g_w_m2[t], weather.t_amb_c[t]
        # 1. collector loop
        if s.area_m2 > 0 and g > 0:
            eta = collector_efficiency(s.collector, t_store + s.flow_delta_t_c / 2.0, ta, g)
            q = eta * g * s.area_m2 / 1000.0 * (1.0 - s.loop_loss)
            if q > 0:
                t_store += q / cap
                col += q
                m_col[m] += q
        # 2. stagnation limit: dump the excess heat
        if t_store > T_STAGNATION:
            dump = (t_store - T_STAGNATION) * cap
            wasted += dump
            col -= dump
            m_col[m] -= dump
            t_store = T_STAGNATION
            stag += 1
        # 3. hot-water draw (preheat when the store is colder than the use temperature)
        d = dhw_demand_kwh(day, hour, s.dhw_litres_per_day, s.t_use_c, t_mean_c, t_season_amp_c)
        if d > 0:
            mains = mains_temperature(day, t_mean_c, t_season_amp_c)
            share = min(1.0, max(0.0, (t_store - mains) / max(1e-9, s.t_use_c - mains)))
            got = d * share
            t_store -= got / cap
            heat_dem += d
            heat_sol += got
            m_hd[m] += d
            m_hs[m] += got
        # 4. adsorption chiller
        c_need = cooling[t]
        if c_need > 0:
            cool_dem += c_need
            m_cd[m] += c_need
            cop = chiller_cop(s.cop_nominal, t_store, s.t_drive_min_c, s.t_drive_nominal_c)
            if cop > 0 and s.chiller_kw_cooling > 0:
                avail = max(0.0, (t_store - s.t_drive_min_c) * cap)
                heat = min(c_need / cop, chiller_heat_cap, avail)
                made = heat * cop
                t_store -= heat / cap
                ch_heat += heat
                cool_sol += made
                m_cs[m] += made
            else:
                below += 1
        # 5. standing loss of the store
        lost = s.store_ua_w_k * max(0.0, t_store - s.t_room_c) / 1000.0
        loss += lost
        t_store -= lost / cap
        t_store = max(t_store, 4.0)
        for start, buf in weeks.values():
            if start <= t < start + 168:
                buf.append(t_store)
    run = SolarRun(
        collector_kwh=col, heat_demand_kwh=heat_dem, heat_solar_kwh=heat_sol,
        heat_backup_kwh=heat_dem - heat_sol, cooling_demand_kwh=cool_dem,
        cooling_solar_kwh=cool_sol, chiller_heat_kwh=ch_heat,
        cooling_backup_kwh=max(0.0, cool_dem - cool_sol), store_loss_kwh=loss,
        wasted_kwh=wasted, hours_stagnation=stag, hours_below_drive=below,
        monthly_collector_kwh=tuple(m_col), monthly_heat_solar_kwh=tuple(m_hs),
        monthly_heat_demand_kwh=tuple(m_hd), monthly_cooling_solar_kwh=tuple(m_cs),
        monthly_cooling_demand_kwh=tuple(m_cd),
        store_temp_week={k: tuple(v) for k, (_, v) in weeks.items()},
        cop_nominal=s.cop_nominal, t_start_c=t_start, t_end_c=t_store,
        store_capacity_kwh_k=cap)
    return run
