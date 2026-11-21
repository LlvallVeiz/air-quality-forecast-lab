"""Gaussian plume dispersion with Briggs (1973) dispersion coefficients.

The steady-state Gaussian plume equation for a continuous point source
with total ground reflection (method of images):

    C(x, y, z) = Q / (2*pi*u*sy*sz) * exp(-y^2 / (2*sy^2))
                 * [exp(-(z-H)^2 / (2*sz^2)) + exp(-(z+H)^2 / (2*sz^2))]

Ground-level centreline (y = 0, z = 0):

    C(x, 0, 0) = Q / (pi*u*sy*sz) * exp(-H^2 / (2*sz^2))

Dispersion coefficients are the Briggs (1973) formulas recommended in
Hanna, Briggs & Hosker, "Handbook on Atmospheric Diffusion"
(DOE/TIC-11223, 1982), Table 4.5, valid for 10^2 < x < 10^4 m:

Open country (rural), x in metres:
    A: sy = 0.22x(1+0.0001x)^-1/2   sz = 0.20x
    B: sy = 0.16x(1+0.0001x)^-1/2   sz = 0.12x
    C: sy = 0.11x(1+0.0001x)^-1/2   sz = 0.08x(1+0.0002x)^-1/2
    D: sy = 0.08x(1+0.0001x)^-1/2   sz = 0.06x(1+0.0015x)^-1/2
    E: sy = 0.06x(1+0.0001x)^-1/2   sz = 0.03x(1+0.0003x)^-1
    F: sy = 0.04x(1+0.0001x)^-1/2   sz = 0.016x(1+0.0003x)^-1
Urban:
    A-B: sy = 0.32x(1+0.0004x)^-1/2  sz = 0.24x(1+0.001x)^1/2
    C:   sy = 0.22x(1+0.0004x)^-1/2  sz = 0.20x
    D:   sy = 0.16x(1+0.0004x)^-1/2  sz = 0.14x(1+0.0003x)^-1/2
    E-F: sy = 0.11x(1+0.0004x)^-1/2  sz = 0.08x(1+0.0015x)^-1/2

An optional mixing-height cap is available: extra image sources are
added at +/- 2*n*hm (Beychok 1994, p. 123).
"""

import math

from aqflab.stability import STABILITY_CLASSES

# (sy_coef, sy_x_coef, sy_exp, sz_coef, sz_x_coef, sz_exp)
# sy = a*x*(1+b*x)^c ; sz = d*x*(1+e*x)^f
_BRIGGS_RURAL = {
    "A": (0.22, 0.0001, -0.5, 0.20, 0.0, 0.0),
    "B": (0.16, 0.0001, -0.5, 0.12, 0.0, 0.0),
    "C": (0.11, 0.0001, -0.5, 0.08, 0.0002, -0.5),
    "D": (0.08, 0.0001, -0.5, 0.06, 0.0015, -0.5),
    "E": (0.06, 0.0001, -0.5, 0.03, 0.0003, -1.0),
    "F": (0.04, 0.0001, -0.5, 0.016, 0.0003, -1.0),
}
_BRIGGS_URBAN = {
    "A": (0.32, 0.0004, -0.5, 0.24, 0.001, 0.5),
    "B": (0.32, 0.0004, -0.5, 0.24, 0.001, 0.5),
    "C": (0.22, 0.0004, -0.5, 0.20, 0.0, 0.0),
    "D": (0.16, 0.0004, -0.5, 0.14, 0.0003, -0.5),
    "E": (0.11, 0.0004, -0.5, 0.08, 0.0015, -0.5),
    "F": (0.11, 0.0004, -0.5, 0.08, 0.0015, -0.5),
}

VALID_RANGE = (100.0, 10000.0)  # metres; Briggs formula range


def _check_inputs(x, stability):
    if stability not in STABILITY_CLASSES:
        raise ValueError(f"unknown stability class {stability!r}")
    if x < 0:
        raise ValueError("downwind distance x must be >= 0")


def sigma_y(x, stability, urban=False):
    """Briggs lateral dispersion coefficient sigma-y (m)."""
    _check_inputs(x, stability)
    if x == 0:
        return 0.0
    a, b, c, _d, _e, _f = (
        _BRIGGS_URBAN if urban else _BRIGGS_RURAL)[stability]
    return a * x * (1.0 + b * x) ** c


def sigma_z(x, stability, urban=False):
    """Briggs vertical dispersion coefficient sigma-z (m)."""
    _check_inputs(x, stability)
    if x == 0:
        return 0.0
    _a, _b, _c, d, e, f = (
        _BRIGGS_URBAN if urban else _BRIGGS_RURAL)[stability]
    return d * x * (1.0 + e * x) ** f


def sigma_y_z(x, stability, urban=False):
    """(sigma-y, sigma-z) in metres at downwind distance x."""
    return sigma_y(x, stability, urban), sigma_z(x, stability, urban)


def gaussian_plume(emission_rate, wind_speed, x, y, z, height,
                   stability, urban=False, mixing_height=None,
                   n_reflections=3):
    """Gaussian plume concentration (g/m^3) at a receptor.

    Parameters
    ----------
    emission_rate : float
        Source strength Q in g/s.
    wind_speed : float
        Mean wind speed at release height in m/s; must be > 0.
    x, y, z : float
        Receptor coordinates (m): downwind, crosswind, height above
        ground. Receptors upwind (x <= 0) get zero concentration.
    height : float
        Effective release height H (m), i.e. stack height + plume rise.
    stability : str
        Pasquill-Gifford class "A".."F".
    urban : bool
        Use the Briggs urban coefficient set.
    mixing_height : float or None
        If given, add ground + mixing-height reflections (method of
        images, ``n_reflections`` pairs).
    """
    if wind_speed <= 0:
        raise ValueError("wind_speed must be > 0")
    if emission_rate < 0:
        raise ValueError("emission_rate must be >= 0")
    if emission_rate == 0.0 or x <= 0:
        return 0.0
    if stability not in STABILITY_CLASSES:
        raise ValueError(f"unknown stability class {stability!r}")
    sy, sz = sigma_y_z(x, stability, urban)
    cross = math.exp(-0.5 * (y / sy) ** 2)
    vertical = math.exp(-0.5 * ((z - height) / sz) ** 2) \
        + math.exp(-0.5 * ((z + height) / sz) ** 2)
    if mixing_height is not None:
        if mixing_height <= 0:
            raise ValueError("mixing_height must be > 0")
        hm = mixing_height
        for n in range(1, n_reflections + 1):
            vertical += math.exp(-0.5 * ((z - height + 2 * n * hm) / sz) ** 2) \
                + math.exp(-0.5 * ((z - height - 2 * n * hm) / sz) ** 2) \
                + math.exp(-0.5 * ((z + height + 2 * n * hm) / sz) ** 2) \
                + math.exp(-0.5 * ((z + height - 2 * n * hm) / sz) ** 2)
    return emission_rate / (2.0 * math.pi * wind_speed * sy * sz) \
        * cross * vertical


def ground_level_centerline(emission_rate, wind_speed, x, height,
                            stability, urban=False):
    """Ground-level centreline concentration (g/m^3) at distance x."""
    return gaussian_plume(emission_rate, wind_speed, x, 0.0, 0.0,
                          height, stability, urban=urban)


def peak_distance(emission_rate, wind_speed, height, stability,
                  urban=False, x_max=10000.0, step=10.0):
    """Downwind distance (m) of the ground-level centreline maximum.

    Scans the centreline on a regular grid; returns (x_peak, C_peak).
    """
    best_x, best_c = 0.0, 0.0
    x = step
    while x <= x_max:
        c = ground_level_centerline(emission_rate, wind_speed, x,
                                    height, stability, urban=urban)
        if c > best_c:
            best_x, best_c = x, c
        x += step
    return best_x, best_c
