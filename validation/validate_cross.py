"""Cross-checks of every RESize technology against independent calculations and, when they are
installed, against established open-source tools.

Run:  python validation/validate_cross.py            (pvlib and PyWake optional, internet for PVGIS)
      python validation/validate_cross.py --offline  (only the checks that need nothing)

Writes docs/validation/cross.md. Exit code 1 only if a HARD check fails (an independent
recomputation that must agree to rounding). Comparisons with other tools and with published
ranges are reported with their differences: they say how far a simplified model is from a
reference, they are not pass/fail.

Sections
  A  Wind     second implementation of Jensen for two turbines, then PyWake (NOJ)
  B  PV       sun position and monthly shape against pvlib (PVGIS typical year), battery on a
              real hourly year against the invented one
  C  Biogas   substrate yields against the Buswell theoretical limits
  D  Hydrogen LCOH recomputed by hand for a grid-only plant; plausibility range
  E  Battery  second implementation of the dispatch; plausibility range
  F  Economics LCOE of PV and wind against published global averages
  G  Solar thermal  second implementation of the hourly loop; f-chart (Klein); plausibility
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from resize_energy.core import battery as bat
from resize_energy.core import economics as eco
from resize_energy.core import hydrogen as h2
from resize_energy.core import profiles as prof
from resize_energy.core import pv_extra, wind
from resize_energy.core import solar_thermal as stm
from resize_energy.core import wind_wake as ww
from resize_energy.core.battery_design import BatteryInputs, BatteryProfiles, size_battery
from resize_energy.core.comparison import ComparisonInputs, compare_technologies
from resize_energy.core.fuel_library import SUBSTRATES
from resize_energy.core.hydrogen_design import HydrogenInputs, HydrogenProfiles, size_hydrogen_plant
from resize_energy.core.solar_thermal_design import SolarThermalInputs, size_solar_thermal
from resize_energy.core.wind_design import TurbineSpec, WindInputs

SITES = [("Torino", 45.07, 7.69), ("Palermo", 38.12, 13.36), ("Berlin", 52.52, 13.40)]


@dataclass
class Section:
    title: str
    intro: str = ""
    header: tuple[str, ...] = ()
    rows: list[tuple] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    hard_ok: bool = True


def md_table(header, rows) -> list[str]:
    if not header:
        return []
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out + [""]


# ---------------------------------------------------------------- A. wind
def _independent_two_turbine(power, k_w, mean, d, spacing_d, decay, cut_in, rated, cut_out) -> float:
    """Efficiency of two aligned turbines by the closed-form Jensen deficit (own code)."""
    scale = mean / math.gamma(1 + 1 / k_w)

    def cdf(v):
        return 1.0 - math.exp(-((max(v, 0.0) / scale) ** k_w))

    free = wake = 0.0
    for v in range(int(math.ceil(cut_in)), int(cut_out)):
        p = cdf(v + 0.5) - cdf(v - 0.5)
        ct = 0.0 if v < cut_in else 0.8 if v <= rated else max(0.05, 0.8 * (rated / v) ** 3)
        delta = (1 - math.sqrt(1 - ct)) / (1 + 2 * decay * spacing_d) ** 2
        free += 2 * p * power(v)
        wake += p * (power(v) + power(v * (1 - delta)))
    return wake / free


def section_wind(offline: bool) -> Section:
    s = Section("A. Wind: wake model",
                "Jensen (Park) wakes. First an independent re-implementation for two aligned "
                "turbines (must agree to rounding), then PyWake's NOJ model when installed.",
                ("Check", "Reference", "RESize", "Difference", "Result"))
    t = TurbineSpec()

    def power(v):
        return wind.generic_power_kw(v, t.rated_power_kw, t.cut_in_ms, t.rated_speed_ms,
                                     t.cut_out_ms, 1.225)

    for spacing in (5.0, 7.0, 10.0):
        pos = ww.grid_layout(2, 1, 5, spacing, t.rotor_diameter_m, False, 270.0)
        weights = tuple(1.0 if i == 9 else 0.0 for i in range(12))
        mine = ww.wake_efficiency(pos, power, t.rotor_diameter_m, 7.0, 2.0, t.cut_in_ms,
                                  t.rated_speed_ms, t.cut_out_ms, 0.075, weights)
        ref = _independent_two_turbine(power, 2.0, 7.0, t.rotor_diameter_m, spacing, 0.075,
                                       t.cut_in_ms, t.rated_speed_ms, t.cut_out_ms)
        ok = math.isclose(ref, mine.array_efficiency, rel_tol=1e-9, abs_tol=1e-12)
        s.hard_ok &= ok
        s.rows.append((f"2 turbines in line, {spacing:g} D", f"{ref:.6f}",
                       f"{mine.array_efficiency:.6f}",
                       f"{(mine.array_efficiency - ref) * 100:+.4f} pts",
                       "match" if ok else "**NO**"))
    try:
        import numpy as np
        from py_wake import NOJ
        from py_wake.site import UniformWeibullSite
        from py_wake.wind_turbines.generic_wind_turbines import GenericWindTurbine
    except Exception as exc:  # noqa: BLE001 - optional dependency
        s.notes.append(f"PyWake comparison not run: {exc.__class__.__name__}: {exc}")
        return s
    try:
        for label, n, per_row, cross, down, conc in (
                ("12 turbines 5Dx7D, prevailing wind", 12, 4, 5, 7, 2.0),
                ("12 turbines 8Dx10D, prevailing wind", 12, 4, 8, 10, 2.0),
                ("12 turbines 5Dx7D, uniform rose", 12, 4, 5, 7, 0.0),
                ("25 turbines 5Dx7D, prevailing wind", 25, 5, 5, 7, 2.0)):
            weights = ww.rose_weights(270.0, conc)
            pos = ww.grid_layout(n, per_row, cross, down, t.rotor_diameter_m, True, 270.0)
            mine = ww.wake_efficiency(pos, power, t.rotor_diameter_m, 7.0, 2.0, t.cut_in_ms,
                                      t.rated_speed_ms, t.cut_out_ms, 0.075, weights)
            scale = 7.0 / math.gamma(1.5)
            site = UniformWeibullSite(p_wd=list(weights), a=[scale] * 12, k=[2.0] * 12, ti=0.1)
            wt = GenericWindTurbine("G2000", t.rotor_diameter_m, t.hub_height_m,
                                    power_norm=t.rated_power_kw)
            wfm = NOJ(site, wt, k=0.075)
            x = np.array([p[0] for p in pos])
            y = np.array([p[1] for p in pos])
            sim = wfm(x, y)
            eff = float(sim.aep().sum() / sim.aep(with_wake_loss=False).sum())
            s.rows.append((f"PyWake NOJ: {label}", f"{(1 - eff) * 100:.2f} % loss",
                           f"{(1 - mine.array_efficiency) * 100:.2f} % loss",
                           f"{(mine.array_efficiency - eff) * 100:+.2f} pts", "info"))
        s.notes.append("PyWake's generic turbine has its own thrust curve and RESize a simple "
                       "one (0.8 below rated), so differences of 1-2 points are expected.")
    except Exception as exc:  # noqa: BLE001
        s.notes.append(f"PyWake comparison failed: {exc.__class__.__name__}: {exc}")
    return s


# ---------------------------------------------------------------- B. PV
def section_pv(offline: bool) -> Section:
    s = Section("B. Photovoltaic: sun position, monthly shape, real hourly year",
                "Sun position (used by the shading model) and month-by-month shape against "
                "pvlib; the battery result on a real typical year against the invented one.",
                ("Check", "Reference", "RESize", "Difference", "Result"))
    try:
        import pandas as pd
        import pvlib
    except Exception as exc:  # noqa: BLE001
        s.notes.append(f"pvlib comparison not run: {exc.__class__.__name__}: {exc}")
        return s
    try:
        worst_el = worst_az = 0.0
        for lat in (45.0, 38.0, -35.0):
            for doy in (80, 172, 266, 355):
                for solar_hour in (9.5, 12.5, 15.5):
                    eot = float(pvlib.solarposition.equation_of_time_spencer71(doy))
                    utc = pd.Timestamp("2021-01-01", tz="UTC") + pd.Timedelta(
                        days=doy - 1, hours=solar_hour - eot / 60.0)
                    ref = pvlib.solarposition.get_solarposition(utc, lat, 0.0)
                    el, az = pv_extra.sun_position(doy - 1, solar_hour, lat)
                    ref_el = float(ref["elevation"].iloc[0])
                    ref_az = float(ref["azimuth"].iloc[0]) - 180.0
                    if ref_el > 5:
                        worst_el = max(worst_el, abs(el - ref_el))
                        diff_az = abs((az - ref_az + 180) % 360 - 180)
                        worst_az = max(worst_az, diff_az)
        ok = worst_el < 2.0 and worst_az < 4.0
        s.hard_ok &= ok
        s.rows.append(("Sun elevation, 36 cases (worst)", "pvlib", "RESize", f"{worst_el:.2f} deg",
                       "ok" if worst_el < 2.0 else "**NO**"))
        s.rows.append(("Sun azimuth, 36 cases (worst)", "pvlib", "RESize", f"{worst_az:.2f} deg",
                       "ok" if worst_az < 4.0 else "**NO**"))
    except Exception as exc:  # noqa: BLE001
        s.notes.append(f"sun-position comparison failed: {exc.__class__.__name__}: {exc}")
    if offline:
        s.notes.append("Real-year comparison not run (offline).")
        return s
    for name, lat, lon in SITES:
        try:
            data = pvlib.iotools.get_pvgis_tmy(lat, lon, map_variables=True)[0]
            sp = pvlib.solarposition.get_solarposition(data.index, lat, lon)
            poa = pvlib.irradiance.get_total_irradiance(
                30, 180 if lat >= 0 else 0, sp["apparent_zenith"], sp["azimuth"],
                data["dni"], data["ghi"], data["dhi"])["poa_global"].fillna(0.0)
            if len(poa) != prof.HOURS:
                raise ValueError(f"typical year has {len(poa)} hours")
            unit = [float(v) / 1000.0 * 0.8 for v in poa]      # kW per kWp, PR 0.8
            yield_kwh = sum(unit)
            months = [0.0] * 12
            for t_i, v in enumerate(unit):
                months[h2.MONTH_OF_HOUR[t_i]] += v
            real = [m / yield_kwh * 100 for m in months]
            mine = [m / yield_kwh * 100 for m in pv_extra.monthly_energy_kwh(lat, yield_kwh)]
            rms = math.sqrt(sum((a - b) ** 2 for a, b in zip(real, mine, strict=True)) / 12)
            s.rows.append((f"{name}: monthly shares of the year", f"pvlib/PVGIS TMY, {yield_kwh:,.0f} kWh/kWp",
                           "RESize invented year", f"RMS {rms:.2f} pts of the year", "info"))
            demand = 4500.0
            kwp = 5.0
            inp = BatteryInputs(annual_demand_kwh=demand, pv_kwp=kwp, mode="given", capacity_kwh=8.0)
            res = {}
            for label, unit_p in (("real", tuple(unit)),
                                  ("invented", prof.synthetic_pv_profile(lat, yield_kwh))):
                res[label] = size_battery(inp, BatteryProfiles(unit_p, None, label))
            s.rows.append((f"{name}: 5 kWp + 8 kWh, self-sufficiency",
                           f"{res['real'].self_sufficiency:.1%} (real year)",
                           f"{res['invented'].self_sufficiency:.1%} (invented)",
                           f"{(res['invented'].self_sufficiency - res['real'].self_sufficiency) * 100:+.1f} pts",
                           "info"))
        except Exception as exc:  # noqa: BLE001
            s.notes.append(f"{name}: real-year comparison failed: {exc.__class__.__name__}: {exc}")
    return s


# ---------------------------------------------------------------- C. biogas
def section_biogas() -> Section:
    s = Section("C. Biogas: substrate yields against Buswell limits",
                "Buswell: carbohydrates give at most 0.373 m3 CH4 per kg of volatile solids, "
                "proteins 0.496, lipids 1.014. A library value above the lipid limit is "
                "impossible; above about 0.6 it would need a fat-rich substrate.",
                ("Substrate", "CH4 m3/t fresh", "VS kg/t fresh", "m3 CH4 per kg VS", "Result"))
    for sub in SUBSTRATES:
        vs = sub.vs_fresh * 1000.0
        y = sub.ch4_m3_per_t / vs
        hard = y <= 1.014
        s.hard_ok &= hard
        flag = "impossible" if not hard else "ok (carbohydrate-like)" if y <= 0.373 else \
            "ok, needs some protein or fat" if y <= 0.6 else "high"
        s.rows.append((sub.name, f"{sub.ch4_m3_per_t:.0f}", f"{vs:.0f}", f"{y:.3f}", flag))
    s.notes.append("Library values are FNR/KTBL handbook figures; the check shows they are "
                   "chemically possible, not that they match your substrate (use a BMP test).")
    return s


# ---------------------------------------------------------------- D. hydrogen
def section_hydrogen() -> Section:
    s = Section("D. Hydrogen: LCOH recomputed by hand",
                "Grid-only 1 MW electrolyser running 8000 h: every cost term written out "
                "separately from the library code.",
                ("Quantity", "By hand", "RESize", "Difference", "Result"))
    inp = HydrogenInputs(mode="plant", use_pv=False, use_wind=False, use_grid=True,
                         electrolyser_kw=1000.0, grid_hours_cap=8000.0, min_load=0.0,
                         storage_days=0.0, stack_hours=80_000.0)
    d = size_hydrogen_plant(inp, HydrogenProfiles(None, None, "none"))
    kwh_total = inp.kwh_per_kg_stack + h2.compression_kwh_per_kg(inp.outlet_bar, inp.storage_bar)
    kwh = 1000.0 * 8000.0
    kg = kwh / kwh_total
    crf = eco.capital_recovery_factor(inp.discount_rate, inp.electrolyser_life_years)
    capex = 1000.0 * inp.electrolyser_capex_per_kw
    annual = (capex * (crf + inp.electrolyser_om_fraction)
              + capex * inp.stack_cost_fraction * 8000.0 / inp.stack_hours
              + kwh * inp.grid_price_per_kwh + kg * inp.water_l_per_kg / 1000 * inp.water_price_per_m3)
    for label, hand, lib in (("Hydrogen per year [kg]", kg, d.hydrogen_kg),
                             ("LCOH [euro/kg]", annual / kg, d.lcoh),
                             ("Carbon [kg CO2/kg H2]", 8000 * 1000 * inp.grid_ef / kg, d.co2_kg_per_kg)):
        ok = math.isclose(hand, lib, rel_tol=1e-6)
        s.hard_ok &= ok
        s.rows.append((label, f"{hand:.4f}", f"{lib:.4f}", f"{(lib - hand):+.2e}",
                       "match" if ok else "**NO**"))
    res = size_hydrogen_plant(
        HydrogenInputs(h2_demand_kg_per_year=100_000.0),
        HydrogenProfiles(prof.synthetic_pv_profile(40.0, 1500.0), None, "synthetic"))
    s.notes.append(f"Plausibility: a 100 t/year PV-fed plant gives {res.lcoh:.1f} euro/kg and "
                   f"{res.full_load_hours:,.0f} full-load hours. Published estimates for "
                   "renewable hydrogen in good European sites are roughly 3-8 euro/kg "
                   "(IEA Global Hydrogen Review; IRENA 2020; check the latest edition). "
                   "A solar-only plant sits at the high end because the electrolyser runs few hours.")
    return s


# ---------------------------------------------------------------- E. battery
def _plain_dispatch(gen, load, cap, power, eta_rt, dod, health, soc0):
    """A second, differently written dispatch (state of charge as a fraction)."""
    usable = cap * dod * health
    eta = math.sqrt(eta_rt)
    soc = soc0
    imp = exp = 0.0
    for g, d in zip(gen, load, strict=True):
        if usable <= 0:
            imp += max(d - g, 0.0)
            exp += max(g - d, 0.0)
            continue
        if g >= d:
            room = (1.0 - soc) * usable
            charge = min(g - d, power, room / eta)
            soc += charge * eta / usable
            exp += g - d - charge
        else:
            have = soc * usable
            out = min(d - g, power, have * eta)
            soc -= out / eta / usable
            imp += d - g - out
    return imp, exp


def section_battery() -> Section:
    s = Section("E. Battery: second implementation of the dispatch",
                "The yearly import and export of the library against a separately written "
                "loop, for several sizes (must agree to rounding).",
                ("Case", "Import ref [kWh]", "Import RESize", "Export difference", "Result"))
    gen = [5.0 * u for u in prof.synthetic_pv_profile(45.0, 1300.0)]
    load = bat.load_profile(6000.0, "residential")
    for cap in (0.0, 4.0, 8.0, 16.0):
        power = cap * 0.5
        imp, exp = _plain_dispatch(gen, load, cap, power, 0.90, 0.90, 0.90, 0.5)
        run = bat.simulate_battery(gen, load, cap, power, 0.90, 0.90, 0.90, 0.5)
        ok = math.isclose(imp, run.import_kwh, rel_tol=1e-9, abs_tol=1e-6) and \
            math.isclose(exp, run.export_kwh, rel_tol=1e-9, abs_tol=1e-6)
        s.hard_ok &= ok
        s.rows.append((f"5 kWp, 6000 kWh, {cap:g} kWh", f"{imp:,.1f}", f"{run.import_kwh:,.1f}",
                       f"{run.export_kwh - exp:+.2e}", "match" if ok else "**NO**"))
    d = size_battery(BatteryInputs(mode="given", capacity_kwh=8.0),
                     BatteryProfiles(prof.synthetic_pv_profile(45.0, 1300.0), None, "synthetic"))
    s.notes.append(f"Plausibility: 5 kWp + 8 kWh for 6000 kWh/year gives self-sufficiency "
                   f"{d.self_sufficiency_without:.0%} -> {d.self_sufficiency:.0%}. Studies of "
                   "residential PV-battery systems (Weniger et al. 2014; HTW Berlin storage "
                   "inspections) report about 55-75 % with a battery of 1 kWh per MWh and a "
                   "similar PV size.")
    return s


# ---------------------------------------------------------------- F. economics
def section_economics() -> Section:
    s = Section("F. Economics: cost of electricity against published averages",
                "Default costs (PV 1000 euro/kWp, wind 1500 euro/kW, 5 % discount, 25 years).",
                ("Technology", "RESize LCOE [euro/kWh]", "Published global average", "Comment"))
    inp = ComparisonInputs(1500.0, 0.8, WindInputs(annual_demand_kwh=1e7, mean_speed_ref_ms=6.5))
    r = compare_technologies(inp)
    s.rows.append(("Solar PV", f"{r.pv.lcoe_eur_per_kwh:.3f}", "about 0.04-0.05 USD/kWh (IRENA 2023)",
                   "Europe is dearer than the global mean; sunny sites get close to it"))
    s.rows.append(("Onshore wind", f"{r.wind.lcoe_eur_per_kwh:.3f}", "about 0.03-0.04 USD/kWh (IRENA 2023)",
                   "Depends mostly on the wind speed; 6.5 m/s at 50 m here"))
    s.notes.append("Averages quoted from memory of the IRENA Renewable Power Generation Costs "
                   "reports: check the latest edition before citing them.")
    return s


# ---------------------------------------------------------------- G. solar thermal
def _plain_hot_water(w, area, c, litres, ua, loop, lpd, t_use, t_mean, amp):
    """Second, deliberately plain implementation of the hot-water loop (no chiller)."""
    cap = litres * 0.001163
    t = max(20.0, t_mean)
    col = sol = dem = 0.0
    for h in range(8760):
        day, hour = divmod(h, 24)
        g, ta = w.g_w_m2[h], w.t_amb_c[h]
        if g > 0:
            eta = max(0.0, c.eta0 - c.a1 * (t + 3.0 - ta) / g - c.a2 * (t + 3.0 - ta) ** 2 / g)
            q = eta * g * area / 1000.0 * (1 - loop)
            t += q / cap
            col += q
        if t > 95.0:
            col -= (t - 95.0) * cap
            t = 95.0
        mains = max(4.0, t_mean - 0.5 * amp * math.cos(2 * math.pi * (day - 50) / 365))
        need = lpd * stm.DAILY_DRAW_SHAPE[hour] / sum(stm.DAILY_DRAW_SHAPE) * 0.001163 * max(
            0.0, t_use - mains)
        if need > 0:
            share = min(1.0, max(0.0, (t - mains) / (t_use - mains)))
            t -= need * share / cap
            sol += need * share
            dem += need
        loss = ua * max(0.0, t - 18.0) / 1000.0
        t = max(4.0, t - loss / cap)
    return col, sol, dem


def _fchart(inp, area, run, w):
    """Annual solar fraction of a hot-water system by the f-chart method (Klein, 1976)."""
    c = stm.COLLECTORS[inp.collector]
    days = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    start = 0
    total_f = total_l = 0.0
    for m, n in enumerate(days):
        hours = range(start * 24, (start + n) * 24)
        h_t = sum(w.g_w_m2[i] for i in hours) / 1000.0
        ta = sum(w.t_amb_c[i] for i in hours) / len(hours)
        mains = sum(stm.mains_temperature(d, inp.t_mean_c, inp.t_season_amp_c)
                    for d in range(start, start + n)) / n
        load = run.monthly_heat_demand_kwh[m]
        frul = c.a1 + c.a2 * 30.0
        frta = c.eta0 * (1 - inp.loop_loss)
        xc = (11.6 + 1.18 * inp.t_use_c + 3.86 * mains - 2.32 * ta) / (100.0 - ta)
        x = area * frul * (100.0 - ta) * 24.0 * n / 1000.0 / load * xc
        y = area * frta * h_t / load * (inp.store_l_per_m2 / 75.0) ** -0.25
        f = 1.029 * y - 0.065 * x - 0.245 * y * y + 0.0018 * x * x + 0.0215 * y ** 3
        f = min(1.0, max(0.0, f))
        total_f += f * load
        total_l += load
        start += n
    return total_f / total_l


def section_solar() -> Section:
    s = Section("G. Solar thermal: second implementation, f-chart and plausibility",
                "Hot water, flat plate, 200 L/day at 55 degC, 4 m2 and 240 L of tank, "
                "synthetic year of 1,400 kWh/m2 at latitude 45.",
                ("Check", "RESize", "Reference", "Result"))
    inp = SolarThermalInputs()
    d = size_solar_thermal(inp, with_sweep=False, with_sensitivity=False)
    w = stm.synthetic_weather(inp.latitude_deg, inp.irradiation_kwh_m2, inp.t_mean_c,
                              inp.t_season_amp_c)
    sysm = stm.SolarSystem(
        area_m2=inp.area_m2, collector=stm.COLLECTORS["flat"], store_litres=d.store_litres,
        store_ua_w_k=0.16 * math.sqrt(d.store_litres), dhw_litres_per_day=inp.dhw_litres_per_day,
        flow_delta_t_c=6.0)
    run = stm.simulate(sysm, w, inp.t_mean_c, inp.t_season_amp_c)
    col, sol, dem = _plain_hot_water(w, inp.area_m2, stm.COLLECTORS["flat"], d.store_litres,
                                     0.16 * math.sqrt(d.store_litres), inp.loop_loss,
                                     inp.dhw_litres_per_day, inp.t_use_c, inp.t_mean_c,
                                     inp.t_season_amp_c)
    ok = (abs(run.heat_solar_kwh - sol) < 1e-6 * max(1.0, sol)
          and abs(run.collector_kwh - col) < 1e-6 * max(1.0, col)
          and abs(run.heat_demand_kwh - dem) < 1e-6 * max(1.0, dem))
    s.hard_ok &= ok
    s.rows.append(("Hot water delivered by the sun [kWh]", f"{run.heat_solar_kwh:,.1f}",
                   f"{sol:,.1f} (plain loop)", "match" if ok else "MISMATCH"))
    s.rows.append(("Collector heat [kWh]", f"{run.collector_kwh:,.1f}", f"{col:,.1f}",
                   "match" if ok else "MISMATCH"))
    f_chart = _fchart(inp, inp.area_m2, run, w)
    s.rows.append(("Annual solar fraction", f"{run.heat_fraction:.2f}", f"{f_chart:.2f} (f-chart)",
                   f"info: difference {run.heat_fraction - f_chart:+.2f}"))
    s.rows.append(("Collector yield [kWh/m2 per year]", f"{run.heat_solar_kwh / inp.area_m2:,.0f}",
                   "about 350-600 for DHW in central Europe", "info"))
    cool = size_solar_thermal(SolarThermalInputs(
        dhw_litres_per_day=0, cooling_kwh_per_year=12000, collector="tube", latitude_deg=38,
        irradiation_kwh_m2=1750, t_mean_c=17, area_m2=30), with_sweep=False,
        with_sensitivity=False)
    cop = (cool.run.cooling_solar_kwh / cool.run.chiller_heat_kwh
           if cool.run.chiller_heat_kwh else 0.0)
    s.rows.append(("Mean thermal COP of the adsorption chiller", f"{cop:.2f}",
                   "0.3-0.6 for silica-gel machines driven by solar heat", "info"))
    s.notes.append("The f-chart is a correlation for monthly averages and a stratified tank; "
                   "RESize uses an hourly balance and one mixed tank, which is the more "
                   "conservative choice (a mixed tank gives a lower fraction). A difference of "
                   "a few points is expected; a large one would deserve a look.")
    s.notes.append("Yield and COP ranges are order-of-magnitude values quoted from memory "
                   "(IEA SHC Solar Heat Worldwide, Henning 2010, manufacturer datasheets): "
                   "check them before citing.")
    return s


def render(sections: list[Section]) -> list[str]:
    out = ["# Cross-checks of all technologies", "",
           "Generated by `validation/validate_cross.py`. Rows marked *match* are independent "
           "recomputations that must agree to rounding. Rows marked *info* compare RESize with "
           "another tool or with published ranges: they show how far a simplified, educational "
           "model is from the reference.", ""]
    for s in sections:
        out += [f"## {s.title}", "", s.intro, ""] + md_table(s.header, s.rows)
        out += [f"- {n}" for n in s.notes] + ([""] if s.notes else [])
    out += ["## Limits", "",
            "- No comparison with measured production, WAsP, WindPRO, PVsyst or HOMER (commercial).",
            "- Published ranges are approximate and quoted from memory of the sources named.",
            "- See DISCLAIMER.md: results are preliminary-design quality.", ""]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--out", default="docs/validation/cross.md")
    args = ap.parse_args()
    sections = [section_wind(args.offline), section_pv(args.offline), section_biogas(),
                section_hydrogen(), section_battery(), section_economics(),
                section_solar()]
    lines = render(sections)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0 if all(s.hard_ok for s in sections) else 1


if __name__ == "__main__":
    sys.exit(main())
