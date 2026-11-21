"""Briggs plume rise.

Implements the Briggs (1969, 1971, 1972) plume-rise scheme as used by
US EPA screening models (SCREEN3, ISC3) and documented in Beychok
(2005) "Fundamentals of Stack Gas Dispersion" and in the Briggs
plume-rise summary of the Georgia Tech / Mustansiriyah lecture
material (worked example: buoyancy flux F = 50 m^4/s^3 gives a final
rise of 81.78 m at u = 4.92 m/s).

Definitions
-----------
Buoyancy flux  Fb = g * vs * d^2 * (Ts - Ta) / (4 * Ts)   [m^4/s^3]
Momentum flux Fm = vs^2 * d^2 * Ta / (4 * Ts)            [m^4/s^2]

Unstable/neutral (classes A-D), buoyant plume:
    xf = 49 * Fb^(5/8)            if Fb < 55 m^4/s^3
    xf = 119 * Fb^(2/5)           if Fb >= 55 m^4/s^3
    dh(x) = 1.6 * Fb^(1/3) * min(x, xf)^(2/3) / u
    (final rise: 21.425 * Fb^0.75 / u for Fb < 55,
                 38.71 * Fb^0.6 / u  for Fb >= 55)
Unstable/neutral, momentum-dominated plume:
    dh = 3 * d^(2/3) * (vs / u)^(1/3)
Stable (classes E-F), buoyant plume:
    dh = min(2.6 * (Fb / (u * s))^(1/3), 5 * Fb^(1/4) * s^(-3/8))
Stable, momentum-dominated plume:
    dh = 1.5 * Fm^(1/3) * s^(-1/6) / u^(1/3)
Calm (u < 1 m/s), buoyant plume: dh = 5 * Fb^(1/4) * s^(-3/8)
Calm jet: dh = 4 * Fm^(1/4) * s^(-1/4)

Buoyancy vs momentum is decided with the crossover temperature
difference dTc (SCREEN3): dTc = 0.0297 * Ts * vs^(2/3) / d^(1/3)
for unstable/neutral with Fb < 55, otherwise
dTc = 0.00575 * Ts * vs^(2/3) / d^(1/3). The plume is buoyant when
Ts - Ta >= dTc.

Stack-tip downwash (Briggs): if vs < 1.5 * u the effective height is
reduced by 2 * d * (1.5 - vs / u).
"""


from aqflab.constants import GRAVITY
from aqflab.stability import stability_parameter_for_class

BUOYANCY_THRESHOLD = 55.0  # m^4/s^3, Briggs Fb split point
CALM_WIND = 1.0  # m/s; below this the calm formulas apply


def buoyancy_flux(exit_velocity, diameter, stack_temp_k, ambient_temp_k):
    """Briggs buoyancy flux parameter Fb (m^4/s^3)."""
    if exit_velocity < 0 or diameter <= 0:
        raise ValueError("exit_velocity >= 0 and diameter > 0 required")
    if stack_temp_k <= 0 or ambient_temp_k <= 0:
        raise ValueError("temperatures must be > 0 K")
    delta_t = stack_temp_k - ambient_temp_k
    if delta_t <= 0:
        return 0.0
    return (GRAVITY * exit_velocity * diameter ** 2 * delta_t
            / (4.0 * stack_temp_k))


def momentum_flux(exit_velocity, diameter, stack_temp_k, ambient_temp_k):
    """Briggs momentum flux parameter Fm (m^4/s^2)."""
    if exit_velocity < 0 or diameter <= 0:
        raise ValueError("exit_velocity >= 0 and diameter > 0 required")
    if stack_temp_k <= 0 or ambient_temp_k <= 0:
        raise ValueError("temperatures must be > 0 K")
    return (exit_velocity ** 2 * diameter ** 2 * ambient_temp_k
            / (4.0 * stack_temp_k))


def crossover_delta_t(stack_temp_k, exit_velocity, diameter,
                      buoyancy_flux_value, stable=False):
    """Crossover temperature difference dTc (K, SCREEN3 form)."""
    if diameter <= 0 or exit_velocity < 0:
        raise ValueError("diameter > 0 and exit_velocity >= 0 required")
    if stable or buoyancy_flux_value >= BUOYANCY_THRESHOLD:
        coef = 0.00575
    else:
        coef = 0.0297
    return coef * stack_temp_k * exit_velocity ** (2.0 / 3.0) \
        / diameter ** (1.0 / 3.0)


def is_buoyant(stack_temp_k, ambient_temp_k, exit_velocity, diameter,
               buoyancy_flux_value, stable=False):
    """True when the plume is buoyancy-dominated (dT >= dTc)."""
    dtc = crossover_delta_t(stack_temp_k, exit_velocity, diameter,
                            buoyancy_flux_value, stable=stable)
    return (stack_temp_k - ambient_temp_k) >= dtc


def final_rise_distance_buoyant(buoyancy_flux_value):
    """Downwind distance xf (m) to final rise, unstable/neutral."""
    if buoyancy_flux_value <= 0:
        raise ValueError("buoyancy flux must be > 0")
    if buoyancy_flux_value < BUOYANCY_THRESHOLD:
        return 49.0 * buoyancy_flux_value ** (5.0 / 8.0)
    return 119.0 * buoyancy_flux_value ** (2.0 / 5.0)


def buoyant_rise_unstable(buoyancy_flux_value, wind_speed, distance=None):
    """Briggs buoyant rise (m) in unstable/neutral air.

    If ``distance`` is given, the gradual (distance-dependent) rise is
    returned; otherwise the final rise.
    """
    if buoyancy_flux_value <= 0:
        raise ValueError("buoyancy flux must be > 0")
    if wind_speed <= 0:
        raise ValueError("wind_speed must be > 0")
    xf = final_rise_distance_buoyant(buoyancy_flux_value)
    x = xf if distance is None else min(distance, xf)
    if x <= 0:
        return 0.0
    return 1.6 * buoyancy_flux_value ** (1.0 / 3.0) * x ** (2.0 / 3.0) \
        / wind_speed


def momentum_rise_unstable(exit_velocity, diameter, wind_speed):
    """Briggs momentum rise (m) in unstable/neutral air."""
    if exit_velocity < 0 or diameter <= 0 or wind_speed <= 0:
        raise ValueError("exit_velocity >= 0, diameter > 0, wind > 0")
    return 3.0 * diameter ** (2.0 / 3.0) \
        * (exit_velocity / wind_speed) ** (1.0 / 3.0)


def buoyant_rise_stable(buoyancy_flux_value, wind_speed, stab_param):
    """Briggs buoyant rise (m) in stable air: min(windy, calm)."""
    if buoyancy_flux_value <= 0 or wind_speed <= 0 or stab_param <= 0:
        raise ValueError("buoyancy flux, wind and s must be > 0")
    windy = 2.6 * (buoyancy_flux_value / (wind_speed * stab_param)) \
        ** (1.0 / 3.0)
    calm = 5.0 * buoyancy_flux_value ** 0.25 * stab_param ** (-3.0 / 8.0)
    return min(windy, calm)


def momentum_rise_stable(momentum_flux_value, wind_speed, stab_param):
    """Briggs momentum rise (m) in stable air (windy)."""
    if momentum_flux_value <= 0 or wind_speed <= 0 or stab_param <= 0:
        raise ValueError("momentum flux, wind and s must be > 0")
    return 1.5 * momentum_flux_value ** (1.0 / 3.0) \
        * stab_param ** (-1.0 / 6.0) / wind_speed ** (1.0 / 3.0)


def calm_rise_buoyant(buoyancy_flux_value, stab_param):
    """Briggs calm-air buoyant rise (m): 5 * Fb^(1/4) * s^(-3/8)."""
    if buoyancy_flux_value <= 0 or stab_param <= 0:
        raise ValueError("buoyancy flux and s must be > 0")
    return 5.0 * buoyancy_flux_value ** 0.25 * stab_param ** (-3.0 / 8.0)


def calm_rise_jet(momentum_flux_value, stab_param):
    """Briggs calm-air momentum-jet rise (m): 4 * Fm^(1/4) * s^(-1/4)."""
    if momentum_flux_value <= 0 or stab_param <= 0:
        raise ValueError("momentum flux and s must be > 0")
    return 4.0 * momentum_flux_value ** 0.25 * stab_param ** (-0.25)


def stack_tip_downwash(exit_velocity, diameter, wind_speed):
    """Briggs stack-tip downwash correction (m) to subtract from height.

    Applies when vs < 1.5 * u: 2 * d * (1.5 - vs / u); otherwise 0.
    """
    if diameter <= 0 or wind_speed <= 0:
        raise ValueError("diameter > 0 and wind_speed > 0 required")
    if exit_velocity >= 1.5 * wind_speed:
        return 0.0
    return 2.0 * diameter * (1.5 - exit_velocity / wind_speed)


def plume_rise(stack_height, exit_velocity, diameter, stack_temp_k,
               ambient_temp_k, wind_speed, stability, distance=None,
               apply_downwash=True):
    """Full Briggs plume rise for one stack under given conditions.

    Parameters
    ----------
    stack_height : float
        Physical stack height (m).
    exit_velocity, diameter : float
        Stack gas exit velocity (m/s) and inside diameter (m).
    stack_temp_k, ambient_temp_k : float
        Stack gas and ambient absolute temperatures (K).
    wind_speed : float
        Mean wind speed at stack height (m/s); must be > 0.
    stability : str
        Pasquill-Gifford class "A".."F".
    distance : float or None
        Downwind distance (m) for the gradual rise in
        unstable/neutral air; None returns the final rise.
    apply_downwash : bool
        Apply the Briggs stack-tip downwash correction.

    Returns
    -------
    dict
        buoyancy_flux, momentum_flux, regime ("buoyant"/"momentum"),
        rise (m), downwash (m), effective_height (m) and, for
        unstable/neutral buoyant plumes, the final-rise distance xf.
    """
    if stack_height < 0:
        raise ValueError("stack_height must be >= 0")
    if wind_speed <= 0:
        raise ValueError("wind_speed must be > 0 (calm air is handled "
                         "by the caller with a minimum wind)")
    stable = stability in ("E", "F")
    fb = buoyancy_flux(exit_velocity, diameter, stack_temp_k,
                       ambient_temp_k)
    fm = momentum_flux(exit_velocity, diameter, stack_temp_k,
                       ambient_temp_k)
    buoyant = is_buoyant(stack_temp_k, ambient_temp_k, exit_velocity,
                         diameter, fb, stable=stable)
    result = {"buoyancy_flux": fb, "momentum_flux": fm,
              "regime": "buoyant" if buoyant else "momentum",
              "final_rise_distance": None}
    if fb <= 0.0 and fm <= 0.0:
        # No buoyancy and no momentum (e.g. exit velocity zero):
        # the plume does not rise above the stack.
        rise = 0.0
        result["regime"] = "none"
    elif wind_speed < CALM_WIND and stable:
        s = stability_parameter_for_class(stability, ambient_temp_k)
        rise = (calm_rise_buoyant(fb, s) if buoyant
                else calm_rise_jet(fm, s))
        result["regime"] += " (calm)"
    elif stable:
        s = stability_parameter_for_class(stability, ambient_temp_k)
        if buoyant and fb > 0.0:
            rise = buoyant_rise_stable(fb, wind_speed, s)
        elif not buoyant and fm > 0.0:
            rise = momentum_rise_stable(fm, wind_speed, s)
        else:
            rise = 0.0
    elif buoyant and fb > 0.0:
        rise = buoyant_rise_unstable(fb, wind_speed, distance=distance)
        result["final_rise_distance"] = \
            final_rise_distance_buoyant(fb)
    elif not buoyant and fm > 0.0:
        rise = momentum_rise_unstable(exit_velocity, diameter,
                                      wind_speed)
    else:
        rise = 0.0
    downwash = 0.0
    if apply_downwash and exit_velocity > 0:
        # No exit flow means no jet to be downwashed.
        downwash = stack_tip_downwash(exit_velocity, diameter,
                                      wind_speed)
    effective = max(stack_height + rise - downwash, 0.0)
    result.update({"rise": rise, "downwash": downwash,
                   "effective_height": effective})
    return result


def effective_stack_height(*args, **kwargs):
    """Convenience wrapper returning only the effective height (m)."""
    return plume_rise(*args, **kwargs)["effective_height"]
