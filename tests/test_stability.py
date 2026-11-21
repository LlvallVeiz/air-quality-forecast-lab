"""Tests for stability classes, Turner method and wind profile."""

import math

import pytest

from aqflab.stability import (
    STABILITY_CLASSES,
    mixing_height,
    stability_parameter,
    stability_parameter_for_class,
    turner_class,
    wind_profile_exponent,
    wind_speed_at_height,
)


def test_turner_daytime_strong_sun_light_wind_is_a():
    assert turner_class(1.0, True, "strong") == "A"


def test_turner_daytime_moderate_wind_4_is_c():
    # Row 3-5 m/s, moderate insolation = "B-C" -> resolved to "C".
    assert turner_class(4.0, True, "moderate") == "C"


def test_turner_daytime_strong_wind_is_d():
    assert turner_class(7.0, True, "strong") == "C"
    assert turner_class(7.0, True, "slight") == "D"


def test_turner_night_clear_is_f_cloudy_is_e():
    assert turner_class(1.0, False, cloud_octas=2) == "F"
    assert turner_class(1.0, False, cloud_octas=6) == "E"


def test_turner_night_strong_wind_is_d():
    assert turner_class(6.5, False, cloud_octas=0) == "D"


def test_turner_invalid_inputs_raise():
    with pytest.raises(ValueError):
        turner_class(-1.0, True)
    with pytest.raises(ValueError):
        turner_class(2.0, True, "blazing")
    with pytest.raises(ValueError):
        turner_class(2.0, False, cloud_octas=9)


def test_wind_profile_class_d_rural():
    # u(50 m) from u(10 m) = 5 m/s, class D rural p = 0.25:
    # 5 * 5**0.25 = 7.4766 m/s (hand calculation).
    assert wind_speed_at_height(5.0, 10.0, 50.0, "D") == pytest.approx(
        5.0 * 5.0 ** 0.25, rel=1e-12)
    assert wind_profile_exponent("D", urban=False) == 0.25
    assert wind_profile_exponent("A", urban=True) == 0.15
    assert wind_profile_exponent("A", urban=False) == 0.10


def test_wind_profile_invalid():
    with pytest.raises(ValueError):
        wind_speed_at_height(5.0, 10.0, 0.0, "D")
    with pytest.raises(ValueError):
        wind_speed_at_height(5.0, 10.0, 50.0, "G")


def test_stability_parameter():
    # s = g/T * d(theta)/dz = 9.81/293 * 0.02 = 6.696e-4 1/s^2.
    assert stability_parameter(293.15, 0.02) == pytest.approx(
        9.81 / 293.15 * 0.02, rel=1e-12)
    assert stability_parameter_for_class("E", 293.15) == pytest.approx(
        9.81 / 293.15 * 0.02, rel=1e-12)
    assert stability_parameter_for_class("F", 293.15) == pytest.approx(
        9.81 / 293.15 * 0.035, rel=1e-12)
    with pytest.raises(ValueError):
        stability_parameter_for_class("D", 293.15)


def test_mixing_height_screening_values():
    assert mixing_height("F") == 200.0
    assert mixing_height("A") == 1500.0
    assert mixing_height("D") == 800.0
    with pytest.raises(ValueError):
        mixing_height("Z")
    assert len(STABILITY_CLASSES) == 6


def test_wind_speed_increases_with_height_unstable():
    assert wind_speed_at_height(3.0, 10.0, 100.0, "A") > 3.0
    assert wind_speed_at_height(3.0, 10.0, 100.0, "F") > \
        wind_speed_at_height(3.0, 10.0, 100.0, "A")
    assert math.isclose(wind_speed_at_height(3.0, 10.0, 10.0, "C"), 3.0)
