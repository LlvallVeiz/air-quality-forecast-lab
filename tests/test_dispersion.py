"""Tests for Gaussian plume dispersion (Briggs sigma formulas).

Reference values (hand calculation, class D rural, x = 1000 m):
    sy = 0.08*1000*(1+0.0001*1000)^(-1/2) = 76.28 m
    sz = 0.06*1000*(1+0.0015*1000)^(-1/2) = 37.95 m
    C(1000, 0, 0) for Q = 10 g/s, u = 5 m/s, H = 50 m:
    C = 10 / (pi*5*sy*sz) * exp(-50^2 / (2*sz^2)) = 92.31 ug/m^3.
The expected values below are computed with plain arithmetic in the
test itself, never through the module under test.
"""

import math

import pytest

from aqflab.dispersion import (
    gaussian_plume,
    ground_level_centerline,
    peak_distance,
    sigma_y,
    sigma_z,
    sigma_y_z,
)


def test_sigma_y_z_class_d_rural_hand_values():
    sy = 0.08 * 1000.0 * (1.0 + 0.0001 * 1000.0) ** (-0.5)
    sz = 0.06 * 1000.0 * (1.0 + 0.0015 * 1000.0) ** (-0.5)
    assert sigma_y(1000.0, "D") == pytest.approx(sy, rel=1e-12)
    assert sigma_z(1000.0, "D") == pytest.approx(sz, rel=1e-12)
    assert sy == pytest.approx(76.28, abs=0.01)
    assert sz == pytest.approx(37.95, abs=0.01)


def test_sigma_urban_a_at_1000m():
    sy = 0.32 * 1000.0 * (1.0 + 0.0004 * 1000.0) ** (-0.5)
    sz = 0.24 * 1000.0 * (1.0 + 0.001 * 1000.0) ** 0.5
    assert sigma_y(1000.0, "A", urban=True) == pytest.approx(
        sy, rel=1e-12)
    assert sigma_z(1000.0, "A", urban=True) == pytest.approx(
        sz, rel=1e-12)
    # Urban dispersion is stronger than rural for the same class.
    assert sigma_y(1000.0, "A", urban=True) > sigma_y(1000.0, "A")
    assert sigma_z(1000.0, "A", urban=True) > sigma_z(1000.0, "A")


def test_sigma_grows_with_distance_and_instability():
    for cls in ("A", "B", "C", "D", "E", "F"):
        assert sigma_y(2000.0, cls) > sigma_y(1000.0, cls)
        assert sigma_z(2000.0, cls) > sigma_z(1000.0, cls)
    assert sigma_y(1000.0, "A") > sigma_y(1000.0, "F")
    assert sigma_z(1000.0, "A") > sigma_z(1000.0, "F")


def test_sigma_y_z_tuple_matches_singles():
    assert sigma_y_z(500.0, "C") == (sigma_y(500.0, "C"),
                                     sigma_z(500.0, "C"))


def test_sigma_zero_distance_and_invalid():
    assert sigma_y(0.0, "D") == 0.0
    assert sigma_z(0.0, "D") == 0.0
    with pytest.raises(ValueError):
        sigma_y(-10.0, "D")
    with pytest.raises(ValueError):
        sigma_z(100.0, "G")


def test_ground_level_centerline_hand_value():
    sy = 0.08 * 1000.0 * (1.0 + 0.0001 * 1000.0) ** (-0.5)
    sz = 0.06 * 1000.0 * (1.0 + 0.0015 * 1000.0) ** (-0.5)
    expected_g_m3 = 10.0 / (math.pi * 5.0 * sy * sz) * math.exp(
        -50.0 ** 2 / (2.0 * sz ** 2))
    result = ground_level_centerline(10.0, 5.0, 1000.0, 50.0, "D")
    assert result == pytest.approx(expected_g_m3, rel=1e-12)
    assert result * 1e6 == pytest.approx(92.31, abs=0.05)


def test_ground_level_centerline_scales_linearly_with_q():
    c1 = ground_level_centerline(10.0, 5.0, 1000.0, 50.0, "D")
    c2 = ground_level_centerline(20.0, 5.0, 1000.0, 50.0, "D")
    assert c2 == pytest.approx(2.0 * c1, rel=1e-12)


def test_higher_stack_lowers_ground_concentration():
    low = ground_level_centerline(10.0, 5.0, 1000.0, 20.0, "D")
    high = ground_level_centerline(10.0, 5.0, 1000.0, 80.0, "D")
    assert high < low


def test_gaussian_plume_matches_centerline_on_axis():
    value = gaussian_plume(10.0, 5.0, 1000.0, 0.0, 0.0, 50.0, "D")
    assert value == pytest.approx(
        ground_level_centerline(10.0, 5.0, 1000.0, 50.0, "D"))


def test_gaussian_plume_falls_off_crosswind():
    centre = gaussian_plume(10.0, 5.0, 1000.0, 0.0, 0.0, 50.0, "D")
    off = gaussian_plume(10.0, 5.0, 1000.0, 200.0, 0.0, 50.0, "D")
    assert 0 < off < centre


def test_gaussian_plume_ground_reflection_doubles_surface_value():
    # At z = 0 the image term equals the direct term, so the
    # ground-level value is twice the no-reflection value.
    with_reflection = gaussian_plume(10.0, 5.0, 1000.0, 0.0, 0.0,
                                     50.0, "D")
    sy, sz = sigma_y_z(1000.0, "D")
    no_reflection = 10.0 / (2.0 * math.pi * 5.0 * sy * sz) * math.exp(
        -50.0 ** 2 / (2.0 * sz ** 2))
    assert with_reflection == pytest.approx(2.0 * no_reflection,
                                            rel=1e-12)


def test_edge_cases_zero_and_upwind():
    assert ground_level_centerline(0.0, 5.0, 1000.0, 50.0, "D") == 0.0
    assert ground_level_centerline(10.0, 5.0, 0.0, 50.0, "D") == 0.0
    assert gaussian_plume(10.0, 5.0, -100.0, 0.0, 0.0, 50.0, "D") == 0.0
    with pytest.raises(ValueError):
        ground_level_centerline(10.0, 0.0, 1000.0, 50.0, "D")
    with pytest.raises(ValueError):
        ground_level_centerline(-5.0, 5.0, 1000.0, 50.0, "D")


def test_mixing_height_caps_vertical_spread():
    capped = gaussian_plume(10.0, 5.0, 5000.0, 0.0, 0.0, 50.0, "D",
                            mixing_height=300.0)
    uncapped = gaussian_plume(10.0, 5.0, 5000.0, 0.0, 0.0, 50.0, "D")
    # Extra reflections can only add mass at the ground.
    assert capped > uncapped


def test_peak_distance_is_downwind_and_finite():
    x_peak, c_peak = peak_distance(10.0, 5.0, 50.0, "D")
    assert 100.0 < x_peak < 10000.0
    assert c_peak > ground_level_centerline(10.0, 5.0, 100.0, 50.0,
                                            "D")
    assert c_peak > ground_level_centerline(10.0, 5.0, 9000.0, 50.0,
                                            "D")
