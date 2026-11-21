#!/usr/bin/env python3
"""Run every CLI example and save the outputs under examples/output/.

Usage: python examples/run_examples.py
All outputs are real runs of the package (no fabricated numbers).
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "examples", "output")
MAIN = os.path.join(ROOT, "main.py")


def run(*args):
    """Run one CLI command, echo it, and fail loudly on error."""
    cmd = [sys.executable, MAIN, *args]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def main():
    os.makedirs(OUT, exist_ok=True)

    # 1. Plume fields: industrial park, PM2.5, all three met scenarios.
    for met in ("calm_morning", "windy_noon", "night_inversion"):
        run("plume", "--scenario", "scenarios/industrial_park.json",
            "--pollutant", "PM2.5", "--met", met, "--hour", "8",
            "--out", f"examples/output/plume_pm25_{met}.csv",
            "--png", f"examples/output/plume_pm25_{met}.png")

    # 2. Plume field: highway corridor, NO2, calm morning.
    run("plume", "--scenario", "scenarios/highway_corridor.json",
        "--pollutant", "NO2", "--met", "calm_morning", "--hour", "8",
        "--out", "examples/output/plume_no2_highway_calm.csv",
        "--png", "examples/output/plume_no2_highway_calm.png")

    # 3. AQI from a set of concentrations.
    run("aqi", "--pm25", "22.3", "--pm10", "80", "--o3", "0.060",
        "--co", "3.0", "--no2", "40", "--so2", "20")

    # 4. Forecast: 10 days, 3-day horizon, industrial park, mixed met.
    run("forecast", "--scenario", "scenarios/industrial_park.json",
        "--days", "10", "--horizon", "3", "--met", "mixed",
        "--out", "examples/output/forecast_daily_aqi.csv",
        "--png", "examples/output/forecast_daily_aqi.png")

    # 5. Report: 7-day scenario report (Markdown + HTML).
    run("report", "--scenario", "scenarios/industrial_park.json",
        "--days", "7", "--met", "mixed", "--hour", "8",
        "--md", "examples/output/report_industrial_park.md",
        "--html", "examples/output/report_industrial_park.html")

    # 6. Batch: every scenario x met scenario, hour 8.
    run("batch", "--scenarios", "scenarios/industrial_park.json",
        "scenarios/highway_corridor.json", "--hour", "8",
        "--out", "examples/output/batch_summary.csv")

    print("\nAll examples finished. Outputs in examples/output/.")


if __name__ == "__main__":
    main()
