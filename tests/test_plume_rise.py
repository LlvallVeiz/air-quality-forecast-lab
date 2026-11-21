"""Tests for Briggs plume rise.

Reference values
----------------
- Worked example from the Mustansiriyah lecture notes on plume rise:
  buoyancy flux F = 50 m^4/s^3, wind at stack height u = 4.92 m/s,
  slightly unstable air -> final rise 81.78 m (xf = 565 m).
- Buoyancy flux hand check: vs = 15 m/s, d = 2 m, Ts = 423 K,
  Ta = 293 K -> Fb = 9.81*15*4*130/(4*423) = 45.21 m^4/s^3.
"""

import math

import pytest

from aqflab.plume_rise import (
    buoyant_rise_stable,
    buoyant_rise_unstable,
    buoyancy_flux,
    calm_rise_buoyant,
    calm_rise_jet,
    crossover_delta_t,
    final_rise_distance_buoyant,
    is_buoyant,
    momentum_flux,
    momentum_rise_stable,
    momentum_rise_unstable,
    plume_rise,
    stack_tip_downwash,
)


def test_buoyancy_flux_hand_value():
    fb = buoyancy_flux(15.0, 2.0, 423.15, 293.15)
    expected = 9.81 * 15.0 * 4.0 * 130.0 / (4.0 * 423.15)
    assert fb == pytest.approx(expected, rel=1e-12)
    assert fb == pytest.approx(45.21, abs=0.01)


def test_buoyancy_flux_zero_when_stack_not_hotter():
    assert buoyancy_flux(15.0, 2.0, 293.15, 293.15) == 0.0
    assert buoyancy_flux(15.0, 2.0, 283.15, 293.15) == 0.0


def test_momentum_flux_hand_value():
    fm = momentum_flux(15.0, 2.0, 423.15, 293.15)
    expected = 15.0 ** 2 * 4.0 * 293.15 / (4.0 * 423.15)
    assert fm == pytest.approx(expected, rel=1e-12)


def test_final_rise_distance_buoyant():
    # xf = 49 * F^(5/8) for F < 55: 49 * 50^0.625 = 564.8 m.
    assert final_rise_distance_buoyant(50.0) == pytest.approx(
        49.0 * 50.0 ** (5.0 / 8.0), rel=1e-12)
    # xf = 119 * F^(2/5) for F >= 55.
    assert final_rise_distance_buoyant(100.0) == pytest.approx(
        119.0 * 100.0 ** 0.4, rel=1e-12)


def test_buoyant_rise_worked_example():
    # Lecture worked example: F = 50, u = 4.92 m/s -> dh = 81.78 m
    # (the notes round intermediate values; the direct formula gives
    # 81.88 m, within 0.15 m of the printed value).
    rise = buoyant_rise_unstable(50.0, 4.92)
    assert rise == pytest.approx(81.78, abs=0.15)


def test_buoyant_rise_matches_closed_form():
    # dh = 1.6*F^(1/3)*xf^(2/3)/u must equal 21.425*F^0.75/u (F < 55)
    # and 38.71*F^0.6/u (F >= 55).
    for f, coef, exp in ((30.0, 21.425, 0.75), (100.0, 38.71, 0.6)):
        assert buoyant_rise_unstable(f, 5.0) == pytest.approx(
            coef * f ** exp / 5.0, rel=0.01)


def test_buoyant_rise_gradual_smaller_than_final():
    final = buoyant_rise_unstable(50.0, 5.0)
    gradual = buoyant_rise_unstable(50.0, 5.0, distance=100.0)
    assert 0 < gradual < final
    assert buoyant_rise_unstable(50.0, 5.0, distance=10000.0) == \
        pytest.approx(final)


def test_momentum_rise_unstable_hand_value():
    # dh = 3 * d^(2/3) * (vs/u)^(1/3): d=2, vs=15, u=5 -> 6.87 m.
    assert momentum_rise_unstable(15.0, 2.0, 5.0) == pytest.approx(
        3.0 * 2.0 ** (2.0 / 3.0) * 3.0 ** (1.0 / 3.0), rel=1e-12)


def test_crossover_decides_buoyant_vs_momentum():
    # Hot stack (dT = 130 K) is buoyant; cold stack is momentum.
    assert is_buoyant(423.15, 293.15, 15.0, 2.0, 45.22) is True
    assert is_buoyant(293.15, 293.15, 15.0, 2.0, 0.0) is False
    # Crossover dT for F < 55 uses the 0.0297 coefficient.
    dtc = crossover_delta_t(423.15, 15.0, 2.0, 45.22, stable=False)
    assert dtc == pytest.approx(
        0.0297 * 423.15 * 15.0 ** (2.0 / 3.0) / 2.0 ** (1.0 / 3.0),
        rel=1e-12)


def test_buoyant_rise_stable_is_min_of_windy_and_calm():
    s = 9.81 / 293.15 * 0.02
    windy = 2.6 * (50.0 / (5.0 * s)) ** (1.0 / 3.0)
    calm = 5.0 * 50.0 ** 0.25 * s ** (-3.0 / 8.0)
    assert buoyant_rise_stable(50.0, 5.0, s) == pytest.approx(
        min(windy, calm), rel=1e-12)
    assert buoyant_rise_stable(50.0, 5.0, s) == pytest.approx(
        windy, rel=1e-9)  # windy < calm here


def test_momentum_rise_stable_hand_value():
    fm = momentum_flux(15.0, 2.0, 423.15, 293.15)
    s = 9.81 / 293.15 * 0.02
    expected = 1.5 * fm ** (1.0 / 3.0) * s ** (-1.0 / 6.0) \
        / 5.0 ** (1.0 / 3.0)
    assert momentum_rise_stable(fm, 5.0, s) == pytest.approx(
        expected, rel=1e-12)


def test_calm_rise_formulas():
    s = 9.81 / 293.15 * 0.035
    assert calm_rise_buoyant(50.0, s) == pytest.approx(
        5.0 * 50.0 ** 0.25 * s ** (-3.0 / 8.0), rel=1e-12)
    fm = momentum_flux(15.0, 2.0, 423.15, 293.15)
    assert calm_rise_jet(fm, s) == pytest.approx(
        4.0 * fm ** 0.25 * s ** (-0.25), rel=1e-12)


def test_stack_tip_downwash():
    # vs = 5, u = 5, d = 2 -> 2*d*(1.5 - 1) = 2.0 m.
    assert stack_tip_downwash(5.0, 2.0, 5.0) == pytest.approx(2.0)
    # vs >= 1.5*u -> no downwash.
    assert stack_tip_downwash(10.0, 2.0, 5.0) == 0.0
    assert stack_tip_downwash(7.5, 2.0, 5.0) == 0.0


def test_plume_rise_integration_hot_stack_class_d():
    result = plume_rise(45.0, 18.0, 2.0, 453.15, 298.15, 5.0, "D")
    assert result["regime"] == "buoyant"
    assert result["rise"] > 0
    assert result["effective_height"] == pytest.approx(
        45.0 + result["rise"] - result["downwash"])
    assert result["final_rise_distance"] is not None


def test_plume_rise_stable_class_f_uses_stable_formulas():
    result = plume_rise(45.0, 18.0, 2.0, 453.15, 298.15, 5.0, "F")
    assert result["regime"] == "buoyant"
    # Stable air caps the rise below the unstable value.
    unstable = plume_rise(45.0, 18.0, 2.0, 453.15, 298.15, 5.0, "D")
    assert result["rise"] < unstable["rise"]


def test_plume_rise_invalid_inputs():
    with pytest.raises(ValueError):
        plume_rise(45.0, 18.0, 2.0, 453.15, 298.15, 0.0, "D")
    with pytest.raises(ValueError):
        buoyant_rise_unstable(0.0, 5.0)
    with pytest.raises(ValueError):
        momentum_rise_unstable(15.0, 0.0, 5.0)
    with pytest.raises(ValueError):
        buoyancy_flux(15.0, 2.0, -5.0, 293.15)
    assert math.isfinite(plume_rise(0.0, 0.0, 1.0, 300.0, 300.0,
                                     3.0, "D")["rise"])
