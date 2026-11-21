"""Tests for synthetic meteorology and diurnal emission profile."""

import pytest

from aqflab.meteorology import (
    SCENARIOS,
    diurnal_emission_factor,
    generate_met_series,
    scenario_day,
)


def test_scenario_names():
    assert set(SCENARIOS) == {"calm_morning", "windy_noon",
                              "night_inversion"}


def test_calm_morning_pattern():
    day = scenario_day("calm_morning")
    assert len(day) == 24
    assert day[0].stability == "F"
    assert day[0].wind_speed_10m == pytest.approx(1.0)
    assert day[12].stability == "C"
    assert day[12].wind_speed_10m == pytest.approx(3.0)
    assert day[12].temp_c == pytest.approx(30.0)


def test_windy_noon_is_stronger_than_calm_morning():
    calm = scenario_day("calm_morning")
    windy = scenario_day("windy_noon")
    assert windy[12].wind_speed_10m > calm[12].wind_speed_10m
    assert windy[12].stability in ("A", "B", "C")
    assert windy[12].mixing_height_m > calm[12].mixing_height_m


def test_night_inversion_is_stable_all_night():
    day = scenario_day("night_inversion")
    assert day[0].stability == "F"
    assert day[3].stability == "F"
    assert day[0].mixing_height_m == pytest.approx(200.0)


def test_scenario_day_unknown_raises():
    with pytest.raises(ValueError):
        scenario_day("hurricane")


def test_wind_direction_wraps():
    day = scenario_day("calm_morning", wind_direction_deg=450.0)
    assert day[0].wind_direction_deg == pytest.approx(90.0)


def test_generate_met_series_length_and_continuity():
    series = generate_met_series(3, scenario="windy_noon", seed=1)
    assert len(series) == 72
    assert series[0].hour == 0
    assert series[24].hour == 24
    assert series[71].hour == 71
    # Days differ slightly (seeded jitter) but share the pattern.
    assert series[12].wind_speed_10m > series[0].wind_speed_10m
    with pytest.raises(ValueError):
        generate_met_series(0)


def test_generate_met_series_is_deterministic():
    a = generate_met_series(2, seed=99)
    b = generate_met_series(2, seed=99)
    assert [c.wind_speed_10m for c in a] == \
        [c.wind_speed_10m for c in b]
    c = generate_met_series(2, seed=100)
    assert [x.wind_speed_10m for x in a] != \
        [x.wind_speed_10m for x in c]


def test_generate_met_series_mixed_rotates_scenarios():
    series = generate_met_series(3, scenario="mixed", seed=1)
    assert len(series) == 72
    # Day 1 calm (F at night), day 2 windy (D at night), day 3 night
    # inversion (F at night) -- stabilities differ across days.
    assert series[0].stability == "F"
    assert series[24].stability == "D"
    assert series[48].stability == "F"
    assert series[24].wind_speed_10m > series[0].wind_speed_10m


def test_diurnal_emission_factor_shape():
    # Morning rush > night minimum; evening rush > midday lull.
    assert diurnal_emission_factor(8.0) > diurnal_emission_factor(3.0)
    assert diurnal_emission_factor(18.0) > diurnal_emission_factor(3.0)
    assert diurnal_emission_factor(3.0) < 1.0
    assert diurnal_emission_factor(8.0) > 1.0
    assert all(diurnal_emission_factor(h) > 0 for h in range(24))
    # 24-hour wrap-around.
    assert diurnal_emission_factor(32.0) == pytest.approx(
        diurnal_emission_factor(8.0))
