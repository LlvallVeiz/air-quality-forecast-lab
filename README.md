# air-quality-forecast-lab

Gaussian plume dispersion (Briggs), US EPA Air Quality Index, and
short-range AQI forecasting — built as an end-to-end laboratory for
a **synthetic city ("Kota Sinar")**. Everything is labelled
synthetic: the city, the sources, the meteorology and the
"observations" are all constructed, and no result here is a claim
about air quality in any real place.

## What it does

1. **Emission inventory** — point (stack), area and line (road)
   sources. Stack rates from US EPA AP-42 Table 1.4-1 (natural-gas
   combustion); road factors from the Euro 6 type-approval limits
   (labelled as limits, not real-world measurements).
2. **Gaussian plume dispersion** — steady-state plume with ground
   reflection (method of images), Briggs (1973) sigma-y/sigma-z
   (rural + urban), Briggs plume rise (buoyant/momentum,
   stable/calm, stack-tip downwash), Pasquill-Gifford classes via
   Turner's method, ISC3 wind-profile power law, optional
   mixing-height reflections.
3. **Meteorology** — three named diurnal scenarios: `calm_morning`
   (light wind, stable dawn), `windy_noon` (6 m/s, unstable),
   `night_inversion` (1.5 m/s, class F, 200 m mixing height);
   `mixed` rotates them day by day for multi-day runs.
4. **AQI** — US EPA breakpoints (40 CFR Part 58, App. G, Table 2),
   including the revised PM2.5 breakpoints effective 6 May 2024,
   with EPA truncation rules, O3 8-hour/1-hour procedure and the
   SO2 1-hour/24-hour rule.
5. **Forecast** — 7-day synthetic hourly series at a receptor,
   daily EPA aggregation, persistence baseline vs AR(1) forecast,
   evaluated with MAE/RMSE/bias and a skill score vs persistence.
6. **Reports** — Markdown + HTML scenario reports (inventory,
   peaks, daily AQI, recommendations) and batch runs over all
   scenarios x met conditions.

## Project structure

```
air-quality-forecast-lab/
├── main.py                  # entry point: python main.py <command>
├── pyproject.toml           # src layout, `aqflab` console script
├── requirements.txt         # numpy/matplotlib/pytest (core is stdlib-only)
├── src/aqflab/
│   ├── constants.py         # physical constants, unit conversions
│   ├── stability.py         # Turner classes, wind profile, mixing height
│   ├── plume_rise.py        # Briggs plume rise
│   ├── dispersion.py        # Gaussian plume, Briggs sigma
│   ├── emissions.py         # AP-42 + Euro 6 factors, source classes
│   ├── meteorology.py       # synthetic diurnal scenarios
│   ├── aqi.py               # EPA AQI breakpoints + sub-index
│   ├── receptors.py         # grids, plume-frame rotation, fields
│   ├── forecast.py          # synthetic series, persistence, AR(1)
│   ├── report.py            # Markdown + HTML reports
│   ├── plot.py              # matplotlib maps/charts, ASCII fallback
│   └── cli.py               # plume / aqi / forecast / report / batch
├── scenarios/               # industrial_park, highway_corridor, met tables
├── examples/
│   ├── run_examples.py      # reproduces every output below
│   └── output/              # CSVs, PNG maps, reports from real runs
├── docs/
│   ├── RESEARCH.md          # methods + every source, verified 2026-11-20
│   └── DESIGN.md            # design decisions, limitations, future work
└── tests/                   # 131 pytest tests, all passing
```

## Quick start

```bash
pip install -r requirements.txt   # or: pip install -e .
python main.py plume --scenario scenarios/industrial_park.json \
    --pollutant PM2.5 --met calm_morning --hour 8 \
    --out examples/output/plume_pm25_calm_morning.csv \
    --png examples/output/plume_pm25_calm_morning.png

python main.py aqi --pm25 22.3 --pm10 80 --o3 0.060 \
    --co 3.0 --no2 40 --so2 20

python main.py forecast --scenario scenarios/industrial_park.json \
    --days 10 --horizon 3 --met mixed

python main.py report --scenario scenarios/industrial_park.json \
    --days 7 --met mixed \
    --md examples/output/report_industrial_park.md \
    --html examples/output/report_industrial_park.html

python main.py batch --scenarios scenarios/industrial_park.json \
    scenarios/highway_corridor.json --hour 8 \
    --out examples/output/batch_summary.csv
```

Run the tests with `python -m pytest tests/ -q` (131 passed).

## Example results (real runs, 2026-11-20)

All outputs are in `examples/output/`; reproduce them with
`python examples/run_examples.py`.

### Plume peaks, industrial park, hour 08:00 (PM2.5, ug/m^3)

| Met scenario | Peak | Location (x, y) |
|---|---|---|
| calm_morning | 30.15 | (1250, 500) — near the logistics yard |
| windy_noon | 16.40 | (1000, 500) |
| night_inversion | 33.03 | (1250, 500) |

Stable, low-wind air traps the plume (highest peak); strong
midday mixing cuts the peak almost in half — exactly what the
theory predicts. Highway corridor, NO2, calm morning:
**87.71 ug/m^3** at (3000, 0); at night inversion it reaches
**136.92 ug/m^3**.

### AQI example

```
$ python main.py aqi --pm25 22.3 --pm10 80 --o3 0.060 --co 3.0 --no2 40 --so2 20
Sub-indices: PM2.5 76, PM10 63, O3 67, CO 34, NO2 38, SO2 29
Overall AQI: 76 (Moderate), driven by PM2.5
```

### Forecast: 10-day daily AQI, industrial-park receptor (1500, 0)

Daily AQI: 58, 59, 58, 58, **60** (worst, day 5), 58, 59, 59, 58, 58
— all Moderate, driven by PM2.5 (daily mean 12.8–13.9 ug/m^3
against a 12 ug/m^3 background; the receptor is
background-dominated, so the AQI varies little).

Hold-out evaluation (last 3 days, trained on 7):

| Method | MAE | RMSE | Bias | Skill vs persistence |
|---|---|---|---|---|
| Persistence | 0.67 | 0.82 | +0.67 | — |
| AR(1) | 0.63 | 0.63 | +0.22 | **+0.397** |

AR(1) beats persistence on this synthetic series. The narrow AQI
range (58–60) is a property of this scenario, not a claim about
real forecasting.

### Inventory totals, industrial park (g/s)

| Pollutant | Total |
|---|---|
| NO2 | 22.2196 |
| CO | 20.5217 |
| PM10 | 2.1883 |
| PM2.5 | 1.8883 |
| SO2 | 0.1323 |

Boiler rates come from AP-42 Table 1.4-1: e.g. Boiler Utara
(30 MMscf/day) emits NO2 15.7497 g/s, PM2.5 1.1970 g/s,
CO 13.2298 g/s, SO2 0.0945 g/s.

### Verification highlights (see `tests/`)

- Centreline concentration, hand calculation: Q = 10 g/s, u = 5 m/s,
  x = 1000 m, H = 50 m, class D rural -> **92.31 ug/m^3**
  (sigma-y 76.28 m, sigma-z 37.95 m, computed independently).
- Centreline peak for the same case: **96.87 ug/m^3 at x = 810 m**.
- Briggs plume rise worked example (lecture notes): F = 50 m^4/s^3,
  u = 4.92 m/s -> **81.88 m** (notes print 81.78 m; 0.1 m is their
  intermediate rounding).
- Every PM2.5 breakpoint edge verified (9.0 -> 50, 9.1 -> 51,
  35.4 -> 100, 35.5 -> 101, 55.4 -> 150, 55.5 -> 151, 125.4 -> 200,
  125.5 -> 201, 225.4 -> 300, 225.5 -> 301, 325.4 -> 500).

## Limitations — read before trusting any number

- Screening model only: flat terrain, no building downwash
  (except stack-tip), no deposition, no chemistry, no fumigation.
  For permits use AERMOD/CALPUFF.
- Briggs formulas are valid for 100 m < x < 10 km. Peaks that land
  on a grid edge are "peak within the grid", not the far-field max.
- Briggs plume rise is known to underestimate observed rise in
  some campaigns (Gordon et al. 2017).
- Ozone is not modelled photochemically; it enters only via the
  AQI module and the background level.
- Euro 6 road factors are type-approval limits, not measured
  real-world emissions. AP-42 factors carry quality ratings as
  low as D. Yard dust rates are scenario assumptions.
- All meteorology, sources and "observations" are synthetic.

See `docs/DESIGN.md` for the full list and `docs/RESEARCH.md`
for every method and source.
