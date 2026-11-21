"""Tests for the emission inventory (AP-42, Euro 6, source classes)."""

import math

import pytest

from aqflab.emissions import (
    AP42_NATURAL_GAS_LB_PER_MMSCF,
    AreaSource,
    Inventory,
    LineSource,
    PointSource,
    ap42_gas_emission_rate,
    fleet_emission_factor,
    gas_boiler_emissions,
    source_from_dict,
)


def test_ap42_conversion_hand_value():
    # 100 lb/MMscf NOx at 30 MMscf/day = 3000 lb/day
    # = 3000 * 453.59237 / 86400 = 15.7497 g/s.
    assert ap42_gas_emission_rate(100.0, 30.0) == pytest.approx(
        3000.0 * 453.59237 / 86400.0, rel=1e-12)
    assert ap42_gas_emission_rate(100.0, 30.0) == pytest.approx(
        15.7497, abs=0.001)


def test_ap42_table_values_present():
    assert AP42_NATURAL_GAS_LB_PER_MMSCF["NO2"] == 100.0
    assert AP42_NATURAL_GAS_LB_PER_MMSCF["CO"] == 84.0
    assert AP42_NATURAL_GAS_LB_PER_MMSCF["PM2.5"] == 7.6
    assert AP42_NATURAL_GAS_LB_PER_MMSCF["SO2"] == 0.6


def test_gas_boiler_emissions_scale_with_fuel():
    small = gas_boiler_emissions(10.0)
    big = gas_boiler_emissions(30.0)
    for pol in small:
        assert big[pol] == pytest.approx(3.0 * small[pol], rel=1e-12)
    assert small["NO2"] == pytest.approx(5.2499, abs=0.001)


def test_fleet_emission_factor_mixed_fleet():
    # 60% petrol + 40% diesel NO2: 0.6*0.06 + 0.4*0.08 = 0.068 g/km.
    assert fleet_emission_factor(
        "NO2", {"petrol": 0.6, "diesel": 0.4}) == pytest.approx(0.068)
    assert fleet_emission_factor(
        "CO", {"petrol": 0.5, "diesel": 0.5}) == pytest.approx(0.75)
    with pytest.raises(ValueError):
        fleet_emission_factor("NO2", {"petrol": 0.6, "diesel": 0.5})
    with pytest.raises(ValueError):
        fleet_emission_factor("NO2", {"electric": 1.0})
    with pytest.raises(ValueError):
        fleet_emission_factor("O3", {"petrol": 1.0})


def test_line_source_total_hand_value():
    # 1800 veh/h, 60/40 fleet, NO2 0.068 g/km, 5000 m road:
    # 1800 * 0.068 * 5000 / 3.6e6 = 0.17 g/s.
    road = LineSource("road", -2000, -1200, 3000, -1200, 1800,
                      {"petrol": 0.6, "diesel": 0.4})
    assert road.length == pytest.approx(5000.0)
    assert road.emission_rate("NO2") == pytest.approx(0.17, rel=1e-9)
    assert road.line_emission_rate("NO2") == pytest.approx(
        1800 * 0.068 / 3.6e6, rel=1e-12)


def test_line_virtual_points_sum_to_total():
    road = LineSource("road", 0, 0, 1000, 0, 1000,
                      {"petrol": 1.0}, segments=10)
    points = road.virtual_points("NO2")
    assert len(points) == 10
    assert sum(q for _x, _y, q in points) == pytest.approx(
        road.emission_rate("NO2"), rel=1e-12)
    xs = [x for x, _y, _q in points]
    assert xs == pytest.approx(
        [50 + 100 * i for i in range(10)], rel=1e-12)


def test_area_virtual_points_sum_to_total():
    yard = AreaSource("yard", 0, 0, 400, 300, 5.0,
                      {"PM10": 1.0}, cells_x=4, cells_y=3)
    points = yard.virtual_points("PM10")
    assert len(points) == 12
    assert sum(q for _x, _y, q in points) == pytest.approx(1.0)
    assert all(q == pytest.approx(1.0 / 12.0)
               for _x, _y, q in points)


def test_point_source_round_trip():
    src = PointSource("stack", 10, 20, 45, 2.0, 18, 180,
                      {"NO2": 15.75, "PM2.5": 1.2})
    rebuilt = source_from_dict(src.to_dict())
    assert isinstance(rebuilt, PointSource)
    assert rebuilt.name == "stack"
    assert rebuilt.emission_rate("NO2") == pytest.approx(15.75)
    assert rebuilt.emission_rate("O3") == 0.0


def test_area_and_line_round_trip():
    yard = AreaSource("yard", 0, 0, 100, 50, 5.0, {"PM10": 0.5})
    assert source_from_dict(yard.to_dict()).emission_rate("PM10") \
        == pytest.approx(0.5)
    road = LineSource("road", 0, 0, 100, 0, 500, {"diesel": 1.0})
    rebuilt = source_from_dict(road.to_dict())
    assert isinstance(rebuilt, LineSource)
    assert rebuilt.traffic == 500
    with pytest.raises(ValueError):
        source_from_dict({"kind": "volcano"})


def test_inventory_totals():
    inv = Inventory([
        PointSource("a", 0, 0, 30, 1.0, 10, 150, {"NO2": 5.0}),
        PointSource("b", 100, 0, 30, 1.0, 10, 150, {"NO2": 7.0,
                                                     "SO2": 1.0}),
    ])
    assert inv.total("NO2") == pytest.approx(12.0)
    assert inv.total("SO2") == pytest.approx(1.0)
    assert inv.total("PM2.5") == 0.0
    assert inv.totals()["NO2"] == pytest.approx(12.0)


def test_invalid_sources_raise():
    with pytest.raises(ValueError):
        PointSource("x", 0, 0, 30, 1.0, 10, 150, {"NO2": -1.0})
    with pytest.raises(ValueError):
        AreaSource("x", 0, 0, 0, 100, 5.0, {"PM10": 1.0})
    with pytest.raises(ValueError):
        LineSource("x", 0, 0, 0, 0, 100, {"petrol": 1.0})
    with pytest.raises(ValueError):
        LineSource("x", 0, 0, 100, 0, -5, {"petrol": 1.0})
    with pytest.raises(ValueError):
        ap42_gas_emission_rate(-1.0, 10.0)
    assert math.isfinite(gas_boiler_emissions(0.0)["NO2"])
