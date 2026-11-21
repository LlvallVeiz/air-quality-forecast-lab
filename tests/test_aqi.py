"""Tests for the US EPA AQI (breakpoints effective 6 May 2024).

Reference: 40 CFR Part 58, Appendix G, Table 2 (EPA-454/B-24-002).
PM2.5 edges: 9.0 -> 50, 9.1 -> 51, 35.4 -> 100, 35.5 -> 101,
55.4 -> 150, 55.5 -> 151, 125.4 -> 200, 125.5 -> 201, 225.4 -> 300,
225.5 -> 301, 325.4 -> 500. Interpolation check: PM2.5 22.25 ug/m^3
is the midpoint of the 9.1-35.4 band -> (51+100)/2 = 75.5 -> 76.
"""

import pytest

from aqflab.aqi import (
    aqi_from_concentrations,
    category,
    o3_sub_index,
    sub_index,
    truncate,
)


@pytest.mark.parametrize("conc,expected", [
    (0.0, 0), (9.0, 50), (9.1, 51), (35.4, 100), (35.5, 101),
    (55.4, 150), (55.5, 151), (125.4, 200), (125.5, 201),
    (225.4, 300), (225.5, 301), (325.4, 500),
])
def test_pm25_breakpoint_edges(conc, expected):
    assert sub_index("PM2.5", conc) == expected


def test_pm25_interpolation_midpoint():
    # 22.3 ug/m^3 is just past the band midpoint; 51 + 49*(13.2/26.3)
    # = 75.59 -> 76. (22.25 would truncate to 22.2 -> 75.)
    assert sub_index("PM2.5", 22.3) == 76


def test_pm25_truncation_before_lookup():
    # 9.09 ug/m^3 truncates to 9.0 -> AQI 50, not 51.
    assert truncate(9.09, 1) == pytest.approx(9.0)
    assert sub_index("PM2.5", 9.09) == 50


def test_pm25_above_scale_caps_at_500():
    assert sub_index("PM2.5", 400.0) == 500


@pytest.mark.parametrize("pollutant,conc,expected", [
    ("PM10", 54, 50), ("PM10", 55, 51), ("PM10", 154, 100),
    ("PM10", 604, 500),
    ("CO", 4.4, 50), ("CO", 4.5, 51), ("CO", 9.4, 100),
    ("NO2", 53, 50), ("NO2", 54, 51), ("NO2", 100, 100),
    ("SO2", 35, 50), ("SO2", 36, 51), ("SO2", 304, 200),
])
def test_other_pollutant_edges(pollutant, conc, expected):
    assert sub_index(pollutant, conc) == expected


def test_o3_8h_interpolation():
    # 0.060 ppm is 1/3 through the 0.055-0.070 band:
    # 51 + 49*(0.005/0.015) = 67.33 -> 67.
    assert sub_index("O3", 0.060) == 67


def test_o3_8h_above_0200_needs_1h():
    assert sub_index("O3", 0.25) is None
    assert o3_sub_index(conc_8h=0.25, conc_1h=0.30) == 248
    assert o3_sub_index(conc_8h=0.060) == 67


def test_so2_1h_above_304_needs_24h():
    assert sub_index("SO2", 400) is None
    # 24-hour 400 ppb: 201 + 99*(95/299) = 232.45 -> 232.
    assert sub_index("SO2", 400, averaging="24h") == 232


def test_unknown_pollutant_and_negative_raise():
    with pytest.raises(ValueError):
        sub_index("VOC", 10.0)
    with pytest.raises(ValueError):
        sub_index("PM2.5", -1.0)


def test_categories_and_colours():
    assert category(25) == ("Good", "#00E400", category(25)[2])
    assert category(75)[0] == "Moderate"
    assert category(125)[0] == "Unhealthy for Sensitive Groups"
    assert category(175)[0] == "Unhealthy"
    assert category(250)[0] == "Very Unhealthy"
    assert category(400)[0] == "Hazardous"
    assert category(400)[1] == "#7E0023"
    assert category(None)[0] == "Not available"


def test_aqi_from_concentrations_driving_pollutant():
    result = aqi_from_concentrations({
        "PM2.5": 22.3, "PM10": 80.0, "O3": 0.060, "CO": 3.0,
        "NO2": 40.0, "SO2": 20.0})
    # Sub-indices: PM2.5 76, PM10 63, O3 67, CO 34, NO2 38, SO2 29.
    assert result["sub_indices"]["PM2.5"] == 76
    assert result["sub_indices"]["PM10"] == 63
    assert result["aqi"] == 76
    assert result["driving_pollutant"] == "PM2.5"
    assert result["category"] == "Moderate"
    assert result["colour"] == "#FFFF00"


def test_aqi_from_concentrations_empty_and_partial():
    result = aqi_from_concentrations({})
    assert result["aqi"] is None
    result = aqi_from_concentrations({"PM2.5": 5.0})
    assert result["aqi"] == 28  # 5.0/9.0 * 50 = 27.78 -> 28
    assert result["driving_pollutant"] == "PM2.5"
