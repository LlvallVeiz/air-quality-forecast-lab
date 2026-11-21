# Example results

All files below are real outputs of `python examples/run_examples.py`
(2026-11-20). No number here is fabricated; re-run the script to
reproduce them exactly (seeded RNG, same inputs).

## Plume fields (industrial park, PM2.5, hour 08:00)

| File | Met scenario | Peak (ug/m^3) | Location |
|---|---|---|---|
| `plume_pm25_calm_morning.csv` (+ `.png`) | calm_morning | 30.15 | (1250, 500) |
| `plume_pm25_windy_noon.csv` (+ `.png`) | windy_noon | 16.40 | (1000, 500) |
| `plume_pm25_night_inversion.csv` (+ `.png`) | night_inversion | 33.03 | (1250, 500) |

Grid: x -500..4000 m, y -2000..2000 m, step 250 m (323 receptors).
Background PM2.5 is 12.0 ug/m^3; the peaks sit near the logistics
yard (800, 400), the low area source.

## Plume field (highway corridor, NO2, calm morning, hour 08:00)

`plume_no2_highway_calm.csv` (+ `.png`): peak **87.71 ug/m^3** at
(3000, 0), at the downwind end of Jalan Tol Sinar. Background NO2
is 12.0 ug/m^3.

## AQI example

```
$ python main.py aqi --pm25 22.3 --pm10 80 --o3 0.060 --co 3.0 --no2 40 --so2 20
Sub-indices: PM2.5 76, PM10 63, O3 67, CO 34, NO2 38, SO2 29
Overall AQI: 76 (Moderate), driven by PM2.5
```

## Forecast (10 days, mixed met, industrial-park receptor)

`forecast_daily_aqi.csv` (+ `.png`): daily AQI
58, 59, 58, 58, **60**, 58, 59, 59, 58, 58. Worst day: day 5
(AQI 60, Moderate).

Hold-out (last 3 days, trained on 7):

| Method | MAE | RMSE | Bias |
|---|---|---|---|
| Persistence | 0.67 | 0.82 | +0.67 |
| AR(1) | 0.63 | 0.63 | +0.22 |

AR(1) skill vs persistence: **+0.397**. The AQI range is narrow
(58–60) because the receptor is background-dominated (daily mean
PM2.5 12.8–13.9 ug/m^3 vs a 12 ug/m^3 background).

## Scenario report (7 days, mixed met)

`report_industrial_park.md` and `.html`: inventory totals
(NO2 22.2196, CO 20.5217, PM10 2.1883, PM2.5 1.8883,
SO2 0.1323 g/s), peak table (calm-morning hour 8, representative
for the peak table), daily AQI table (worst day 5, AQI 60) and
daily concentrations in ug/m^3.

## Batch summary (all scenarios x met, hour 08:00)

`batch_summary.csv`: 30 rows (2 scenarios x 3 met x 5 pollutants).
Extremes:

| Scenario / met | Pollutant | Peak (ug/m^3) |
|---|---|---|
| highway / night_inversion | NO2 | 136.92 |
| highway / night_inversion | CO | 1688.39 |
| highway / calm_morning | CO | 1160.96 |
| industrial / night_inversion | PM10 | 77.57 |
| industrial / night_inversion | PM2.5 | 33.03 |
| industrial / calm_morning | CO | 461.68 |

Stable night air gives the highest peaks everywhere; windy noon
the lowest. SO2 peaks stay near background (4–5 ug/m^3) because
gas combustion emits very little SO2 (AP-42: 0.6 lb/MMscf).
