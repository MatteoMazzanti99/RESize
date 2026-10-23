"""Typical solid biomass fuels and biogas substrates.

The numbers are round handbook values (EN ISO 17225 for solid fuels; FNR / KTBL biogas
guides for substrates). They are starting points: replace them with your supplier's
specification or a laboratory biochemical methane potential (BMP) test.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolidFuel:
    name: str
    lhv_dry_kwh_per_kg: float       # lower heating value of the dry matter
    moisture_wb: float              # moisture as delivered, wet basis (0-1)
    bulk_density_kg_m3: float       # as delivered
    ash_dry: float                  # ash share of the dry matter (0-1)


@dataclass(frozen=True)
class Substrate:
    name: str
    ch4_m3_per_t: float             # methane per tonne of fresh matter
    ch4_fraction: float             # CH4 share of the biogas
    ts: float                       # total solids, share of fresh matter
    vs_of_ts: float                 # volatile solids, share of total solids
    crop_yield_t_per_ha: float = 0.0  # fresh matter per hectare, 0 for wastes and manure

    @property
    def vs_fresh(self) -> float:
        """Volatile solids as a share of the fresh matter."""
        return self.ts * self.vs_of_ts


SOLID_FUELS: tuple[SolidFuel, ...] = (
    SolidFuel("Wood chips (30 % moisture)", 5.15, 0.30, 250.0, 0.010),
    SolidFuel("Wood pellets (8 % moisture)", 5.15, 0.08, 650.0, 0.005),
    SolidFuel("Firewood logs (20 % moisture)", 5.15, 0.20, 380.0, 0.007),
    SolidFuel("Straw bales (15 % moisture)", 5.00, 0.15, 140.0, 0.050),
)

SUBSTRATES: tuple[Substrate, ...] = (
    Substrate("Cattle slurry", 14.0, 0.55, 0.09, 0.80),
    Substrate("Pig slurry", 12.0, 0.60, 0.06, 0.75),
    Substrate("Maize silage", 105.0, 0.52, 0.33, 0.95, 45.0),
    Substrate("Grass silage", 93.0, 0.54, 0.35, 0.90, 30.0),
    Substrate("Biowaste (organic fraction of municipal waste)", 60.0, 0.60, 0.25, 0.85),
)


def fuel_by_name(name: str) -> SolidFuel:
    for fuel in SOLID_FUELS:
        if fuel.name == name:
            return fuel
    raise KeyError(name)


def substrate_by_name(name: str) -> Substrate:
    for item in SUBSTRATES:
        if item.name == name:
            return item
    raise KeyError(name)
