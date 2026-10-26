"""The literature behind the formulas and the typical values (no Qt needed).

Every entry is a real publication, standard or dataset. ``tools/check_references.py`` asks
Crossref about the entries that have a DOI, so a wrong year, title or DOI is caught. Standards
and reports change edition: check the current one before you cite it in your own work.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class Ref:
    short: str            # how it is cited in the text: "Duffie & Beckman (2013)"
    authors: str          # full author list or organisation
    year: str
    title: str
    container: str = ""   # journal, publisher or series
    detail: str = ""      # volume(issue):pages, or edition
    doi: str = ""
    url: str = ""
    kind: str = "article"  # article, book, standard, report, dataset


def _r(short, authors, year, title, container="", detail="", doi="", url="", kind="article"):
    return Ref(short, authors, year, title, container, detail, doi, url, kind)


REFS: dict[str, Ref] = {
    # --- solar and photovoltaics --------------------------------------------------------------
    "duffie2013": _r("Duffie & Beckman (2013)", "Duffie, J.A., Beckman, W.A.", "2013",
                     "Solar Engineering of Thermal Processes", "Wiley, Hoboken", "4th ed.",
                     kind="book"),
    "masters2013": _r("Masters (2013)", "Masters, G.M.", "2013",
                      "Renewable and Efficient Electric Power Systems", "Wiley, Hoboken",
                      "2nd ed.", kind="book"),
    "luque2011": _r("Luque & Hegedus (2011)", "Luque, A., Hegedus, S. (eds.)", "2011",
                    "Handbook of Photovoltaic Science and Engineering", "Wiley, Chichester",
                    "2nd ed.", kind="book"),
    "quaschning2013": _r("Quaschning (2013)", "Quaschning, V.", "2013",
                         "Regenerative Energiesysteme: Technologie, Berechnung, Simulation",
                         "Hanser, Munich", "8th ed.", kind="book"),
    "huld2012": _r("Huld et al. (2012)", "Huld, T., Müller, R., Gambardella, A.", "2012",
                   "A new solar radiation database for estimating PV performance in Europe and Africa",
                   "Solar Energy", "86(6):1803-1815", doi="10.1016/j.solener.2012.03.006"),
    "suri2007": _r("Šúri et al. (2007)", "Šúri, M., Huld, T.A., Dunlop, E.D., Ossenbrink, H.A.",
                   "2007", "Potential of solar electricity generation in the European Union member "
                   "states and candidate countries", "Solar Energy", "81(10):1295-1305",
                   doi="10.1016/j.solener.2006.12.007"),
    "pvgis": _r("PVGIS (JRC)", "European Commission, Joint Research Centre", "",
                "Photovoltaic Geographical Information System (PVGIS)", "",
                url="https://re.jrc.ec.europa.eu/pvg_tools/", kind="dataset"),
    "iec61724": _r("IEC 61724-1", "International Electrotechnical Commission", "2021",
                   "IEC 61724-1: Photovoltaic system performance, Part 1: Monitoring",
                   "IEC, Geneva", kind="standard"),
    "iec62548": _r("IEC 62548", "International Electrotechnical Commission", "",
                   "IEC 62548 series: Photovoltaic (PV) arrays, design requirements",
                   "IEC, Geneva", "use the current edition", kind="standard"),
    "reich2012": _r("Reich et al. (2012)",
                    "Reich, N.H., Mueller, B., Armbruster, A., van Sark, W.G.J.H.M., Kiefer, K., Reise, C.",
                    "2012", "Performance ratio revisited: is PR > 90% realistic?",
                    "Progress in Photovoltaics", "20(6):717-726"),
    "jordan2013": _r("Jordan & Kurtz (2013)", "Jordan, D.C., Kurtz, S.R.", "2013",
                     "Photovoltaic degradation rates: an analytical review",
                     "Progress in Photovoltaics", "21(1):12-29", doi="10.1002/pip.1182"),
    "skoplaki2009": _r("Skoplaki & Palyvos (2009)", "Skoplaki, E., Palyvos, J.A.", "2009",
                       "On the temperature dependence of photovoltaic module electrical "
                       "performance: a review of efficiency/power correlations",
                       "Solar Energy", "83(5):614-624", doi="10.1016/j.solener.2008.10.008"),
    "faiman2008": _r("Faiman (2008)", "Faiman, D.", "2008",
                     "Assessing the outdoor operating temperature of photovoltaic modules",
                     "Progress in Photovoltaics", "16(4):307-315", doi="10.1002/pip.813"),
    "mondol2006": _r("Mondol et al. (2006)", "Mondol, J.D., Yohanis, Y.G., Norton, B.", "2006",
                     "Optimal sizing of array and inverter for grid-connected photovoltaic systems",
                     "Solar Energy", "80(12):1517-1539"),
    "quaschning1996": _r("Quaschning & Hanitsch (1996)", "Quaschning, V., Hanitsch, R.", "1996",
                         "Numerical simulation of current-voltage characteristics of photovoltaic "
                         "systems with shaded solar cells", "Solar Energy", "56(6):513-520"),
    "luthander2015": _r("Luthander et al. (2015)",
                        "Luthander, R., Widén, J., Nilsson, D., Palm, J.", "2015",
                        "Photovoltaic self-consumption in buildings: a review",
                        "Applied Energy", "142:80-94", doi="10.1016/j.apenergy.2014.12.028"),
    "nasa_power": _r("NASA POWER", "NASA Langley Research Center", "",
                     "Prediction Of Worldwide Energy Resources (POWER) Project", "",
                     url="https://power.larc.nasa.gov/", kind="dataset"),
    # --- wind ---------------------------------------------------------------------------------
    "burton2011": _r("Burton et al. (2011)", "Burton, T., Jenkins, N., Sharpe, D., Bossanyi, E.",
                     "2011", "Wind Energy Handbook", "Wiley, Chichester", "2nd ed.", kind="book"),
    "manwell2009": _r("Manwell et al. (2009)", "Manwell, J.F., McGowan, J.G., Rogers, A.L.", "2009",
                      "Wind Energy Explained: Theory, Design and Application", "Wiley, Chichester",
                      "2nd ed.", kind="book"),
    "betz1926": _r("Betz (1926)", "Betz, A.", "1926",
                   "Wind-Energie und ihre Ausnutzung durch Windmühlen",
                   "Vandenhoeck & Ruprecht, Göttingen", kind="book"),
    "justus1978": _r("Justus et al. (1978)", "Justus, C.G., Hargraves, W.R., Mikhail, A., Graber, D.",
                     "1978", "Methods for estimating wind speed frequency distributions",
                     "Journal of Applied Meteorology", "17(3):350-353"),
    "jensen1983": _r("Jensen (1983)", "Jensen, N.O.", "1983", "A note on wind generator interaction",
                     "Risø National Laboratory, Roskilde", "Risø-M-2411", kind="report"),
    "katic1986": _r("Katić et al. (1986)", "Katić, I., Højstrup, J., Jensen, N.O.", "1986",
                    "A simple model for cluster efficiency",
                    "Proceedings of the European Wind Energy Association Conference and "
                    "Exhibition (EWEC'86), Rome", "pp. 407-410", kind="report"),
    "iec61400_12": _r("IEC 61400-12-1", "International Electrotechnical Commission", "",
                      "IEC 61400-12-1: Wind energy generation systems, power performance "
                      "measurements of electricity producing wind turbines", "IEC, Geneva",
                      "use the current edition", kind="standard"),
    "iec61400_1": _r("IEC 61400-1", "International Electrotechnical Commission", "",
                     "IEC 61400-1: Wind energy generation systems, design requirements",
                     "IEC, Geneva", "use the current edition", kind="standard"),
    "iso2533": _r("ISO 2533", "International Organization for Standardization", "1975",
                  "ISO 2533: Standard Atmosphere", "ISO, Geneva", kind="standard"),
    "gwa": _r("Davis et al. (2023)", "Davis, N.N., et al.", "2023",
              "The Global Wind Atlas: a high-resolution dataset of climatologies and "
              "associated web-based application", "Bulletin of the American Meteorological "
              "Society", "104(8):E1507-E1525", url="https://globalwindatlas.info/"),
    "nrel_turbines": _r("NREL turbine-models", "National Renewable Energy Laboratory", "",
                        "turbine-models: power curves and specifications of wind turbines", "",
                        url="https://github.com/NREL/turbine-models", kind="dataset"),
    "ewea2009": _r("EWEA (2009)", "European Wind Energy Association", "2009",
                   "Wind Energy: The Facts", "Earthscan, London", kind="book"),
    # --- economics and emissions ----------------------------------------------------------------
    "short1995": _r("Short et al. (1995)", "Short, W., Packey, D.J., Holt, T.", "1995",
                    "A Manual for the Economic Evaluation of Energy Efficiency and Renewable "
                    "Energy Technologies", "National Renewable Energy Laboratory, Golden",
                    "NREL/TP-462-5173", kind="report"),
    "iea_projected": _r("IEA & NEA (2020)", "International Energy Agency, Nuclear Energy Agency",
                        "2020", "Projected Costs of Generating Electricity, 2020 edition",
                        "OECD Publishing, Paris", kind="report"),
    "irena_costs": _r("IRENA (2024)", "International Renewable Energy Agency", "2024",
                      "Renewable Power Generation Costs in 2023", "IRENA, Abu Dhabi",
                      "latest edition: check", kind="report"),
    "ipcc_ar5_annex3": _r("Schlömer et al. (2014)", "Schlömer, S., et al.", "2014",
                          "Annex III: Technology-specific cost and performance parameters. In: "
                          "Climate Change 2014: Mitigation of Climate Change (IPCC AR5, Working "
                          "Group III)", "Cambridge University Press", kind="report"),
    "ipcc2006": _r("IPCC (2006)", "IPCC", "2006",
                   "2006 IPCC Guidelines for National Greenhouse Gas Inventories, Volume 2: Energy",
                   "IGES, Hayama", kind="report"),
    "saltelli2008": _r("Saltelli et al. (2008)",
                       "Saltelli, A., Ratto, M., Andres, T., Campolongo, F., Cariboni, J., "
                       "Gatelli, D., Saisana, M., Tarantola, S.", "2008",
                       "Global Sensitivity Analysis: The Primer", "Wiley, Chichester",
                       kind="book"),
    "ispra": _r("ISPRA", "ISPRA (Istituto Superiore per la Protezione e la Ricerca Ambientale)", "",
                "Fattori di emissione atmosferica di gas a effetto serra nel settore elettrico "
                "nazionale e nei principali Paesi europei", "ISPRA, Roma", "annual report: use "
                "the latest", url="https://www.isprambiente.gov.it/", kind="report"),
    # --- hydrogen -------------------------------------------------------------------------------
    "ulleberg2003": _r("Ulleberg (2003)", "Ulleberg, Ø.", "2003",
                       "Modeling of advanced alkaline electrolyzers: a system simulation approach",
                       "International Journal of Hydrogen Energy", "28(1):21-33",
                       doi="10.1016/S0360-3199(02)00033-2"),
    "carmo2013": _r("Carmo et al. (2013)", "Carmo, M., Fritz, D.L., Mergel, J., Stolten, D.", "2013",
                    "A comprehensive review on PEM water electrolysis",
                    "International Journal of Hydrogen Energy", "38(12):4901-4934",
                    doi="10.1016/j.ijhydene.2013.01.151"),
    "buttler2018": _r("Buttler & Spliethoff (2018)", "Buttler, A., Spliethoff, H.", "2018",
                      "Current status of water electrolysis for energy storage, grid balancing and "
                      "sector coupling via power-to-gas and power-to-liquids: a review",
                      "Renewable and Sustainable Energy Reviews", "82:2440-2454",
                      doi="10.1016/j.rser.2017.09.003"),
    "brauns2020": _r("Brauns & Turek (2020)", "Brauns, J., Turek, T.", "2020",
                     "Alkaline water electrolysis powered by renewable energy: a review",
                     "Processes", "8(2):248"),
    "frensch2019": _r("Frensch et al. (2019)",
                      "Frensch, S.H., Fouda-Onana, F., Serre, G., Thoby, D., Araya, S.S., Kær, S.K.",
                      "2019", "Influence of the operation mode on PEM water electrolysis degradation",
                      "International Journal of Hydrogen Energy", "44(57):29889-29898"),
    "schmidt2017": _r("Schmidt et al. (2017)",
                      "Schmidt, O., Gambhir, A., Staffell, I., Hawkes, A., Nelson, J., Few, S.", "2017",
                      "Future cost and performance of water electrolysis: an expert elicitation study",
                      "International Journal of Hydrogen Energy", "42(52):30470-30492"),
    "armijo2020": _r("Armijo & Philibert (2020)", "Armijo, J., Philibert, C.", "2020",
                     "Flexible production of green hydrogen and ammonia from variable solar and "
                     "wind energy: case study of Chile and Argentina",
                     "International Journal of Hydrogen Energy", "45(3):1541-1558"),
    "iea_future_h2": _r("IEA (2019)", "International Energy Agency", "2019", "The Future of Hydrogen",
                        "IEA, Paris", kind="report"),
    "iea_ghr": _r("IEA (2024)", "International Energy Agency", "2024", "Global Hydrogen Review 2024",
                  "IEA, Paris", "latest edition: check", kind="report"),
    "irena_h2_2020": _r("IRENA (2020a)", "International Renewable Energy Agency", "2020",
                        "Green Hydrogen Cost Reduction: Scaling up Electrolysers to Meet the 1.5 °C "
                        "Climate Goal", "IRENA, Abu Dhabi", kind="report"),
    "irena_h2_policy": _r("IRENA (2020b)", "International Renewable Energy Agency", "2020",
                          "Green Hydrogen: A Guide to Policy Making", "IRENA, Abu Dhabi",
                          kind="report"),
    "h2council2020": _r("Hydrogen Council (2020)", "Hydrogen Council", "2020",
                        "Path to Hydrogen Competitiveness: A Cost Perspective",
                        "Hydrogen Council, Brussels", kind="report"),
    "gardiner2009": _r("Gardiner (2009)", "Gardiner, M.", "2009",
                       "Energy requirements for hydrogen gas compression and liquefaction as "
                       "related to vehicle storage needs", "U.S. DOE Hydrogen and Fuel Cells "
                       "Program", "Record 9013", kind="report"),
    "nist_webbook": _r("NIST Chemistry WebBook", "Linstrom, P.J., Mallard, W.G. (eds.)", "",
                       "NIST Chemistry WebBook, NIST Standard Reference Database Number 69", "NIST",
                       doi="10.18434/T4D303", url="https://webbook.nist.gov/chemistry/",
                       kind="dataset"),
    "rfnbo2023": _r("EU (2023/1184)", "European Commission", "2023",
                    "Commission Delegated Regulation (EU) 2023/1184 supplementing Directive (EU) "
                    "2018/2001 as regards a Union methodology for renewable fuels of non-biological "
                    "origin", "Official Journal of the European Union", "L 157, 20.6.2023",
                    kind="standard"),
    "entsoe": _r("ENTSO-E Transparency Platform", "ENTSO-E", "", "ENTSO-E Transparency Platform "
                 "(day-ahead prices)", "", url="https://transparency.entsoe.eu/", kind="dataset"),
    # --- batteries ------------------------------------------------------------------------------
    "weniger2014": _r("Weniger et al. (2014)", "Weniger, J., Tjaden, T., Quaschning, V.", "2014",
                      "Sizing of residential PV battery systems", "Energy Procedia", "46:78-87"),
    "schimpe2018": _r("Schimpe et al. (2018)", "Schimpe, M., et al.", "2018",
                      "Comprehensive modeling of temperature-dependent degradation mechanisms in "
                      "lithium iron phosphate batteries", "Journal of The Electrochemical Society",
                      "165(2):A181-A193"),
    "hoppmann2014": _r("Hoppmann et al. (2014)", "Hoppmann, J., Volland, J., Schmidt, T.S., Hoffmann, V.H.",
                       "2014", "The economic viability of battery storage for residential solar "
                       "photovoltaic systems: a review and a simulation model",
                       "Renewable and Sustainable Energy Reviews", "39:1101-1118"),
    "wang2011": _r("Wang et al. (2011)", "Wang, J., et al.", "2011",
                   "Cycle-life model for graphite-LiFePO4 cells", "Journal of Power Sources",
                   "196(8):3942-3948"),
    "peters2017": _r("Peters et al. (2017)", "Peters, J.F., Baumann, M., Zimmermann, B., Braun, J., Weil, M.",
                     "2017", "The environmental impact of Li-ion batteries and the role of key "
                     "parameters: a review", "Renewable and Sustainable Energy Reviews", "67:491-506"),
    "schmidt2019": _r("Schmidt et al. (2019)", "Schmidt, O., Melchior, S., Hawkes, A., Staffell, I.",
                      "2019", "Projecting the future levelized cost of electricity storage "
                      "technologies", "Joule", "3(1):81-100", doi="10.1016/j.joule.2018.12.008"),
    "lazard": _r("Lazard (2024)", "Lazard", "2024", "Lazard's Levelized Cost of Energy+ (LCOE+)",
                 "Lazard, New York", "latest edition: check", kind="report"),
    "irena_storage2017": _r("IRENA (2017)", "International Renewable Energy Agency", "2017",
                            "Electricity Storage and Renewables: Costs and Markets to 2030",
                            "IRENA, Abu Dhabi", kind="report"),
    "vdew1999": _r("VDEW (1999)", "VDEW", "1999", "Repräsentative VDEW-Lastprofile",
                   "VDEW-Materialien M-32/99, Frankfurt", kind="report"),
    # --- biomass --------------------------------------------------------------------------------
    "fnr": _r("FNR (2010)", "Fachagentur Nachwachsende Rohstoffe (FNR)", "2010",
              "Guide to Biogas: From Production to Use", "FNR, Gülzow", "5th ed.", kind="report"),
    "ktbl2013": _r("KTBL (2013)", "KTBL", "2013", "Faustzahlen Biogas", "KTBL, Darmstadt", "3rd ed.",
                   kind="report"),
    "obernberger2010": _r("Obernberger & Thek (2010)", "Obernberger, I., Thek, G.", "2010",
                          "The Pellet Handbook: The Production and Thermal Utilization of Biomass "
                          "Pellets", "Earthscan, London", kind="book"),
    "iso17225": _r("EN ISO 17225-1", "International Organization for Standardization", "2021",
                   "EN ISO 17225-1: Solid biofuels, fuel specifications and classes, Part 1: "
                   "General requirements", "ISO, Geneva", kind="standard"),
    "mckendry2002": _r("McKendry (2002)", "McKendry, P.", "2002",
                       "Energy production from biomass (part 1): overview of biomass",
                       "Bioresource Technology", "83(1):37-46"),
    "weiland2010": _r("Weiland (2010)", "Weiland, P.", "2010", "Biogas production: current state and perspectives",
                      "Applied Microbiology and Biotechnology", "85(4):849-860"),
    "red3": _r("Directive (EU) 2023/2413", "European Parliament and Council", "2023",
               "Directive (EU) 2023/2413 amending Directive (EU) 2018/2001 (RED III)",
               "Official Journal of the European Union", kind="standard"),
    "en15316": _r("EN 15316", "CEN", "", "EN 15316 series: Energy performance of buildings, method "
                  "for calculation of system energy requirements and system efficiencies",
                  "CEN, Brussels", "use the current edition", kind="standard"),
    # --- solar thermal and cooling --------------------------------------------------------------
    "iso9806": _r("ISO 9806", "International Organization for Standardization", "2017",
                  "ISO 9806: Solar energy, solar thermal collectors, test methods", "ISO, Geneva",
                  kind="standard"),
    "hottel1958": _r("Hottel & Whillier (1958)", "Hottel, H.C., Whillier, A.", "1958",
                     "Evaluation of flat-plate collector performance",
                     "Transactions of the Conference on the Use of Solar Energy, Vol. 2, "
                     "University of Arizona Press, Tucson", "pp. 74-104", kind="report"),
    "bliss1959": _r("Bliss (1959)", "Bliss, R.W.", "1959",
                    "The derivations of several 'plate-efficiency factors' useful in the design of "
                    "flat-plate solar heat collectors", "Solar Energy", "3(4):55-64"),
    "klein1979": _r("Klein & Beckman (1979)", "Klein, S.A., Beckman, W.A.", "1979",
                    "A general design method for closed-loop solar energy systems",
                    "Solar Energy", "22(3):269-282"),
    "henning2007": _r("Henning (2007)", "Henning, H.-M. (ed.)", "2007",
                      "Solar-Assisted Air-Conditioning in Buildings: A Handbook for Planners",
                      "Springer, Vienna", "2nd ed.", kind="book"),
    "ashrae": _r("ASHRAE Handbook", "ASHRAE", "", "ASHRAE Handbook: HVAC Applications, chapter "
                 "'Service Water Heating'", "ASHRAE, Atlanta", "use the current edition", url="https://www.ashrae.org/", kind="book"),
    "weiss2024": _r("Weiss & Spörk-Dür (2024)", "Weiss, W., Spörk-Dür, M.", "2024",
                    "Solar Heat Worldwide", "AEE INTEC, for the IEA Solar Heating and Cooling "
                    "Programme", "latest edition: check", kind="report"),
    "iea_shc": _r("IEA SHC Tasks", "IEA Solar Heating and Cooling Programme", "",
                  "Task reports of the IEA SHC Programme (Tasks 26, 32, 38, 44, 53)",
                  "IEA SHC", url="https://www.iea-shc.org/", kind="report"),
    # --- hydropower -----------------------------------------------------------------------------
    "esha2004": _r("ESHA (2004)", "European Small Hydropower Association", "2004",
                   "Guide on How to Develop a Small Hydropower Plant", "ESHA, Brussels",
                   "chapters 3, 5 and 6 (turbines)", kind="report"),
    "paish2002": _r("Paish (2002)", "Paish, O.", "2002", "Small hydro power: technology and current status",
                    "Renewable and Sustainable Energy Reviews", "6(6):537-556",
                    doi="10.1016/S1364-0321(02)00006-0"),
    "vogel1994": _r("Vogel & Fennessey (1994)", "Vogel, R.M., Fennessey, N.M.", "1994",
                    "Flow-duration curves. I: New interpretation and confidence intervals",
                    "Journal of Water Resources Planning and Management", "120(4):485-504",
                    doi="10.1061/(ASCE)0733-9496(1994)120:4(485)"),
    "tennant1976": _r("Tennant (1976)", "Tennant, D.L.", "1976",
                      "Instream flow regimens for fish, wildlife, recreation and related environmental "
                      "resources", "Fisheries", "1(4):6-10"),
    "wfd2000": _r("Directive 2000/60/EC", "European Parliament and Council", "2000",
                  "Water Framework Directive", "Official Journal of the European Communities",
                  "L 327", kind="standard"),
    "white2016": _r("White (2016)", "White, F.M.", "2016", "Fluid Mechanics", "McGraw-Hill, New York",
                    "8th ed.", kind="book"),
    "swamee1976": _r("Swamee & Jain (1976)", "Swamee, P.K., Jain, A.K.", "1976",
                     "Explicit equations for pipe-flow problems",
                     "Journal of the Hydraulics Division, ASCE", "102(5):657-664"),
    "nrel_atb2024_hydro": _r("NREL ATB (2024), hydropower", "National Renewable Energy Laboratory", "2024",
                             "Annual Technology Baseline: the 2024 electricity update, hydropower",
                             "NREL, Golden", url="https://atb.nrel.gov/electricity/2024/hydropower",
                             kind="dataset"),
    # --- geothermal -----------------------------------------------------------------------------
    "mit2006": _r("MIT (2006)", "Tester, J.W., et al.", "2006",
                  "The Future of Geothermal Energy: Impact of Enhanced Geothermal Systems (EGS) on the "
                  "United States in the 21st Century", "Massachusetts Institute of Technology",
                  "chapters 6 (drilling) and 7 (energy conversion)",
                  url="https://www1.eere.energy.gov/geothermal/pdfs/egs_chapter_7.pdf", kind="report"),
    "dipippo2016": _r("DiPippo (2016)", "DiPippo, R.", "2016",
                      "Geothermal Power Plants: Principles, Applications, Case Studies and Environmental "
                      "Impact", "Butterworth-Heinemann, Oxford", "4th ed.", kind="book"),
    "lund2021": _r("Lund & Toth (2021)", "Lund, J.W., Toth, A.N.", "2021",
                   "Direct utilization of geothermal energy 2020 worldwide review", "Geothermics",
                   "90:101915", doi="10.1016/j.geothermics.2020.101915"),
    "nrel_atb2024_geo": _r("NREL ATB (2024), geothermal", "National Renewable Energy Laboratory", "2024",
                           "Annual Technology Baseline: the 2024 electricity update, geothermal",
                           "NREL, Golden", url="https://atb.nrel.gov/electricity/2024/geothermal",
                           kind="dataset"),
    # --- cost data ------------------------------------------------------------------------------
    "fraunhofer2024": _r("Kost et al. (2024)",
                         "Kost, C., Müller, P., Sepúlveda Schweiger, J., Fluri, V., Thomsen, J.", "2024",
                         "Levelized Cost of Electricity: Renewable Energy Technologies",
                         "Fraunhofer Institute for Solar Energy Systems ISE, Freiburg", "July 2024",
                         url="https://www.ise.fraunhofer.de/en/publications/studies/cost-of-electricity.html",
                         kind="report"),
    "iea_pvps_italy2024": _r("IEA PVPS (2024), Italy", "IEA Photovoltaic Power Systems Programme", "2024",
                             "National Survey Report of PV Power Applications in Italy 2024", "IEA PVPS",
                             url="https://iea-pvps.org/national_survey/nsr-italy-2024/", kind="report"),
    "nrel_atb2024": _r("NREL ATB (2024)", "National Renewable Energy Laboratory", "2024",
                       "Annual Technology Baseline: the 2024 electricity update, utility-scale PV",
                       "NREL, Golden", url="https://atb.nrel.gov/electricity/2024/utility-scale_pv",
                       kind="dataset"),
    "cole2023": _r("Cole & Karmakar (2023)", "Cole, W., Karmakar, A.", "2023",
                   "Cost Projections for Utility-Scale Battery Storage: 2023 Update",
                   "National Renewable Energy Laboratory, Golden", "NREL/TP-6A40-85332",
                   url="https://www.nrel.gov/docs/fy23osti/85332.pdf", kind="report"),
    "baldwin2014": _r("Baldwin (2014)", "Baldwin, D. (Hexagon Lincoln)", "2014",
                      "Development of High Pressure Hydrogen Storage Tank for Storage and Gaseous Truck "
                      "Delivery", "U.S. DOE Hydrogen and Fuel Cells Program Annual Merit Review, project "
                      "PD021, 17 June 2014",
                      url="https://www.hydrogen.energy.gov/pdfs/review14/pd021_baldwin_2014_o.pdf",
                      kind="report"),
    "mugnier2018": _r("Mugnier et al. (2018)", "Mugnier, D., Saile, S., Philippen, D.", "2018",
                      "Review of installation costs. Info Sheet D1, IEA SHC Task 54 Price Reduction of "
                      "Solar Thermal Systems", "IEA Solar Heating and Cooling Programme", "15 September 2018",
                      url="https://mobile.iea-shc.org/Data/Sites/1/publications/D01-Info-Sheet--Review-of-Installation-Costs.pdf",
                      kind="report"),
}


def full_citation(key: str) -> str:
    """The reference as one HTML line."""
    r = REFS[key]
    year = f" ({escape(r.year)})" if r.year else ""
    title = escape(r.title)
    if r.kind == "article":
        body = f"{escape(r.authors)}{year}. {title}. <i>{escape(r.container)}</i>"
        body += f" {escape(r.detail)}." if r.detail else "."
    elif r.kind == "book":
        body = f"{escape(r.authors)}{year}. <i>{title}</i>"
        body += f", {escape(r.detail.rstrip('.'))}" if r.detail else ""
        body += f". {escape(r.container)}."
    else:
        body = f"{escape(r.authors)}{year}. <i>{title}</i>"
        parts = [p for p in (r.container, r.detail) if p]
        body += (". " + ", ".join(escape(p) for p in parts) + ".") if parts else "."
    if r.doi:
        body += f' doi:<a href="https://doi.org/{escape(r.doi)}">{escape(r.doi)}</a>'
    elif r.url:
        body += f' <a href="{escape(r.url)}">{escape(r.url)}</a>'
    return body
