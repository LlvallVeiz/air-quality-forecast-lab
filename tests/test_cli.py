"""CLI smoke tests (small coarse-grid scenario for speed)."""

import json

import pytest

from aqflab.cli import main

SCENARIO = {
    "name": "mini",
    "title": "Mini test scenario",
    "urban": False,
    "sources": [
        {"kind": "point", "name": "Stack", "x": 0, "y": 0,
         "stack_height": 30, "diameter": 1.5, "exit_velocity": 12,
         "exit_temp_c": 160, "ambient_temp_c": 25,
         "emissions": {"PM2.5": 1.0, "PM10": 1.0, "NO2": 10.0,
                       "SO2": 0.1, "CO": 8.0}},
        {"kind": "line", "name": "Road", "x1": -1000, "y1": -800,
         "x2": 1000, "y2": -800, "traffic_veh_per_hour": 1000,
         "fleet_mix": {"petrol": 0.5, "diesel": 0.5},
         "release_height": 2.0, "segments": 5},
    ],
    "receptor": {"x": 1000, "y": 0},
    "background": {"PM2.5": 12.0, "PM10": 25.0, "NO2": 15.0,
                   "SO2": 5.0, "CO": 400.0},
    "grid": {"x_min": -500, "x_max": 2000, "y_min": -1000,
             "y_max": 1000, "step": 500},
}


@pytest.fixture
def scenario_path(tmp_path):
    path = tmp_path / "mini.json"
    path.write_text(json.dumps(SCENARIO), encoding="utf-8")
    return str(path)


def test_cli_aqi(capsys):
    assert main(["aqi", "--pm25", "22.3", "--pm10", "80"]) == 0
    out = capsys.readouterr().out
    assert "Overall AQI: 76" in out
    assert "PM2.5" in out


def test_cli_aqi_no_inputs_returns_error(capsys):
    assert main(["aqi"]) == 2


def test_cli_plume_writes_csv(scenario_path, tmp_path, capsys):
    out_csv = str(tmp_path / "grid.csv")
    assert main(["plume", "--scenario", scenario_path,
                 "--pollutant", "PM2.5", "--met", "calm_morning",
                 "--hour", "8", "--out", out_csv]) == 0
    text = capsys.readouterr().out
    assert "Peak" in text
    assert "ug/m^3" in text
    rows = (tmp_path / "grid.csv").read_text(
        encoding="utf-8").strip().splitlines()
    # 6 x 5 grid = 30 receptors + header.
    assert len(rows) == 31
    assert rows[0] == "x_m,y_m,conc_ug_m3"


def test_cli_forecast(scenario_path, tmp_path, capsys):
    out_csv = str(tmp_path / "aqi.csv")
    assert main(["forecast", "--scenario", scenario_path,
                 "--days", "7", "--horizon", "2",
                 "--met", "calm_morning", "--out", out_csv]) == 0
    text = capsys.readouterr().out
    assert "Day  AQI" in text
    assert "Worst day" in text
    assert "AR(1) skill" in text
    rows = (tmp_path / "aqi.csv").read_text(
        encoding="utf-8").strip().splitlines()
    assert len(rows) == 8  # header + 7 days


def test_cli_report(scenario_path, tmp_path):
    md_path = str(tmp_path / "report.md")
    html_path = str(tmp_path / "report.html")
    assert main(["report", "--scenario", scenario_path,
                 "--days", "7", "--met", "calm_morning",
                 "--md", md_path, "--html", html_path]) == 0
    md = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Mini test scenario" in md
    assert "Worst day" in md
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html


def test_cli_batch(scenario_path, tmp_path, capsys):
    out_csv = str(tmp_path / "batch.csv")
    assert main(["batch", "--scenarios", scenario_path,
                 "--hour", "8", "--out", out_csv]) == 0
    text = capsys.readouterr().out
    assert "calm_morning" in text
    assert "windy_noon" in text
    assert "night_inversion" in text
    rows = (tmp_path / "batch.csv").read_text(
        encoding="utf-8").strip().splitlines()
    # 3 met scenarios x 5 pollutants + header.
    assert len(rows) == 16
