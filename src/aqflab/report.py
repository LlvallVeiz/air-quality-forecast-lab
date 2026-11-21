"""Report generation: Markdown and HTML summaries of one scenario run.

A report combines the inventory totals, the peak ground-level
concentration per pollutant, the daily AQI table and rule-based
recommendations. Recommendations follow the EPA AQI health messages
and are generic public-health guidance, not medical advice.
"""

import html

from aqflab.aqi import category

RECOMMENDATIONS = {
    "Good": "No action needed. Outdoor activities can proceed normally.",
    "Moderate": "Unusually sensitive people should consider reducing "
                "prolonged or heavy outdoor exertion.",
    "Unhealthy for Sensitive Groups": "Sensitive groups (children, "
                "elderly, people with heart or lung disease) should "
                "reduce prolonged or heavy outdoor exertion.",
    "Unhealthy": "Everyone should reduce prolonged or heavy outdoor "
                 "exertion; sensitive groups should avoid it.",
    "Very Unhealthy": "Everyone should avoid prolonged or heavy "
                      "outdoor exertion; sensitive groups should "
                      "remain indoors.",
    "Hazardous": "Everyone should avoid all outdoor physical "
                 "activity and remain indoors.",
}


def recommendation_for(aqi):
    """Rule-based recommendation text for an AQI value."""
    name, _colour, _message = category(aqi)
    return RECOMMENDATIONS.get(name, "No recommendation available.")


def build_report_data(title, inventory_totals, peaks, daily_aqi,
                      daily_conc, worst_day):
    """Assemble the plain-data dict a report is rendered from."""
    return {
        "title": title,
        "inventory_totals": inventory_totals,
        "peaks": peaks,
        "daily_aqi": daily_aqi,
        "daily_conc": daily_conc,
        "worst_day": worst_day,
    }


def render_markdown(data):
    """Render a report dict as Markdown text."""
    lines = [f"# {data['title']}", "",
             "Synthetic-city air-quality scenario report. All sources, "
             "meteorology and concentrations are synthetic; see "
             "`docs/RESEARCH.md` for the methods and sources.", "",
             "## Emission inventory (g/s)", "",
             "| Pollutant | Total emission rate (g/s) |",
             "|---|---|"]
    for pol, total in sorted(data["inventory_totals"].items()):
        lines.append(f"| {pol} | {total:.4f} |")
    lines += ["", "## Peak ground-level concentration (ug/m^3)", "",
              "| Pollutant | Peak (ug/m^3) | Location (x, y) m |",
              "|---|---|---|"]
    for pol, peak in sorted(data["peaks"].items()):
        rec, value = peak
        lines.append(f"| {pol} | {value:.2f} | ({rec.x:.0f}, {rec.y:.0f}) |")
    lines += ["", "## Daily AQI", "",
              "| Day | AQI | Category | Recommendation |",
              "|---|---|---|---|"]
    for day, aqi in enumerate(data["daily_aqi"], start=1):
        name, _colour, _message = category(aqi)
        lines.append(f"| {day} | {aqi} | {name} | "
                     f"{recommendation_for(aqi)} |")
    worst = data["worst_day"]
    lines += ["",
              f"**Worst day: day {worst + 1} "
              f"(AQI {data['daily_aqi'][worst]}).**",
              "",
              "## Daily concentrations (ug/m^3)", ""]
    pollutants = sorted(data["daily_conc"])
    header = "| Day | " + " | ".join(pollutants) + " |"
    lines.append(header)
    lines.append("|---|" + "---|" * len(pollutants))
    for day in range(len(data["daily_aqi"])):
        row = " | ".join(
            f"{data['daily_conc'][pol][day]:.2f}" for pol in pollutants)
        lines.append(f"| {day + 1} | {row} |")
    lines.append("")
    return "\n".join(lines)


def render_html(data):
    """Render a report dict as a standalone HTML page."""
    rows_aqi = "".join(
        f"<tr><td>{d + 1}</td><td>{aqi}</td>"
        f"<td>{category(aqi)[0]}</td>"
        f"<td>{html.escape(recommendation_for(aqi))}</td></tr>"
        for d, aqi in enumerate(data["daily_aqi"]))
    rows_inv = "".join(
        f"<tr><td>{pol}</td><td>{total:.4f}</td></tr>"
        for pol, total in sorted(data["inventory_totals"].items()))
    rows_peak = "".join(
        f"<tr><td>{pol}</td><td>{value:.2f}</td>"
        f"<td>({rec.x:.0f}, {rec.y:.0f})</td></tr>"
        for pol, (rec, value) in sorted(data["peaks"].items()))
    pollutants = sorted(data["daily_conc"])
    header = "".join(f"<th>{pol}</th>" for pol in pollutants)
    rows_conc = ""
    for day in range(len(data["daily_aqi"])):
        cells = "".join(
            f"<td>{data['daily_conc'][pol][day]:.2f}</td>"
            for pol in pollutants)
        rows_conc += f"<tr><td>{day + 1}</td>{cells}</tr>"
    worst = data["worst_day"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8">
<title>{html.escape(data['title'])}</title>
<style>
body {{ font-family: sans-serif; max-width: 900px; margin: 2em auto;
       padding: 0 1em; color: #222; }}
table {{ border-collapse: collapse; margin: 1em 0; }}
th, td {{ border: 1px solid #999; padding: 0.4em 0.8em;
          text-align: left; }}
th {{ background: #eee; }}
</style></head>
<body>
<h1>{html.escape(data['title'])}</h1>
<p>Synthetic-city air-quality scenario report. All sources,
meteorology and concentrations are synthetic; see
<code>docs/RESEARCH.md</code> for the methods and sources.</p>
<h2>Emission inventory (g/s)</h2>
<table><tr><th>Pollutant</th><th>Total (g/s)</th></tr>{rows_inv}</table>
<h2>Peak ground-level concentration (ug/m^3)</h2>
<table><tr><th>Pollutant</th><th>Peak</th><th>Location (x, y) m</th>
</tr>{rows_peak}</table>
<h2>Daily AQI</h2>
<table><tr><th>Day</th><th>AQI</th><th>Category</th>
<th>Recommendation</th></tr>{rows_aqi}</table>
<p><strong>Worst day: day {worst + 1}
(AQI {data['daily_aqi'][worst]}).</strong></p>
<h2>Daily concentrations (ug/m^3)</h2>
<table><tr><th>Day</th>{header}</tr>{rows_conc}</table>
</body>
</html>
"""


def write_report(data, md_path, html_path=None):
    """Write the Markdown report and, optionally, the HTML report."""
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(data))
    if html_path is not None:
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(render_html(data))
