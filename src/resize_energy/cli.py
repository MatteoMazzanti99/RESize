"""Minimal command-line interface (useful for quick checks and scripting)."""

from __future__ import annotations

import argparse

from resize_energy import __version__
from resize_energy.core import pv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="resize-cli", description="RESize command line")
    parser.add_argument("--version", action="version", version=f"RESize {__version__}")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("pv-power", help="required PV peak power for an annual demand")
    p.add_argument("--demand-kwh", type=float, required=True)
    p.add_argument("--irradiation", type=float, required=True, help="annual in-plane kWh/m2")
    p.add_argument("--pr", type=float, default=0.80)
    p.add_argument("--coverage", type=float, default=1.0)

    args = parser.parse_args(argv)
    if args.command == "pv-power":
        kwp = pv.required_peak_power_kwp(args.demand_kwh, args.irradiation, args.pr, args.coverage)
        print(f"Required peak power: {kwp:.2f} kWp")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
