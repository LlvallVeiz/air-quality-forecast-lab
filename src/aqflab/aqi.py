"""US EPA Air Quality Index (AQI).

Breakpoints: 40 CFR Part 58, Appendix G, Table 2, as reproduced in
US EPA, "Technical Assistance Document for the Reporting of Daily Air
Quality -- the Air Quality Index (AQI)", EPA-454/B-24-002 (May 2024),
including the revised PM2.5 breakpoints effective 6 May 2024
(Good ends at 9.0 ug/m^3; AQI 500 at 325.4 ug/m^3).

Sub-index formula (EPA Equation 1):

    I = (Ihi - Ilo) / (BPhi - Bplo) * (Cp - Bplo) + Ilo

rounded to the nearest integer (halves round up). Concentrations are
truncated before lookup, as EPA specifies: PM2.5 to 1 decimal place,
PM10 to integer, O3 to 3 decimals, CO to 1 decimal, SO2 and NO2 to
integer.

Averaging periods: PM2.5/PM10 24-hour; O3 8-hour (1-hour is used for
AQI > 300); CO 8-hour; NO2 1-hour; SO2 1-hour up to AQI 200 -- above
that EPA uses the 24-hour SO2 average, implemented here as a separate
function. Category colours are the EPA/AirNow standard hex values.
"""

import math

# (conc_lo, conc_hi, aqi_lo, aqi_hi) per pollutant.
# Units: PM ug/m^3, O3/CO ppm, SO2/NO2 ppb.
BREAKPOINTS = {
    "PM2.5": [
        (0.0, 9.0, 0, 50),
        (9.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 125.4, 151, 200),
        (125.5, 225.4, 201, 300),
        (225.5, 325.4, 301, 500),
    ],
    "PM10": [
        (0, 54, 0, 50),
        (55, 154, 51, 100),
        (155, 254, 101, 150),
        (255, 354, 151, 200),
        (355, 424, 201, 300),
        (425, 604, 301, 500),
    ],
    "O3_8h": [
        (0.000, 0.054, 0, 50),
        (0.055, 0.070, 51, 100),
        (0.071, 0.085, 101, 150),
        (0.086, 0.105, 151, 200),
        (0.106, 0.200, 201, 300),
    ],
    "O3_1h": [
        (0.125, 0.164, 101, 150),
        (0.165, 0.204, 151, 200),
        (0.205, 0.404, 201, 300),
        (0.405, 0.604, 301, 500),
    ],
    "CO_8h": [
        (0.0, 4.4, 0, 50),
        (4.5, 9.4, 51, 100),
        (9.5, 12.4, 101, 150),
        (12.5, 15.4, 151, 200),
        (15.5, 30.4, 201, 300),
        (30.5, 50.4, 301, 500),
    ],
    "SO2_1h": [
        (0, 35, 0, 50),
        (36, 75, 51, 100),
        (76, 185, 101, 150),
        (186, 304, 151, 200),
    ],
    "SO2_24h": [
        (305, 604, 201, 300),
        (605, 1004, 301, 500),
    ],
    "NO2_1h": [
        (0, 53, 0, 50),
        (54, 100, 51, 100),
        (101, 360, 101, 150),
        (361, 649, 151, 200),
        (650, 1249, 201, 300),
        (1250, 2049, 301, 500),
    ],
}

# Truncation decimals before lookup (EPA rule).
TRUNCATION = {
    "PM2.5": 1, "PM10": 0, "O3_8h": 3, "O3_1h": 3,
    "CO_8h": 1, "SO2_1h": 0, "SO2_24h": 0, "NO2_1h": 0,
}

# Which breakpoint key belongs to each pollutant by default.
DEFAULT_KEY = {
    "PM2.5": "PM2.5", "PM10": "PM10", "O3": "O3_8h",
    "CO": "CO_8h", "SO2": "SO2_1h", "NO2": "NO2_1h",
}

CATEGORIES = [
    (0, 50, "Good", "#00E400",
     "Air quality is satisfactory, and air pollution poses little "
     "or no risk."),
    (51, 100, "Moderate", "#FFFF00",
     "Air quality is acceptable; however, for some pollutants there "
     "may be a moderate health concern for a very small number of "
     "people who are unusually sensitive to air pollution."),
    (101, 150, "Unhealthy for Sensitive Groups", "#FF7E00",
     "Members of sensitive groups may experience health effects. "
     "The general public is not likely to be affected."),
    (151, 200, "Unhealthy", "#FF0000",
     "Everyone may begin to experience health effects; members of "
     "sensitive groups may experience more serious health effects."),
    (201, 300, "Very Unhealthy", "#8F3F97",
     "Health warnings of emergency conditions. The entire "
     "population is more likely to be affected."),
    (301, 500, "Hazardous", "#7E0023",
     "Health alert: everyone may experience more serious health "
     "effects."),
]


def truncate(value, decimals):
    """Truncate (not round) a value to ``decimals`` decimal places."""
    factor = 10.0 ** decimals
    return math.floor(value * factor) / factor


def _interpolate(conc, lo, hi, aqi_lo, aqi_hi):
    """EPA Equation 1, rounded to the nearest integer (halves up)."""
    value = (aqi_hi - aqi_lo) / (hi - lo) * (conc - lo) + aqi_lo
    return int(math.floor(value + 0.5))


def sub_index(pollutant, concentration, averaging=None):
    """AQI sub-index for one pollutant concentration.

    Parameters
    ----------
    pollutant : str
        One of PM2.5, PM10, O3, CO, SO2, NO2.
    concentration : float
        Concentration in the pollutant's breakpoint units
        (ug/m^3 for PM, ppm for O3/CO, ppb for SO2/NO2).
    averaging : str or None
        "8h"/"1h"/"24h" for pollutants with two tables (O3, SO2);
        the default is the EPA primary averaging period.

    Returns
    -------
    int or None
        The sub-index, or None when EPA defines no index for this
        concentration/averaging combination (e.g. 1-hour SO2 above
        304 ppb, which requires a 24-hour average, or 8-hour O3
        above 0.200 ppm, which requires the 1-hour value).
    """
    if concentration < 0:
        raise ValueError("concentration must be >= 0")
    key = DEFAULT_KEY.get(pollutant)
    if key is None:
        raise ValueError(f"unknown pollutant {pollutant!r}")
    if pollutant == "O3" and averaging == "1h":
        key = "O3_1h"
    elif pollutant == "SO2" and averaging == "24h":
        key = "SO2_24h"
    elif averaging is not None and pollutant not in ("O3", "SO2"):
        raise ValueError(
            f"averaging override not supported for {pollutant}")
    table = BREAKPOINTS[key]
    conc = truncate(concentration, TRUNCATION[key])
    for lo, hi, aqi_lo, aqi_hi in table:
        if lo <= conc <= hi:
            return _interpolate(conc, lo, hi, aqi_lo, aqi_hi)
    # Above the last breakpoint: for O3 8-hour (> 0.200 ppm) and SO2
    # 1-hour (> 304 ppb) EPA requires a different averaging period,
    # so no index is defined here; for the other pollutants EPA
    # continues the slope of the 301-500 segment up to AQI 500.
    last_lo, last_hi, last_aqi_lo, last_aqi_hi = table[-1]
    if conc > last_hi:
        if key in ("O3_8h", "SO2_1h"):
            return None
        value = _interpolate(conc, last_lo, last_hi,
                             last_aqi_lo, last_aqi_hi)
        return min(value, 500)
    return None


def o3_sub_index(conc_8h=None, conc_1h=None):
    """O3 sub-index following the EPA procedure.

    The 8-hour value defines AQI up to 300; if the 8-hour average
    exceeds 0.200 ppm the 1-hour value is used instead.
    """
    if conc_8h is not None and conc_8h <= 0.200:
        return sub_index("O3", conc_8h)
    if conc_1h is not None:
        return sub_index("O3", conc_1h, averaging="1h")
    return None


def category(aqi):
    """(name, hex colour, health message) for an AQI value."""
    if aqi is None:
        return ("Not available", "#CCCCCC",
                "No AQI could be computed for the given concentrations.")
    if aqi < 0:
        raise ValueError("AQI must be >= 0")
    for lo, hi, name, colour, message in CATEGORIES:
        if lo <= aqi <= hi:
            return (name, colour, message)
    return ("Hazardous", "#7E0023", CATEGORIES[-1][4])


def aqi_from_concentrations(concentrations):
    """Overall AQI from a dict of pollutant concentrations.

    ``concentrations`` maps pollutant names to concentrations in
    breakpoint units (PM ug/m^3, O3/CO ppm, SO2/NO2 ppb). The key
    ``"O3_1h"`` may be supplied alongside ``"O3"`` (8-hour) for the
    above-300 path, and ``"SO2_24h"`` alongside ``"SO2"`` (1-hour).

    Returns
    -------
    dict
        {"aqi": int or None, "driving_pollutant": str or None,
         "sub_indices": {pollutant: sub-index or None},
         "category": name, "colour": hex, "message": health text}
    """
    sub = {}
    for pollutant in ("PM2.5", "PM10", "CO", "NO2"):
        if pollutant in concentrations:
            sub[pollutant] = sub_index(
                pollutant, concentrations[pollutant])
    if "O3" in concentrations or "O3_1h" in concentrations:
        sub["O3"] = o3_sub_index(concentrations.get("O3"),
                                 concentrations.get("O3_1h"))
    if "SO2" in concentrations or "SO2_24h" in concentrations:
        value = sub_index("SO2", concentrations["SO2"]) \
            if "SO2" in concentrations else None
        if value is None and "SO2_24h" in concentrations:
            value = sub_index("SO2", concentrations["SO2_24h"],
                              averaging="24h")
        sub["SO2"] = value
    valid = {k: v for k, v in sub.items() if v is not None}
    if not valid:
        result = {"aqi": None, "driving_pollutant": None,
                  "sub_indices": sub}
    else:
        driving = max(valid, key=lambda k: valid[k])
        result = {"aqi": valid[driving],
                  "driving_pollutant": driving,
                  "sub_indices": sub}
    name, colour, message = category(result["aqi"])
    result.update({"category": name, "colour": colour,
                   "message": message})
    return result
