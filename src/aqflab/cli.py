"""Command-line interface.

Subcommands
-----------
plume     Gaussian plume field for one scenario + met condition.
aqi       US EPA AQI from pollutant concentrations.
forecast  7-day synthetic series, persistence vs AR(1) forecast.
report    Markdown + HTML scenario report.
batch     Plume peaks for every scenario x met-scenario combination.

Scenario files are JSON: {"name", "title", "sources": [...],
"receptor": {"x", "y"}, "background": {pollutant: ug/m^3},
"grid": {...}, "urban": bool}. Sources use the to_dict() format of
aqflab.emissions. The city is synthetic ("Kota Sinar") and is
labelled as such in every output.
"""

import argparse
import csv
import json
import os
import sys

from aqflab import aqi as aqi_mod
from aqflab.emissions import Inventory
from aqflab.forecast import run_forecast
from aqflab.meteorology import SCENARIOS, scenario_day
from aqflab.plot import HAS_MATPLOTLIB, ascii_map, \
    plot_concentration_map, plot_daily_aqi
from aqflab.receptors import Receptor, concentration_field, find_peak, \
    make_grid
from aqflab.report import build_report_data, write_report

DEFAULT_POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO"]
# Forecast/report accept "mixed": rotate the three met scenarios
# day by day. Plume/batch use a single scenario day.
MET_CHOICES = list(SCENARIOS) + ["mixed"]


def load_scenario(path):
    """Load a scenario JSON file; returns (data dict, Inventory)."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    from aqflab.emissions import source_from_dict
    sources = [source_from_dict(item) for item in data["sources"]]
    return data, Inventory(sources)


def _met_condition(met_name, hour):
    day = scenario_day(met_name)
    return day[hour % 24]


def cmd_plume(args):
    """Run the plume subcommand."""
    data, inventory = load_scenario(args.scenario)
    met = _met_condition(args.met, args.hour)
    grid = data.get("grid", {"x_min": -500, "x_max": 4000,
                             "y_min": -2000, "y_max": 2000,
                             "step": 250})
    receptors = make_grid(grid["x_min"], grid["x_max"],
                          grid["y_min"], grid["y_max"], grid["step"])
    urban = data.get("urban", False)
    background = data.get("background", {}).get(args.pollutant, 0.0)
    values = concentration_field(
        receptors, inventory.sources, met, args.pollutant,
        urban=urban, background_ug_m3=background)
    receptor, peak = find_peak(receptors, values)
    print(f"Scenario : {data.get('title', data.get('name'))}")
    print(f"Met      : {args.met} hour {args.hour} ({met})")
    print(f"Pollutant: {args.pollutant} "
          f"(background {background:.1f} ug/m^3)")
    print(f"Peak     : {peak:.2f} ug/m^3 at ({receptor.x:.0f}, "
          f"{receptor.y:.0f})")
    print()
    print(ascii_map([r.x for r in receptors], [r.y for r in receptors],
                    values))
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["x_m", "y_m", "conc_ug_m3"])
            for rec, value in zip(receptors, values):
                writer.writerow([f"{rec.x:.0f}", f"{rec.y:.0f}",
                                 f"{value:.4f}"])
        print(f"\nWrote grid CSV: {args.out}")
    if args.png:
        if not HAS_MATPLOTLIB:
            print("matplotlib unavailable; PNG map skipped.")
        else:
            plot_concentration_map(
                [r.x for r in receptors], [r.y for r in receptors],
                values, args.png,
                f"{args.pollutant} ground-level concentration "
                f"({args.met} h{args.hour})")
            print(f"Wrote map PNG: {args.png}")
    return 0


def cmd_aqi(args):
    """Run the aqi subcommand."""
    concentrations = {}
    for key, pollutant in (("pm25", "PM2.5"), ("pm10", "PM10"),
                           ("o3", "O3"), ("o3_1h", "O3_1h"),
                           ("co", "CO"), ("no2", "NO2"),
                           ("so2", "SO2"), ("so2_24h", "SO2_24h")):
        value = getattr(args, key)
        if value is not None:
            concentrations[pollutant] = value
    if not concentrations:
        print("No concentrations given. Pass at least one of "
              "--pm25/--pm10/--o3/--co/--no2/--so2.")
        return 2
    result = aqi_mod.aqi_from_concentrations(concentrations)
    print("Sub-indices:")
    for pol, value in sorted(result["sub_indices"].items()):
        print(f"  {pol:6s} {value if value is not None else 'n/a'}")
    if result["aqi"] is None:
        print("Overall AQI: not available for the given inputs.")
    else:
        print(f"Overall AQI: {result['aqi']} "
              f"({result['category']}), driven by "
              f"{result['driving_pollutant']}")
        print(f"Health: {result['message']}")
    return 0


def cmd_forecast(args):
    """Run the forecast subcommand."""
    data, inventory = load_scenario(args.scenario)
    receptor_data = data.get("receptor", {"x": 1500, "y": 0})
    receptor = Receptor(receptor_data["x"], receptor_data["y"],
                        name="forecast receptor")
    result = run_forecast(
        inventory.sources, receptor, DEFAULT_POLLUTANTS,
        data.get("background", {}), days=args.days,
        horizon=args.horizon, scenario=args.met, seed=args.seed,
        noise_std=args.noise, urban=data.get("urban", False))
    print(f"Scenario : {data.get('title', data.get('name'))}")
    print(f"Receptor : ({receptor.x:.0f}, {receptor.y:.0f})")
    print(f"Met      : {args.met} (synthetic, {args.days} days)")
    print()
    print("Day  AQI")
    for day, value in enumerate(result["daily_aqi"], start=1):
        name = aqi_mod.category(value)[0]
        print(f"{day:3d}  {value:3d}  {name}")
    worst = max(range(len(result["daily_aqi"])),
                key=lambda i: result["daily_aqi"][i])
    print(f"\nWorst day: {worst + 1} "
          f"(AQI {result['daily_aqi'][worst]})")
    print(f"\nForecast of last {args.horizon} days "
          f"(trained on {len(result['train'])} days):")
    print("Day  Actual  Persistence  AR(1)")
    for i, actual in enumerate(result["test"]):
        day = len(result["train"]) + i + 1
        print(f"{day:3d}  {actual:6d}  "
              f"{result['persistence_forecast'][i]:11.1f}  "
              f"{result['ar1_forecast'][i]:6.1f}")
    metrics = result["metrics"]
    print("\nEvaluation (hold-out):")
    for method in ("persistence", "ar1"):
        m = metrics[method]
        print(f"  {method:11s} MAE {m['mae']:.2f}  "
              f"RMSE {m['rmse']:.2f}  bias {m['bias']:+.2f}")
    print(f"  AR(1) skill vs persistence: "
          f"{metrics['ar1_skill_vs_persistence']:+.3f}")
    if args.png:
        if not HAS_MATPLOTLIB:
            print("matplotlib unavailable; PNG chart skipped.")
        else:
            plot_daily_aqi(list(range(1, len(result["daily_aqi"]) + 1)),
                           result["daily_aqi"], args.png,
                           title="Daily AQI (synthetic)")
            print(f"Wrote AQI chart: {args.png}")
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["day", "aqi"])
            for day, value in enumerate(result["daily_aqi"], start=1):
                writer.writerow([day, value])
        print(f"Wrote daily AQI CSV: {args.out}")
    return 0


def _peak_met_name(met_name):
    """Single-day scenario used for the peak table.

    "mixed" rotates scenarios across days, so the peak table uses the
    first day's scenario (calm_morning) as the representative hour.
    """
    if met_name == "mixed":
        return SCENARIOS[0]
    return met_name


def _scenario_peaks(data, inventory, met_name, hour):
    """Peak ground-level concentration per pollutant for one met hour."""
    met = _met_condition(met_name, hour)
    grid = data.get("grid", {"x_min": -500, "x_max": 4000,
                             "y_min": -2000, "y_max": 2000,
                             "step": 250})
    receptors = make_grid(grid["x_min"], grid["x_max"],
                          grid["y_min"], grid["y_max"], grid["step"])
    urban = data.get("urban", False)
    peaks = {}
    for pollutant in DEFAULT_POLLUTANTS:
        background = data.get("background", {}).get(pollutant, 0.0)
        values = concentration_field(
            receptors, inventory.sources, met, pollutant,
            urban=urban, background_ug_m3=background)
        receptor, peak = find_peak(receptors, values)
        peaks[pollutant] = (receptor, peak)
    return peaks


def cmd_report(args):
    """Run the report subcommand."""
    data, inventory = load_scenario(args.scenario)
    receptor_data = data.get("receptor", {"x": 1500, "y": 0})
    receptor = Receptor(receptor_data["x"], receptor_data["y"],
                        name="forecast receptor")
    # horizon=1: the daily series is still complete, which is what
    # the report needs; the forecast split itself is not reported.
    result = run_forecast(
        inventory.sources, receptor, DEFAULT_POLLUTANTS,
        data.get("background", {}), days=args.days,
        horizon=1, scenario=args.met, seed=args.seed,
        noise_std=args.noise, urban=data.get("urban", False))
    peaks = _scenario_peaks(data, inventory,
                            _peak_met_name(args.met), args.hour)
    print(f"Peak table uses met scenario "
          f"'{_peak_met_name(args.met)}' hour {args.hour}.")
    daily_aqi = result["daily_aqi"]
    worst = max(range(len(daily_aqi)), key=lambda i: daily_aqi[i])
    report_data = build_report_data(
        data.get("title", data.get("name", "Air quality report")),
        inventory.totals(), peaks, daily_aqi,
        result["daily_conc"], worst)
    write_report(report_data, args.md,
                 args.html if args.html else None)
    print(f"Wrote report: {args.md}")
    if args.html:
        print(f"Wrote report: {args.html}")
    print(f"Worst day: {worst + 1} (AQI {daily_aqi[worst]})")
    return 0


def cmd_batch(args):
    """Run the batch subcommand over scenarios x met conditions."""
    rows = []
    for scenario_path in args.scenarios:
        data, inventory = load_scenario(scenario_path)
        for met_name in SCENARIOS:
            peaks = _scenario_peaks(data, inventory, met_name,
                                    args.hour)
            for pollutant, (receptor, peak) in peaks.items():
                rows.append({
                    "scenario": data.get("name", scenario_path),
                    "met": met_name, "hour": args.hour,
                    "pollutant": pollutant,
                    "peak_ug_m3": round(peak, 2),
                    "peak_x_m": receptor.x, "peak_y_m": receptor.y,
                })
                print(f"{data.get('name'):22s} {met_name:16s} "
                      f"{pollutant:6s} peak {peak:8.2f} ug/m^3 "
                      f"at ({receptor.x:.0f}, {receptor.y:.0f})")
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=["scenario", "met", "hour", "pollutant",
                                "peak_ug_m3", "peak_x_m", "peak_y_m"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nWrote batch summary: {args.out}")
    return 0


def build_parser():
    """Build the argparse parser."""
    parser = argparse.ArgumentParser(
        prog="aqflab",
        description="Air-quality forecast lab: Gaussian plume "
                    "dispersion, EPA AQI and short-range forecasting "
                    "for a synthetic city.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plume", help="plume concentration field")
    p.add_argument("--scenario", required=True)
    p.add_argument("--pollutant", default="PM2.5")
    p.add_argument("--met", default="calm_morning",
                   choices=list(SCENARIOS))
    p.add_argument("--hour", type=int, default=8)
    p.add_argument("--out", help="grid CSV output path")
    p.add_argument("--png", help="map PNG output path")
    p.set_defaults(func=cmd_plume)

    p = sub.add_parser("aqi", help="EPA AQI from concentrations")
    p.add_argument("--pm25", type=float,
                   help="PM2.5 24-h mean (ug/m^3)")
    p.add_argument("--pm10", type=float,
                   help="PM10 24-h mean (ug/m^3)")
    p.add_argument("--o3", type=float, help="O3 8-h mean (ppm)")
    p.add_argument("--o3-1h", dest="o3_1h", type=float,
                   help="O3 1-h max (ppm)")
    p.add_argument("--co", type=float, help="CO 8-h mean (ppm)")
    p.add_argument("--no2", type=float, help="NO2 1-h max (ppb)")
    p.add_argument("--so2", type=float, help="SO2 1-h max (ppb)")
    p.add_argument("--so2-24h", dest="so2_24h", type=float,
                   help="SO2 24-h mean (ppb)")
    p.set_defaults(func=cmd_aqi)

    p = sub.add_parser("forecast", help="7-day AQI forecast")
    p.add_argument("--scenario", required=True)
    p.add_argument("--days", type=int, default=10)
    p.add_argument("--horizon", type=int, default=3)
    p.add_argument("--met", default="mixed",
                   choices=MET_CHOICES)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--noise", type=float, default=2.0,
                   help="hourly noise std (ug/m^3)")
    p.add_argument("--out", help="daily AQI CSV output path")
    p.add_argument("--png", help="AQI chart PNG output path")
    p.set_defaults(func=cmd_forecast)

    p = sub.add_parser("report", help="Markdown + HTML report")
    p.add_argument("--scenario", required=True)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--met", default="mixed",
                   choices=MET_CHOICES)
    p.add_argument("--hour", type=int, default=8)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--noise", type=float, default=2.0)
    p.add_argument("--md", required=True)
    p.add_argument("--html", help="HTML report output path")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("batch", help="batch plume peaks")
    p.add_argument("--scenarios", nargs="+", required=True)
    p.add_argument("--hour", type=int, default=8)
    p.add_argument("--out", help="batch summary CSV output path")
    p.set_defaults(func=cmd_batch)
    return parser


def main(argv=None):
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
