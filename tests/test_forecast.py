"""Tests for forecasting: AR(1), persistence, evaluation metrics."""

import pytest

from aqflab.emissions import PointSource
from aqflab.forecast import (
    ar1_forecast,
    daily_aqi_series,
    daily_aggregates,
    evaluate,
    fit_ar1,
    persistence_forecast,
    run_forecast,
    skill_score,
)
from aqflab.meteorology import generate_met_series
from aqflab.receptors import Receptor


def test_evaluate_hand_values():
    # obs [12, 11, 13], pred [10, 12, 11]: errors [-2, +1, -2].
    result = evaluate([12, 11, 13], [10, 12, 11])
    assert result["mae"] == pytest.approx(5.0 / 3.0)
    assert result["rmse"] == pytest.approx(3.0 ** 0.5)
    assert result["bias"] == pytest.approx(-1.0)
    assert result["n"] == 3
    with pytest.raises(ValueError):
        evaluate([1, 2], [1])
    with pytest.raises(ValueError):
        evaluate([], [])


def test_fit_ar1_exact_series():
    # x_t = 1 + 1*x_{t-1} exactly for [0, 1, 2, 3, 4].
    c, phi = fit_ar1([0, 1, 2, 3, 4])
    assert phi == pytest.approx(1.0)
    assert c == pytest.approx(1.0)


def test_fit_ar1_recovers_known_parameters():
    # Generate x_t = 5 + 0.6*x_{t-1} (no noise).
    series = [10.0]
    for _ in range(20):
        series.append(5.0 + 0.6 * series[-1])
    c, phi = fit_ar1(series)
    assert phi == pytest.approx(0.6, abs=0.01)
    assert c == pytest.approx(5.0, abs=0.05)


def test_fit_ar1_needs_variance():
    with pytest.raises(ValueError):
        fit_ar1([5.0, 5.0, 5.0, 5.0])
    with pytest.raises(ValueError):
        fit_ar1([1.0, 2.0])


def test_ar1_forecast_iterates():
    # Constant drift series: next values continue +1 per step.
    assert ar1_forecast([0, 1, 2, 3, 4], 3) == pytest.approx(
        [5.0, 6.0, 7.0])


def test_ar1_forecast_falls_back_to_persistence_on_constant_series():
    assert ar1_forecast([5.0, 5.0, 5.0, 5.0], 2) == [5.0, 5.0]


def test_persistence_forecast():
    assert persistence_forecast([10, 12, 11], 3) == [11, 11, 11]
    with pytest.raises(ValueError):
        persistence_forecast([], 2)


def test_skill_score_perfect_and_useless():
    assert skill_score([10, 12, 11], [10, 12, 11], [9, 9, 9]) \
        == pytest.approx(1.0)
    assert skill_score([10, 12, 11], [9, 9, 9], [9, 9, 9]) \
        == pytest.approx(0.0)


def test_daily_aggregates_pm_is_24h_mean():
    hourly = [10.0] * 24 + [20.0] * 24
    assert daily_aggregates(hourly, "PM2.5") == [10.0, 20.0]


def test_daily_aggregates_o3_is_8h_max():
    hourly = [0.0] * 24
    hourly[10:18] = [0.08] * 8  # one 8-hour block at 0.08
    assert daily_aggregates(hourly, "O3") == pytest.approx([0.08])
    hourly[0:8] = [0.05] * 8
    assert daily_aggregates(hourly, "O3") == pytest.approx([0.08])


def test_daily_aggregates_no2_is_1h_max():
    hourly = [5.0] * 24
    hourly[7] = 42.0
    assert daily_aggregates(hourly, "NO2") == [42.0]
    with pytest.raises(ValueError):
        daily_aggregates([1.0] * 25, "PM2.5")


def test_daily_aqi_series_converts_units():
    # Constant 20 ug/m^3 PM2.5 all day -> daily mean 20 -> AQI 71
    # (51 + 49*(20-9.1)/26.3 = 71.31 -> 71).
    hourly = {"PM2.5": [20.0] * 48}
    values, daily = daily_aqi_series(hourly)
    assert len(values) == 2
    assert values[0] == 71
    assert daily["PM2.5"][0] == pytest.approx(20.0)


def test_daily_aqi_series_reports_ug_m3_for_gases():
    # Daily concentrations returned to the caller are always ug/m^3,
    # even though the AQI itself is computed in ppm/ppb.
    hourly = {"CO": [400.0] * 48, "NO2": [15.0] * 48,
              "PM2.5": [20.0] * 48}
    values, daily = daily_aqi_series(hourly)
    assert daily["CO"][0] == pytest.approx(400.0)
    assert daily["NO2"][0] == pytest.approx(15.0)
    assert daily["PM2.5"][0] == pytest.approx(20.0)
    assert values[0] == 71  # PM2.5 drives the AQI here


def test_run_forecast_smoke_and_deterministic():
    sources = [PointSource("stack", 0, 0, 30, 2.0, 15.0, 180.0,
                           {"PM2.5": 1.0, "PM10": 1.0, "NO2": 5.0,
                            "SO2": 0.1, "CO": 5.0})]
    receptor = Receptor(1500, 0)
    result = run_forecast(
        sources, receptor,
        ["PM2.5", "PM10", "NO2", "SO2", "CO"],
        {"PM2.5": 12.0, "PM10": 25.0, "NO2": 15.0, "SO2": 5.0,
         "CO": 400.0},
        days=7, horizon=2, scenario="calm_morning", seed=42,
        noise_std=1.0)
    assert len(result["daily_aqi"]) == 7
    assert len(result["test"]) == 2
    assert len(result["ar1_forecast"]) == 2
    assert all(v is not None and v >= 0 for v in result["daily_aqi"])
    assert result["metrics"]["ar1"]["rmse"] >= 0
    assert result["metrics"]["persistence"]["rmse"] >= 0
    again = run_forecast(
        sources, receptor,
        ["PM2.5", "PM10", "NO2", "SO2", "CO"],
        {"PM2.5": 12.0, "PM10": 25.0, "NO2": 15.0, "SO2": 5.0,
         "CO": 400.0},
        days=7, horizon=2, scenario="calm_morning", seed=42,
        noise_std=1.0)
    assert again["daily_aqi"] == result["daily_aqi"]
    assert again["ar1_forecast"] == result["ar1_forecast"]
