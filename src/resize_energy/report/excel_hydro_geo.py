"""Excel workbooks with live formulas for hydropower and geothermal designs.

Qt-free; builds on the helpers of :mod:`resize_energy.report.excel`.

* Hydropower: the flow-duration curve, the penstock head loss at every flow and the energy
  integral are rebuilt as a table of 400 rows ('Curve'), as in the program. The type of turbine
  and the generator efficiency (which depends on the size) are inputs taken from RESize.
* Geothermal: everything is formulas. For heat, the share of the demand covered by a plant of a
  given size is solved with a bisection table, as in the biomass workbook.
"""

from __future__ import annotations

import math

from openpyxl import Workbook

from resize_energy.core.geothermal_design import GeothermalDesign, GeothermalInputs
from resize_energy.core.hydro import HOURS_PER_YEAR
from resize_energy.core.hydro_design import STEPS, HydroDesign, HydroInputs
from resize_energy.report.excel import _COMMON_ABOUT, _about, _Book
from resize_energy.report.excel_more import _table_header, _title


def _economics(book: _Book, ws, d, inputs_note: str = "") -> None:
    """Rows shared by both workbooks: needs capex, om_per_year, net_benefit, energy names."""
    p = book.put
    p(ws, "crf", "Capital recovery factor",
      "=IF(rate=0,1/life,rate*(1+rate)^life/((1+rate)^life-1))", "1/year",
      "CRF = r(1+r)^n / ((1+r)^n - 1)", "0.0000")
    p(ws, "annuity", "Annuity factor", "=1/crf", "years",
      "Present value of 1 euro per year over the lifetime.", "0.000")
    p(ws, "payback_y", "Simple payback",
      '=IF(net_benefit>0,capex/net_benefit,"never")', "years", "CAPEX / net benefit", "0.0",
      check=d.payback_years if math.isfinite(d.payback_years) else None)
    p(ws, "npv_euro", "Net present value", "=-capex+net_benefit*annuity", "euro",
      "NPV = -CAPEX + net benefit x annuity factor", "#,##0", check=d.npv)


# --- hydropower ----------------------------------------------------------------------------
def build_hydro_workbook(inp: HydroInputs, d: HydroDesign) -> Workbook:
    book = _Book()
    p = book.put
    _about(book, "RESize - run-of-river hydropower design as a spreadsheet", _COMMON_ABOUT + [
        f"Reproduced: the log-normal flow-duration curve, the design flow, the penstock, the "
        f"head loss and the power at each of {STEPS} equal slices of the year ('Curve' sheet), "
        "the yearly energy and the economics.",
        "Taken from RESize as inputs: the type of turbine and its best efficiency and lowest "
        "flow, and the generator efficiency (a table of the ESHA Guide that depends on the "
        "size). If you change the head or the flow a lot, check them.",
    ])
    ws = book.sheet("Inputs")
    _title(ws, "Inputs (yellow cells can be changed)")
    book.heading(ws, "River and site")
    p(ws, "head", "Gross head", inp.gross_head_m, "m", "", "0.0", True)
    p(ws, "q_mean", "Mean flow", inp.mean_flow_m3s, "m3/s", "", "0.000", True)
    p(ws, "q_low", "Q95: flow exceeded 95 % of the time", inp.q95_m3s, "m3/s", "", "0.000", True)
    p(ws, "q_eco", "Environmental flow", inp.eco_flow_m3s, "m3/s", "", "0.000", True)
    p(ws, "p_design", "Design flow exceeded this share of the time", inp.design_exceedance, "-",
      "", "0.00", True)
    p(ws, "demand", "Annual electricity demand", inp.annual_demand_kwh, "kWh/year",
      "0: everything is sold", "#,##0", True)
    book.heading(ws, "Penstock")
    p(ws, "pen_len", "Length", inp.penstock_length_m, "m", "", "0", True)
    p(ws, "vel_design", "Design velocity", inp.penstock_velocity_ms, "m/s",
      "Chooses the diameter when it is 0 below", "0.0", True)
    p(ws, "diam_in", "Diameter (0: from the velocity)", inp.penstock_diameter_m, "m", "",
      "0.00", True)
    p(ws, "rough_mm", "Roughness", inp.roughness_mm, "mm", "", "0.00", True)
    p(ws, "k_local", "Local losses, sum of K", inp.local_loss_k, "-", "", "0.0", True)
    book.heading(ws, "Turbine and generator (from RESize)")
    p(ws, "turbine_name", "Turbine", d.turbine_name, "", "Chosen from head and flow", None)
    p(ws, "eta_t", "Turbine efficiency", d.turbine_eff, "-", "", "0.000", True)
    p(ws, "eta_g", "Generator efficiency", d.generator_eff, "-", "", "0.000", True)
    p(ws, "min_frac", "Lowest working flow / design flow",
      d.min_flow_m3s / d.design_flow_m3s, "-", "", "0.00", True)
    p(ws, "losses", "Outages and part-load losses", inp.operating_losses, "-",
      "Share of the energy", "0.00", True)
    book.heading(ws, "Costs and prices")
    p(ws, "capex_kw", "Installed cost", inp.capex_per_kw, "euro/kW", "", "#,##0", True)
    p(ws, "om_frac", "O&M per year", inp.om_fraction, "-", "Share of the CAPEX", "0.000", True)
    p(ws, "life", "Life", inp.life_years, "years", "", "0", True)
    p(ws, "rate", "Discount rate", inp.discount_rate, "-", "", "0.000", True)
    p(ws, "retail", "Price you pay", inp.retail_price, "euro/kWh", "", "0.000", True)
    p(ws, "export", "Price for the energy you sell", inp.export_price, "euro/kWh", "", "0.000",
      True)
    p(ws, "grid_ef", "Emission factor of the grid", inp.grid_ef, "kg CO2/kWh", "", "0.000", True)
    p(ws, "lifecycle", "Life-cycle emissions of the plant", inp.lifecycle_g_per_kwh,
      "g CO2/kWh", "", "0", True)

    c = book.sheet("Calculation")
    _title(c, "Calculation (every cell is a formula)")
    book.heading(c, "1. Flow-duration curve and design flow")
    p(c, "sigma", "Sigma of ln Q", "=-1.6449+SQRT(1.6449^2+2*LN(q_mean/q_low))", "-",
      "sigma = -1.645 + sqrt(1.645^2 + 2 ln(Qmean/Q95))", "0.0000", check=d.sigma)
    p(c, "mu", "Mu of ln Q", "=LN(q_mean)-sigma^2/2", "-", "", "0.0000", check=d.mu)
    p(c, "q_river_d", "River flow at the design exceedance",
      "=EXP(mu+sigma*NORMSINV(1-p_design))", "m3/s", "", "0.000",
      check=d.river_flow_at_design_m3s)
    p(c, "q_design", "Design flow of the turbine", "=q_river_d-q_eco", "m3/s",
      "River flow minus the environmental flow", "0.000", check=d.design_flow_m3s)
    p(c, "q_min", "Lowest working flow", "=min_frac*q_design", "m3/s", "", "0.000",
      check=d.min_flow_m3s)
    book.heading(c, "2. Penstock at the design flow")
    p(c, "diam", "Diameter", "=IF(diam_in>0,diam_in,SQRT(4*q_design/(PI()*vel_design)))", "m",
      "D = sqrt(4 Q / (pi v))", "0.000", check=d.penstock_diameter_m)
    p(c, "area", "Cross-section", "=PI()*diam^2/4", "m2", "", "0.0000")
    p(c, "vel", "Velocity", "=q_design/area", "m/s", "", "0.00", check=d.velocity_ms)
    p(c, "reynolds", "Reynolds number", "=vel*diam/0.000001", "-", "", "#,##0")
    p(c, "friction", "Friction factor (Swamee-Jain)",
      "=IF(reynolds<2300,64/reynolds,0.25/LOG10(rough_mm/1000/diam/3.7+5.74/reynolds^0.9)^2)",
      "-", "", "0.0000")
    p(c, "h_loss", "Head loss", "=(friction*pen_len/diam+k_local)*vel^2/(2*9.81)", "m",
      "(f L / D + K) v^2 / 2g", "0.000", check=d.head_loss_m)
    p(c, "h_net", "Net head", "=head-h_loss", "m", "", "0.000", check=d.net_head_m)
    book.heading(c, "3. Power and energy")
    p(c, "p_hyd", "Hydraulic power", "=9.81*q_design*h_net", "kW", "P = rho g Q H", "#,##0.0")
    p(c, "rated", "Rated electric power", "=p_hyd*eta_t*eta_g", "kW", "", "#,##0.0",
      check=d.rated_kw)
    p(c, "dt", "Hours of each slice of the year", f"={HOURS_PER_YEAR:g}/{STEPS}", "h", "",
      "0.0000")
    p(c, "energy", "Energy per year", "=SUM(Curve!I2:I401)*dt*(1-losses)", "kWh/year",
      "Sum over the curve, minus the operating losses", "#,##0", check=d.energy_kwh)
    p(c, "flh", "Full-load hours", "=energy/rated", "h/year", "", "#,##0",
      check=d.full_load_hours)
    p(c, "cf", "Capacity factor", f"=energy/(rated*{HOURS_PER_YEAR:g})", "-", "", "0.000",
      check=d.capacity_factor)
    p(c, "hours_w", "Hours the turbine works", '=COUNTIF(Curve!D2:D401,">0")*dt', "h/year",
      "", "#,##0", check=d.hours_working)
    p(c, "water_used", "Share of the river's water used", "=SUM(Curve!D2:D401)/SUM(Curve!B2:B401)",
      "-", "", "0.000", check=d.water_used_fraction)
    book.heading(c, "4. Economics")
    p(c, "capex", "Plant cost (CAPEX)", "=rated*capex_kw", "euro", "", "#,##0", check=d.capex)
    p(c, "om_per_year", "O&M per year", "=capex*om_frac", "euro/year", "", "#,##0",
      check=d.om_per_year)
    p(c, "savings", "Value of the energy per year",
      "=MIN(energy,demand)*retail+MAX(0,energy-demand)*export", "euro/year", "", "#,##0",
      check=d.savings_per_year)
    p(c, "net_benefit", "Net benefit per year", "=savings-om_per_year", "euro/year", "",
      "#,##0")
    _economics(book, c, d)
    p(c, "lcoe", "Levelised cost of energy", "=(capex*crf+om_per_year)/energy", "euro/kWh",
      "LCOE = (CAPEX x CRF + O&M) / yearly energy", "0.0000", check=d.lcoe)
    p(c, "co2", "CO2 avoided per year", "=energy*(grid_ef-lifecycle/1000)/1000", "t CO2/year",
      "", "#,##0.0", check=d.co2_avoided_t_per_year)

    cv = book.sheet("Curve", (12, 14, 14, 14, 12, 14, 12, 12, 14))
    _table_header(cv, ["Exceedance", "River flow", "Available", "Turbine flow", "Velocity",
                       "Reynolds", "Friction", "Head loss", "Power [kW]"])
    for r in range(2, STEPS + 2):
        cv.append([
            f"=(ROW()-1.5)/{STEPS}",
            f"=EXP(mu+sigma*NORMSINV(1-A{r}))",
            f"=MAX(B{r}-q_eco,0)",
            f"=IF(MIN(C{r},q_design)<q_min,0,MIN(C{r},q_design))",
            f"=IF(D{r}>0,D{r}/area,0)",
            f"=IF(D{r}>0,E{r}*diam/0.000001,0)",
            f"=IF(D{r}>0,IF(F{r}<2300,64/F{r},0.25/LOG10(rough_mm/1000/diam/3.7"
            f"+5.74/F{r}^0.9)^2),0)",
            f"=IF(D{r}>0,(G{r}*pen_len/diam+k_local)*E{r}^2/(2*9.81),0)",
            f"=IF(D{r}>0,9.81*D{r}*(head-H{r})*eta_t*eta_g,0)",
        ])
    cv.freeze_panes = "A2"
    book.finish_checks()
    return book.wb


# --- geothermal ----------------------------------------------------------------------------
def build_geothermal_workbook(inp: GeothermalInputs, d: GeothermalDesign) -> Workbook:
    book = _Book()
    p = book.put
    heat = d.pathway == "heat"
    _about(book, "RESize - geothermal design as a spreadsheet", _COMMON_ABOUT + [
        "Everything is reproduced: heat from the brine, number of well pairs, depth, pumping, "
        + ("share of the heat covered (sheet 'Coverage': a bisection, one row per step), "
           if heat else "gross and net power of the binary or flash plant, ")
        + "economics and emissions.",
        "Not reproduced: the choice between binary and flash for 'auto' (the plant type is an "
        "input taken from RESize).",
    ])
    ws = book.sheet("Inputs")
    _title(ws, "Inputs (yellow cells can be changed)")
    book.heading(ws, "Resource and wells")
    p(ws, "t_res", "Temperature of the water at the wellhead", inp.reservoir_temp_c, "degC", "",
      "0.0", True)
    p(ws, "flow", "Flow of one production well", inp.flow_per_well_kg_s, "kg/s", "", "0.0", True)
    p(ws, "t_amb", "Mean ambient temperature", inp.ambient_temp_c, "degC", "", "0.0", True)
    p(ws, "gradient", "Temperature gradient", inp.gradient_k_per_km, "degC/km", "", "0.0", True)
    p(ws, "pump_bar", "Pressure rise of the pumps, per well pair", inp.pump_pressure_bar, "bar",
      "", "0.0", True)
    p(ws, "pump_eff", "Pump efficiency", inp.pump_efficiency, "-", "", "0.00", True)
    p(ws, "avail", "Availability", inp.availability, "-", "", "0.00", True)
    if heat:
        book.heading(ws, "Heat demand and network")
        p(ws, "q_heat", "Annual heat demand", inp.annual_heat_demand_kwh, "kWh/year", "",
          "#,##0", True)
        p(ws, "peak_kw", "Peak heat load", inp.peak_heat_kw, "kW", "", "#,##0", True)
        p(ws, "coverage", "Share of the heat to cover", inp.coverage, "-", "", "0.00", True)
        p(ws, "t_ret", "Return temperature", inp.return_temp_c, "degC", "", "0.0", True)
        p(ws, "hx_eff", "Exchanger and network efficiency", inp.exchanger_efficiency, "-", "",
          "0.00", True)
        book.heading(ws, "Costs, prices and emissions")
        p(ws, "drill", "Drilling, one well", inp.drilling_eur_per_m, "euro/m", "", "#,##0", True)
        p(ws, "surface", "Surface equipment", inp.surface_eur_per_kw_th, "euro/kW heat", "",
          "#,##0", True)
        p(ws, "heat_price", "Value of the heat replaced", inp.heat_price_eur_per_kwh,
          "euro/kWh", "", "0.000", True)
        p(ws, "ref_eff", "Efficiency of the boiler replaced", inp.reference_heat_efficiency, "-",
          "", "0.00", True)
        p(ws, "ref_ef", "Emission factor of its fuel", inp.reference_heat_ef, "kg CO2/kWh", "",
          "0.000", True)
    else:
        book.heading(ws, "Electricity demand and plant")
        p(ws, "e_dem", "Annual electricity demand", inp.annual_electricity_demand_kwh,
          "kWh/year", "", "#,##0", True)
        p(ws, "coverage", "Share of the demand to cover", inp.coverage, "-", "", "0.00", True)
        p(ws, "plant_kind", "Plant type (binary or flash)", d.plant, "", "From RESize", None)
        p(ws, "t_reinj", "Temperature of the water reinjected", inp.reinjection_temp_c, "degC",
          "Binary plants", "0.0", True)
        p(ws, "flash_u", "Flash plant: utilization efficiency", inp.flash_utilization, "-", "",
          "0.00", True)
        p(ws, "flash_par", "Flash plant: own consumption", inp.flash_parasitic, "-", "",
          "0.00", True)
        p(ws, "hours", "Operating hours", inp.operating_hours, "h/year", "", "#,##0", True)
        book.heading(ws, "Costs, prices and emissions")
        p(ws, "capex_kw_el", "Installed cost, wells included", inp.capex_per_kw_el, "euro/kW net",
          "", "#,##0", True)
        p(ws, "retail", "Price you pay for electricity", inp.retail_price, "euro/kWh", "",
          "0.000", True)
        p(ws, "export", "Price for the energy you sell", inp.export_price, "euro/kWh", "",
          "0.000", True)
        p(ws, "lifecycle", "Life-cycle emissions of the plant", inp.lifecycle_g_per_kwh,
          "g CO2/kWh", "", "0", True)
    p(ws, "om_frac", "O&M per year", inp.om_fraction, "-", "Share of the CAPEX", "0.000", True)
    p(ws, "life", "Life", inp.life_years, "years", "", "0", True)
    p(ws, "rate", "Discount rate", inp.discount_rate, "-", "", "0.000", True)
    if heat:
        p(ws, "retail", "Price you pay for electricity (pumps)", inp.retail_price, "euro/kWh",
          "", "0.000", True)
    p(ws, "grid_ef", "Emission factor of the grid", inp.grid_ef, "kg CO2/kWh", "", "0.000", True)

    c = book.sheet("Calculation")
    _title(c, "Calculation (every cell is a formula)")
    book.heading(c, "1. Wells")
    p(c, "depth", "Depth of the wells", "=(t_res-t_amb)/gradient*1000", "m",
      "z = (T - T_surface) / gradient", "#,##0", check=d.depth_m)
    p(c, "pump_kw", "Pumping power per well pair", "=flow/1000*pump_bar*100/pump_eff", "kW",
      "V dp / eta", "#,##0.0")
    if heat:
        book.heading(c, "2. Heat and wells needed")
        p(c, "load_factor", "Load factor of the heat demand", "=q_heat/(peak_kw*8760)", "-", "",
          "0.0000", check=d.load_factor)
        p(c, "n_exp", "Exponent of the load-duration curve", "=1/load_factor-1", "-",
          "P(t) = P_peak x (1 - t/T)^n", "0.0000")
        p(c, "ratio_target", "Plant power / peak load needed",
          "=IF(coverage>=1,1,(Coverage!A82+Coverage!B82)/2)", "-",
          "Found on the 'Coverage' sheet.", "0.0000")
        p(c, "p_pair", "Useful heat of one well pair", "=flow*4.18*(t_res-t_ret)*hx_eff", "kW",
          "P = m cp (T_prod - T_return) eta", "#,##0.0", check=d.heat_per_pair_kw)
        p(c, "pairs", "Well pairs", "=MAX(1,ROUNDUP(ratio_target*peak_kw/p_pair-0.000000001,0))",
          "", "Whole pairs, rounded up", "0", check=d.wells_pairs)
        p(c, "ratio", "Plant power / peak load", "=MIN(1,pairs*p_pair/peak_kw)", "-", "",
          "0.0000", check=d.power_ratio)
        p(c, "covered", "Share of the heat covered",
          "=IF(n_exp<0.000000001,ratio,(n_exp+1)*ratio-n_exp*ratio^((n_exp+1)/n_exp))", "-",
          "f(x) = (n + 1) x - n x^((n + 1) / n)", "0.0000")
        p(c, "heat_kwh", "Heat delivered", "=covered*q_heat*avail", "kWh/year", "", "#,##0",
          check=d.heat_kwh)
        p(c, "coverage_real", "Coverage of the demand", "=heat_kwh/q_heat", "-", "", "0.000",
          check=d.coverage)
        p(c, "th_power", "Heat taken from the brine, all wells", "=pairs*flow*4.18*(t_res-t_ret)",
          "kW", "", "#,##0", check=d.thermal_power_kw)
        p(c, "full_hours", "Full-load hours", "=heat_kwh/(pairs*p_pair)", "h/year", "",
          "#,##0", check=d.full_load_hours)
        p(c, "pump_kwh", "Pumping electricity", "=pairs*pump_kw*full_hours", "kWh/year", "",
          "#,##0")
        p(c, "spf", "Seasonal performance factor", "=heat_kwh/pump_kwh", "-",
          "Heat delivered / pumping electricity", "0.0", check=d.spf)
        book.heading(c, "3. Economics and emissions")
        p(c, "capex", "Plant cost (CAPEX)", "=pairs*2*depth*drill+pairs*p_pair*surface", "euro",
          "Two wells per pair plus surface equipment", "#,##0", check=d.capex)
        p(c, "om_per_year", "O&M per year", "=capex*om_frac", "euro/year", "", "#,##0",
          check=d.om_per_year)
        p(c, "pump_cost", "Cost of the pumping electricity", "=pump_kwh*retail", "euro/year", "",
          "#,##0")
        p(c, "net_benefit", "Net benefit per year", "=heat_kwh*heat_price-pump_cost-om_per_year",
          "euro/year", "", "#,##0")
        p(c, "savings", "Value of the heat per year", "=net_benefit+om_per_year", "euro/year",
          "", "#,##0", check=d.savings_per_year)
        _economics(book, c, d)
        p(c, "lcoe", "Levelised cost of the heat", "=(capex*crf+om_per_year+pump_cost)/heat_kwh",
          "euro/kWh", "", "0.0000", check=d.lcoe)
        p(c, "co2", "CO2 avoided per year",
          "=(heat_kwh/ref_eff*ref_ef-pump_kwh*grid_ef)/1000", "t CO2/year", "", "#,##0.0",
          check=d.co2_avoided_t_per_year)
        cov = book.sheet("Coverage", (14, 14, 14, 16))
        _table_header(cov, ["Low", "High", "Trial ratio", "Heat covered by the trial ratio"])
        for i in range(81):
            r = i + 2
            if i == 0:
                lo, hi = 0, 1
            else:
                lo = f"=IF(D{r - 1}<coverage,C{r - 1},A{r - 1})"
                hi = f"=IF(D{r - 1}<coverage,B{r - 1},C{r - 1})"
            cov.append([lo, hi, f"=(A{r}+B{r})/2",
                        f"=IF(n_exp<1E-9,C{r},(n_exp+1)*C{r}-n_exp*C{r}^((n_exp+1)/n_exp))"])
        cov.append([])
        cov.append(["Bisection: each row halves the interval that contains the plant size "
                    "giving the requested coverage."])
    else:
        book.heading(c, "2. Plant")
        p(c, "t_k", "Brine temperature", "=t_res+273.15", "K", "", "0.00")
        p(c, "t0_k", "Ambient temperature", "=t_amb+273.15", "K", "", "0.00")
        p(c, "exergy", "Exergy of the brine", "=4.18*((t_k-t0_k)-t0_k*LN(t_k/t0_k))", "kJ/kg",
          "e = cp ((T - T0) - T0 ln(T / T0))", "0.0", check=d.exergy_kj_per_kg)
        p(c, "eff", "Efficiency",
          '=IF(plant_kind="binary",MAX(0,(0.09345*t_res-2.32657)/100),flash_u)', "-",
          "Binary: MIT fit; flash: utilization efficiency", "0.0000", check=d.efficiency)
        p(c, "gross_pair", "Gross power of one well pair",
          '=IF(plant_kind="binary",eff*flow*4.18*(t_res-t_reinj),eff*flow*exergy)', "kW", "",
          "#,##0.0")
        p(c, "own_pair", "Plant's own consumption, per pair",
          '=IF(plant_kind="binary",0,flash_par*gross_pair)', "kW", "", "#,##0.0")
        p(c, "net_pair", "Net power of one well pair", "=gross_pair-own_pair-pump_kw", "kW",
          "Gross - plant use - pumps", "#,##0.0")
        book.heading(c, "3. Number of wells and energy")
        p(c, "target_kw", "Net power needed", "=coverage*e_dem/hours", "kW", "", "#,##0.0")
        p(c, "pairs", "Well pairs", "=MAX(1,ROUNDUP(target_kw/net_pair-0.000000001,0))", "",
          "Whole pairs, rounded up", "0", check=d.wells_pairs)
        p(c, "gross", "Gross power", "=pairs*gross_pair", "kW", "", "#,##0.0", check=d.gross_kw)
        p(c, "pumps", "Pump power", "=pairs*pump_kw", "kW", "", "#,##0.0", check=d.pumps_kw)
        p(c, "net", "Net power", "=pairs*net_pair", "kW", "", "#,##0.0", check=d.net_kw)
        p(c, "energy", "Net electricity per year", "=net*hours", "kWh/year", "", "#,##0",
          check=d.electricity_kwh)
        p(c, "coverage_real", "Coverage of the demand", "=energy/e_dem", "-", "", "0.000",
          check=d.coverage)
        p(c, "th_power", "Heat taken from the brine, all wells",
          "=pairs*flow*4.18*(t_res-MIN(t_reinj,t_res))", "kW", "", "#,##0",
          check=d.thermal_power_kw)
        book.heading(c, "4. Economics and emissions")
        p(c, "capex", "Plant cost (CAPEX)", "=net*capex_kw_el", "euro", "", "#,##0",
          check=d.capex)
        p(c, "om_per_year", "O&M per year", "=capex*om_frac", "euro/year", "", "#,##0",
          check=d.om_per_year)
        p(c, "savings", "Value of the energy per year",
          "=MIN(energy,e_dem)*retail+MAX(0,energy-e_dem)*export", "euro/year", "", "#,##0",
          check=d.savings_per_year)
        p(c, "net_benefit", "Net benefit per year", "=savings-om_per_year", "euro/year", "",
          "#,##0")
        _economics(book, c, d)
        p(c, "lcoe", "Levelised cost of energy", "=(capex*crf+om_per_year)/energy", "euro/kWh",
          "", "0.0000", check=d.lcoe)
        p(c, "co2", "CO2 avoided per year", "=energy*(grid_ef-lifecycle/1000)/1000",
          "t CO2/year", "", "#,##0.0", check=d.co2_avoided_t_per_year)
    book.finish_checks()
    return book.wb
