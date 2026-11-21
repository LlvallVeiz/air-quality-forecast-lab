"""Tests for receptor grids, plume-frame rotation and fields.

Reference values (hand calculation, class C, x = 1000 m):
    u(30 m) from u10 = 3 m/s: 3 * 3^0.20 = 3.737 m/s
    sy = 0.11*1000*(1.1)^(-1/2) = 104.88 m
    sz = 0.08*1000*(1.2)^(-1/2) = 73.03 m
    C = 10 / (pi*3.737*sy*sz) * exp(-30^2/(2*sz^2)) = 102.19 ug/m^3
for Q = 10 g/s, H = 30 m, receptor (1000, 0), wind toward east.
The expected value is computed with plain arithmetic in the test.
"""

import math

import pytest

from aqflab.dispersion import gaussian_plume
from aqflab.emissions import AreaSource, LineSource, PointSource
from aqflab.meteorology import scenario_day
from aqflab.receptors import (
    Receptor,
    concentration_at,
    concentration_field,
    find_peak,
    make_grid,
    rotate_to_plume_frame,
)
from aqflab.stability import wind_speed_at_height


def _cold_stack():
    """A stack with no plume rise (exit velocity 0, no buoyancy)."""
    return PointSource("stack", 0, 0, 30, 2.0, 0.0, 25.0,
                       {"PM2.5": 10.0})


def test_rotate_to_plume_frame_east_wind():
    down, cross = rotate_to_plume_frame(100.0, 0.0, 90.0)
    assert down == pytest.approx(100.0)
    assert cross == pytest.approx(0.0)
    down, cross = rotate_to_plume_frame(0.0, 100.0, 90.0)
    assert down == pytest.approx(0.0)
    assert cross == pytest.approx(100.0)


def test_rotate_to_plume_frame_north_wind():
    down, cross = rotate_to_plume_frame(0.0, 100.0, 0.0)
    assert down == pytest.approx(100.0)
    assert cross == pytest.approx(0.0)


def test_make_grid_count_and_names():
    grid = make_grid(0, 1000, 0, 500, 250)
    assert len(grid) == 5 * 3
    assert grid[0].x == 0 and grid[0].y == 0
    assert grid[-1].x == 1000 and grid[-1].y == 500
    with pytest.raises(ValueError):
        make_grid(0, 1000, 0, 500, 0)


def test_concentration_at_hand_value():
    met = scenario_day("calm_morning")[12]  # u10=3.0, class C, 30 C
    receptor = Receptor(1000, 0)
    value = concentration_at(receptor, [_cold_stack()], met, "PM2.5")
    wind = wind_speed_at_height(3.0, 10.0, 30.0, "C")
    sy = 0.11 * 1000.0 * (1.0 + 0.0001 * 1000.0) ** (-0.5)
    sz = 0.08 * 1000.0 * (1.0 + 0.0002 * 1000.0) ** (-0.5)
    expected = 10.0 / (math.pi * wind * sy * sz) * math.exp(
        -30.0 ** 2 / (2.0 * sz ** 2)) * 1e6
    assert value == pytest.approx(expected, rel=1e-9)
    assert value == pytest.approx(102.19, abs=0.05)


def test_concentration_at_matches_direct_plume_call():
    met = scenario_day("windy_noon")[12]
    receptor = Receptor(2000, 100)
    value = concentration_at(receptor, [_cold_stack()], met, "PM2.5")
    wind = wind_speed_at_height(met.wind_speed_10m, 10.0, 30.0,
                                met.stability)
    direct = gaussian_plume(10.0, wind, 2000.0, 100.0, 0.0, 30.0,
                            met.stability) * 1e6
    assert value == pytest.approx(direct, rel=1e-9)


def test_upwind_receptor_gets_background_only():
    met = scenario_day("calm_morning")[12]
    receptor = Receptor(-1000, 0)  # upwind of the stack
    value = concentration_at(receptor, [_cold_stack()], met, "PM2.5",
                            background_ug_m3=12.0)
    assert value == pytest.approx(12.0)


def test_background_adds_linearly():
    met = scenario_day("calm_morning")[12]
    receptor = Receptor(1000, 0)
    base = concentration_at(receptor, [_cold_stack()], met, "PM2.5")
    with_bg = concentration_at(receptor, [_cold_stack()], met, "PM2.5",
                              background_ug_m3=12.0)
    assert with_bg == pytest.approx(base + 12.0)


def test_hot_stack_rises_above_physical_height():
    hot = PointSource("hot", 0, 0, 30, 2.0, 18.0, 180.0,
                      {"PM2.5": 10.0})
    met = scenario_day("calm_morning")[12]
    receptor = Receptor(1000, 0)
    hot_value = concentration_at(receptor, [hot], met, "PM2.5")
    cold_value = concentration_at(receptor, [_cold_stack()], met,
                                  "PM2.5")
    # Plume rise lifts the plume: less ground-level impact nearby.
    assert hot_value < cold_value


def test_concentration_field_and_peak():
    met = scenario_day("calm_morning")[8]
    grid = make_grid(-500, 3000, -1000, 1000, 500)
    values = concentration_field(grid, [_cold_stack()], met, "PM2.5")
    assert len(values) == len(grid)
    assert all(v >= 0 for v in values)
    receptor, peak = find_peak(grid, values)
    assert peak == max(values)
    assert receptor.x > 0  # peak is downwind of the source
    with pytest.raises(ValueError):
        find_peak([], [])


def test_area_and_line_sources_contribute():
    met = scenario_day("calm_morning")[12]
    receptor = Receptor(500, 0)
    yard = AreaSource("yard", 0, 0, 400, 300, 5.0, {"PM10": 1.0})
    road = LineSource("road", -1000, -500, 1000, -500, 1000,
                      {"petrol": 1.0})
    value = concentration_at(receptor, [yard, road], met, "PM10")
    assert value > 0
    yard_only = concentration_at(receptor, [yard], met, "PM10")
    assert value > yard_only
