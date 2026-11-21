"""Tests for report rendering and recommendations."""

from aqflab.receptors import Receptor
from aqflab.report import (
    build_report_data,
    recommendation_for,
    render_html,
    render_markdown,
)


def _sample_data():
    return build_report_data(
        "Test report",
        {"PM2.5": 1.197, "NO2": 15.75},
        {"PM2.5": (Receptor(1500, 0), 42.5),
         "NO2": (Receptor(1200, 0), 88.1)},
        [45, 78, 132, 60, 55, 48, 70],
        {"PM2.5": [10.0, 22.0, 40.0, 15.0, 12.0, 9.0, 18.0],
         "NO2": [20.0, 30.0, 55.0, 25.0, 22.0, 18.0, 28.0]},
        worst_day=2)


def test_recommendation_for_categories():
    assert "No action" in recommendation_for(30)
    assert "sensitive" in recommendation_for(120).lower()
    assert "avoid" in recommendation_for(250).lower()
    assert "indoors" in recommendation_for(350).lower()


def test_render_markdown_contains_key_sections():
    text = render_markdown(_sample_data())
    assert "# Test report" in text
    assert "Emission inventory" in text
    assert "PM2.5" in text
    assert "15.75" in text
    assert "Worst day: day 3 (AQI 132)" in text
    assert "Unhealthy for Sensitive Groups" in text
    assert "| 3 | 132 |" in text


def test_render_html_is_standalone_page():
    page = render_html(_sample_data())
    assert page.startswith("<!DOCTYPE html>")
    assert "<table>" in page
    assert "Worst day: day 3" in page
    assert "132" in page
    assert "</html>" in page


def test_build_report_data_round_trip():
    data = _sample_data()
    assert data["title"] == "Test report"
    assert data["worst_day"] == 2
    assert data["daily_aqi"][2] == 132
