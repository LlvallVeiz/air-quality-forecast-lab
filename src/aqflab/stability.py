"""Atmospheric stability: Pasquill-Gifford classes, Turner method,
wind-profile power law and screening mixing heights.

Sources
-------
- Pasquill (1961) and Gifford (1961) stability classes A-F, as used by
  US EPA screening models (SCREEN3, ISC3).
- Turner (1964) stability classification from surface wind speed,
  solar insolation and cloud cover, as reproduced in Beychok (2005)
  and in EPA's SCREEN3 documentation.
- Wind-profile power-law exponents: ISC3 (EPA-454/B-95-003) rural and
  urban values.
- Potential-temperature gradients for stable classes (0.02 K/m for E,
  0.035 K/m for F) are the SCREEN3 defaults used in the Briggs
  stability parameter.
"""

from aqflab.constants import GRAVITY

STABILITY_CLASSES = ("A", "B", "C", "D", "E", "F")

CLASS_DESCRIPTIONS = {
    "A": "Extremely unstable",
    "B": "Moderately unstable",
    "C": "Slightly unstable",
    "D": "Neutral",
    "E": "Slightly stable",
    "F": "Moderately stable",
}

# ISC3 wind-profile power-law exponents, by stability class.
WIND_EXPONENT_RURAL = {"A": 0.10, "B": 0.15, "C": 0.20,
                       "D": 0.25, "E": 0.30, "F": 0.30}
WIND_EXPONENT_URBAN = {"A": 0.15, "B": 0.15, "C": 0.20,
                       "D": 0.25, "E": 0.30, "F": 0.30}

# Screening mixing heights (m). Typical climatological values in the
# Holzworth tradition; used only when a mixing-layer cap is requested.
# They are NOT measurements for any real city.
MIXING_HEIGHT_SCREENING = {"A": 1500.0, "B": 1200.0, "C": 1000.0,
                           "D": 800.0, "E": 400.0, "F": 200.0}

# Potential-temperature gradient d(theta)/dz (K/m) for stable classes
# (SCREEN3 defaults).
DTheta_DZ_STABLE = {"E": 0.02, "F": 0.035}

# Turner (1964) table. Rows keyed by surface wind speed (m/s);
# columns are daytime insolation (strong / moderate / slight) and
# nighttime cloud cover (>= 4/8 / <= 3/8). Intermediate entries such
# as "A-B" are resolved to the more stable letter (B), the common
# conservative choice for screening; the resolution is documented
# wherever it is applied.
_TURNER_DAY = {
    (0.0, 2.0): ("A", "A-B", "B"),
    (2.0, 3.0): ("A-B", "B", "C"),
    (3.0, 5.0): ("B", "B-C", "C"),
    (5.0, 6.0): ("C", "C-D", "D"),
    (6.0, float("inf")): ("C", "D", "D"),
}
_TURNER_NIGHT = {
    (0.0, 2.0): ("E", "F"),
    (2.0, 3.0): ("E", "F"),
    (3.0, 5.0): ("D", "E"),
    (5.0, 6.0): ("D", "D"),
    (6.0, float("inf")): ("D", "D"),
}
_INSULATION_INDEX = {"strong": 0, "moderate": 1, "slight": 2}


def _resolve(entry):
    """Resolve an intermediate Turner entry (e.g. "A-B") to one class.

    The more stable letter is chosen (B for "A-B"), the conservative
    screening choice: less dispersion, higher ground-level values.
    """
    if "-" in entry:
        return entry.split("-")[1]
    return entry


def _wind_row(wind_speed):
    for (lo, hi), value in _TURNER_DAY.items():
        if lo <= wind_speed < hi:
            return value
    raise ValueError("wind_speed must be >= 0")


def turner_class(wind_speed, is_day, insolation="moderate",
                 cloud_octas=4):
    """Pasquill-Gifford stability class by Turner's method.

    Parameters
    ----------
    wind_speed : float
        Surface (10 m) wind speed in m/s, must be >= 0.
    is_day : bool
        True for daytime, False for nighttime.
    insolation : {"strong", "moderate", "slight"}
        Daytime solar insolation class (ignored at night).
    cloud_octas : int
        Nighttime cloud cover in octas (0-8); >= 4 means mostly
        cloudy. Ignored during the day.

    Returns
    -------
    str
        One of "A".."F".
    """
    if wind_speed < 0:
        raise ValueError("wind_speed must be >= 0")
    if is_day:
        if insolation not in _INSULATION_INDEX:
            raise ValueError("insolation must be strong/moderate/slight")
        row = _wind_row(wind_speed)
        return _resolve(row[_INSULATION_INDEX[insolation]])
    if not 0 <= cloud_octas <= 8:
        raise ValueError("cloud_octas must be 0..8")
    for (lo, hi), value in _TURNER_NIGHT.items():
        if lo <= wind_speed < hi:
            return _resolve(value[0] if cloud_octas >= 4 else value[1])
    raise ValueError("wind_speed must be >= 0")


def wind_profile_exponent(stability, urban=False):
    """Power-law wind-profile exponent p for a stability class.

    u(z) = u_ref * (z / z_ref) ** p (ISC3 exponents).
    """
    if stability not in STABILITY_CLASSES:
        raise ValueError(f"unknown stability class {stability!r}")
    table = WIND_EXPONENT_URBAN if urban else WIND_EXPONENT_RURAL
    return table[stability]


def wind_speed_at_height(u_ref, z_ref, z, stability, urban=False):
    """Wind speed at height z from a reference measurement.

    Parameters
    ----------
    u_ref : float
        Wind speed (m/s) measured at height ``z_ref`` (m).
    z : float
        Target height (m), must be > 0.
    """
    if z <= 0 or z_ref <= 0:
        raise ValueError("heights must be > 0")
    if u_ref < 0:
        raise ValueError("u_ref must be >= 0")
    p = wind_profile_exponent(stability, urban)
    return u_ref * (z / z_ref) ** p


def stability_parameter(temp_k, dtheta_dz):
    """Briggs stability parameter s = (g / T) * d(theta)/dz (1/s^2)."""
    if temp_k <= 0:
        raise ValueError("temp_k must be > 0")
    return GRAVITY / temp_k * dtheta_dz


def stability_parameter_for_class(stability, temp_k):
    """Stability parameter s for a stable class using SCREEN3 gradients.

    Only defined for classes E and F; raises ValueError otherwise.
    """
    if stability not in DTheta_DZ_STABLE:
        raise ValueError(
            f"stability parameter is only defined for stable classes "
            f"E/F, got {stability!r}")
    return stability_parameter(temp_k, DTheta_DZ_STABLE[stability])


def mixing_height(stability):
    """Screening mixing height (m) for a stability class.

    Typical climatological values only; not a measurement.
    """
    if stability not in STABILITY_CLASSES:
        raise ValueError(f"unknown stability class {stability!r}")
    return MIXING_HEIGHT_SCREENING[stability]
