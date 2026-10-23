"""Build src/resize_energy/data/turbines.json from a clone of NREL/turbine-models (BSD-3-Clause).

Usage:  python tools/build_turbine_library.py /path/to/turbine-models/turbine_models

Only onshore and distributed turbines with a power curve in kW are kept. The output is one
compact JSON file shipped inside the package; see THIRD_PARTY_NOTICES.md for the source and
license. Re-run it when the upstream library is updated.
"""

from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from pathlib import Path

GROUPS = ("Onshore", "Distributed")


def parse_yaml(path: Path) -> dict[str, object]:
    """Tiny reader for the flat 'key: value  # comment' files of the library."""
    out: dict[str, object] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not m:
            continue
        key, rest = m.group(1), m.group(2)
        rest = rest.split(" #")[0].strip() if not rest.startswith("[") else rest.split("]")[0] + "]"
        rest = rest.strip().strip("'\"")
        if rest in ("", "#N/A") or rest.startswith("#"):
            out[key] = None
        elif rest.startswith("["):
            nums = re.findall(r"-?\d+(?:\.\d+)?", rest)
            out[key] = [float(n) for n in nums]
        else:
            try:
                out[key] = float(rest)
            except ValueError:
                out[key] = rest
    return out


def read_curve(path: Path) -> list[list[float]] | None:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    header = [h.strip() for h in rows[0]]
    try:
        iv = next(i for i, h in enumerate(header) if h.startswith("Wind Speed"))
        ip = next(i for i, h in enumerate(header) if h.startswith("Power [kW]"))
    except StopIteration:
        return None  # normalised curves have no kW column
    pts: list[list[float]] = []
    for row in rows[1:]:
        try:
            v, p = float(row[iv]), float(row[ip])
        except (ValueError, IndexError):
            continue
        pts.append([round(v, 3), round(max(p, 0.0), 3)])
    pts.sort()
    return pts if len(pts) >= 5 else None


def main(root: Path) -> int:
    turbines = []
    for group in GROUPS:
        for yml in sorted((root / "specs" / group).glob("*.yaml")):
            spec = parse_yaml(yml)
            csv_path = root / "data" / group / f"{yml.stem}.csv"
            if not csv_path.exists():
                continue
            curve = read_curve(csv_path)
            if curve is None:
                continue
            pmax = max(p for _, p in curve)
            rated_kw = spec.get("rated_power") if isinstance(spec.get("rated_power"), float) else pmax
            diameter = spec.get("rotor_diameter")
            if not isinstance(diameter, float):
                m = re.search(r"_([\d.]+)$", yml.stem)
                diameter = float(m.group(1)) if m else None
            if not diameter or pmax <= 0:
                continue
            first_pos = next(v for v, p in curve if p > 0)
            rated_v = spec.get("rated_wind_speed") or next(v for v, p in curve if p >= 0.98 * pmax)
            hub = spec.get("hub_height")
            if isinstance(hub, list):
                hub = statistics.median(hub)
            elif not isinstance(hub, float):
                hub = None  # e.g. "Varies"
            name = str(spec.get("name") or yml.stem).replace("_", " ")
            turbines.append({
                "id": yml.stem,
                "name": name,
                "group": group.lower(),
                "manufacturer": spec.get("manufacturer"),
                "origin": spec.get("origin"),
                "rated_power_kw": float(rated_kw),
                "rotor_diameter_m": float(diameter),
                "hub_height_m": float(hub) if hub else None,
                "cut_in_ms": float(spec.get("cut_in_wind_speed") or first_pos),
                "rated_speed_ms": float(rated_v),
                "cut_out_ms": float(spec.get("cut_out_wind_speed") or curve[-1][0]),
                "curve": curve,
            })
    out = Path(__file__).resolve().parent.parent / "src" / "resize_energy" / "data" / "turbines.json"
    out.write_text(json.dumps({
        "source": "NREL turbine-models (BSD-3-Clause), https://github.com/NREL/turbine-models",
        "turbines": turbines,
    }, separators=(",", ":")), encoding="utf-8")
    print(f"{len(turbines)} turbines written to {out} ({out.stat().st_size / 1024:.0f} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
