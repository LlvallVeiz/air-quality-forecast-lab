"""Meteorology: synthetic but realistic diurnal conditions.

The meteorology in this package is SYNTHETIC. It is built from
textbook diurnal patterns (stable night, unstable day, wind-speed
cycle) and is used to drive the dispersion and forecast models for a
fictional city. It is not observations from any real city, and no
result here is a claim about real-world air quality anywhere.

Three named scenarios are provided:

- ``calm_morning`` -- light wind (1 m/s), class F at dawn turning to
  D by mid-morning: weak dispersion, high ground-level impact.
- ``windy_noon`` -- 6 m/s, class B/C, strong mixing: low impact.
- ``night_inversion`` -- 1.5 m/s, class F all night, low mixing
  height (200 m): trapped plume, worst case for a low stack.

Wind direction is the direction the wind blows TOWARD, in degrees
clockwise from north (0 = toward north, 90 = toward east).
"""

import math
import random

from aqflab.stability import STABILITY_CLASSES

# Nominal hourly patterns: (hour, wind_10m, stability, temp_c,
# mixing height m) anchor points; linear interpolation between them.
_SCENARIO_ANCHORS = {
    "calm_morning": [
        (0, 1.0, "F", 24.0, 200.0),
        (6, 1.0, "F", 24.0, 200.0),
        (9, 1.5, "D", 27.0, 500.0),
        (12, 3.0, "C", 30.0, 1000.0),
        (15, 3.5, "C", 31.0, 1000.0),
        (18, 2.0, "D", 28.0, 600.0),
        (21, 1.2, "E", 25.0, 300.0),
        (24, 1.0, "F", 24.0, 200.0),
    ],
    "windy_noon": [
        (0, 3.0, "D", 25.0, 800.0),
        (6, 3.5, "D", 26.0, 800.0),
        (9, 5.0, "C", 29.0, 1200.0),
        (12, 6.0, "B", 32.0, 1500.0),
        (15, 6.0, "B", 33.0, 1500.0),
        (18, 5.0, "C", 30.0, 1200.0),
        (21, 4.0, "D", 27.0, 800.0),
        (24, 3.0, "D", 25.0, 800.0),
    ],
    "night_inversion": [
        (0, 1.5, "F", 23.0, 200.0),
        (6, 1.5, "F", 23.0, 200.0),
        (9, 2.0, "E", 25.0, 300.0),
        (12, 3.0, "D", 29.0, 800.0),
        (15, 3.0, "C", 30.0, 1000.0),
        (18, 2.0, "D", 27.0, 500.0),
        (21, 1.5, "F", 24.0, 200.0),
        (24, 1.5, "F", 23.0, 200.0),
    ],
}

SCENARIOS = tuple(_SCENARIO_ANCHORS)


class MetCondition:
    """One hour of meteorological conditions."""

    def __init__(self, hour, wind_speed_10m, wind_direction_deg,
                 stability, temp_c, mixing_height_m):
        if stability not in STABILITY_CLASSES:
            raise ValueError(f"unknown stability class {stability!r}")
        if wind_speed_10m < 0:
            raise ValueError("wind_speed_10m must be >= 0")
        if mixing_height_m <= 0:
            raise ValueError("mixing_height_m must be > 0")
        self.hour = float(hour)
        self.wind_speed_10m = float(wind_speed_10m)
        self.wind_direction_deg = float(wind_direction_deg) % 360.0
        self.stability = stability
        self.temp_c = float(temp_c)
        self.mixing_height_m = float(mixing_height_m)

    def __repr__(self):
        return (f"MetCondition(hour={self.hour:.0f}, "
                f"u10={self.wind_speed_10m:.1f} m/s, "
                f"dir={self.wind_direction_deg:.0f} deg, "
                f"stab={self.stability}, T={self.temp_c:.1f} C, "
                f"hm={self.mixing_height_m:.0f} m)")

    def to_dict(self):
        """JSON-serialisable representation."""
        return {"hour": self.hour,
                "wind_speed_10m": self.wind_speed_10m,
                "wind_direction_deg": self.wind_direction_deg,
                "stability": self.stability,
                "temp_c": self.temp_c,
                "mixing_height_m": self.mixing_height_m}

    @classmethod
    def from_dict(cls, data):
        """Rebuild a MetCondition from :meth:`to_dict` output."""
        return cls(data["hour"], data["wind_speed_10m"],
                   data["wind_direction_deg"], data["stability"],
                   data["temp_c"], data["mixing_height_m"])


def _interp(anchors, hour):
    """Linear interpolation of one anchor table at a given hour."""
    hour = hour % 24.0
    for i in range(len(anchors) - 1):
        h0, u0, s0, t0, m0 = anchors[i]
        h1, u1, s1, t1, m1 = anchors[i + 1]
        if h0 <= hour <= h1:
            frac = 0.0 if h1 == h0 else (hour - h0) / (h1 - h0)
            # Stability classes are categorical: switch at midpoint.
            stab = s0 if frac < 0.5 else s1
            return (u0 + frac * (u1 - u0), stab,
                    t0 + frac * (t1 - t0), m0 + frac * (m1 - m0))
    return anchors[-1][1], anchors[-1][2], anchors[-1][3], anchors[-1][4]


def scenario_day(name, wind_direction_deg=90.0, noise=0.0, seed=0):
    """24 hourly MetConditions for a named scenario.

    ``wind_direction_deg`` is the direction the wind blows toward
    (default 90 = toward the east). ``noise`` adds seeded Gaussian
    jitter (m/s) to the wind speed for forecast ensembles.
    """
    if name not in _SCENARIO_ANCHORS:
        raise ValueError(f"unknown scenario {name!r}; "
                         f"choose from {sorted(_SCENARIO_ANCHORS)}")
    rng = random.Random(seed)
    anchors = _SCENARIO_ANCHORS[name]
    conditions = []
    for hour in range(24):
        u, stab, temp, hm = _interp(anchors, hour)
        if noise:
            u = max(0.2, u + rng.gauss(0.0, noise))
        conditions.append(MetCondition(hour, u, wind_direction_deg,
                                       stab, temp, hm))
    return conditions


def generate_met_series(days, scenario="calm_morning",
                        wind_direction_deg=90.0, seed=42):
    """Multi-day hourly meteorology.

    ``scenario`` is one named scenario, or ``"mixed"``: the three
    scenarios are then rotated day by day (calm -> windy -> night
    inversion -> ...), which is the realistic case for a multi-day
    forecast -- real weather changes from day to day. Each day
    re-uses its scenario pattern with a small seeded jitter on wind
    speed and temperature so days are not identical.
    Returns a list of MetCondition, hour counted from 0.
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    rng = random.Random(seed)
    series = []
    for day in range(days):
        if scenario == "mixed":
            day_scenario = SCENARIOS[day % len(SCENARIOS)]
        else:
            day_scenario = scenario
        wind_jitter = rng.gauss(0.0, 0.4)
        temp_jitter = rng.gauss(0.0, 0.8)
        day_conditions = scenario_day(day_scenario,
                                      wind_direction_deg,
                                      noise=0.0, seed=seed + day)
        for cond in day_conditions:
            series.append(MetCondition(
                hour=day * 24 + cond.hour,
                wind_speed_10m=max(0.2,
                                   cond.wind_speed_10m + wind_jitter),
                wind_direction_deg=cond.wind_direction_deg,
                stability=cond.stability,
                temp_c=cond.temp_c + temp_jitter,
                mixing_height_m=cond.mixing_height_m))
    return series


def diurnal_emission_factor(hour):
    """Diurnal activity factor for industrial + traffic emissions.

    Dimensionless multiplier (daily mean = 1 by construction is NOT
    guaranteed; the profile is a smooth two-peak day shape peaking at
    the morning and evening rush hours, minimum at 03:00). Values are
    a scenario assumption, documented in docs/RESEARCH.md.
    """
    h = hour % 24.0
    # Morning peak 08:00, evening peak 18:00, night minimum.
    value = 1.0 \
        + 0.35 * math.exp(-0.5 * ((h - 8.0) / 2.0) ** 2) \
        + 0.30 * math.exp(-0.5 * ((h - 18.0) / 2.0) ** 2) \
        - 0.35 * math.exp(-0.5 * ((h - 3.0) / 2.5) ** 2)
    return max(0.2, value)
