"""Short-range forecasting: synthetic series, persistence and AR(1).

The forecast target is the DAILY AQI (or daily mean PM2.5) at one
receptor over a 7-day horizon. The "observed" series is synthetic:
hourly concentrations are built from the plume model driven by the
scenario meteorology, a diurnal emission profile, a background level
and seeded Gaussian noise, then aggregated to the daily metric that
the EPA AQI uses (24-hour mean for PM, 8-hour maximum for O3/CO,
1-hour maximum for NO2/SO2). Two forecast methods are compared:

- persistence: tomorrow = today (the baseline every forecast must
  beat);
- AR(1): ordinary least squares on the daily series, iterated forward.

Evaluation on a hold-out tail reports MAE, RMSE, bias and the skill
score 1 - MSE(model)/MSE(persistence). Nothing here is a claim about
forecast skill for any real city: the "truth" is synthetic by design.
"""

import math
import random

from aqflab.aqi import aqi_from_concentrations
from aqflab.constants import MOLAR_MASS, ug_m3_to_ppb, ug_m3_to_ppm
from aqflab.meteorology import diurnal_emission_factor, \
    generate_met_series
from aqflab.receptors import concentration_at


def _rolling_max_8h(hourly):
    """Maximum 8-hour running mean of an hourly series."""
    if len(hourly) < 8:
        return max(hourly) if hourly else 0.0
    best = 0.0
    for i in range(len(hourly) - 7):
        mean = sum(hourly[i:i + 8]) / 8.0
        best = max(best, mean)
    return best


def build_hourly_series(sources, receptor, pollutant, met_series,
                        background_ug_m3, noise_std=0.0, seed=7,
                        urban=False, diurnal=True):
    """Hourly concentrations (ug/m^3) at a receptor for a met series.

    The plume contribution is scaled by the diurnal emission factor
    and added to the background; seeded Gaussian noise is added last
    (negative values are clipped at zero).
    """
    rng = random.Random(seed)
    hourly = []
    for met in met_series:
        factor = diurnal_emission_factor(met.hour) if diurnal else 1.0
        # The plume concentration is linear in Q, so evaluate the
        # source part once and scale it by the diurnal factor.
        plume_only = concentration_at(
            receptor, sources, met, pollutant, urban=urban,
            background_ug_m3=0.0)
        value = background_ug_m3 + factor * plume_only
        if noise_std:
            value += rng.gauss(0.0, noise_std)
        hourly.append(max(0.0, value))
    return hourly


def daily_aggregates(hourly, pollutant):
    """Daily EPA averaging metrics from an hourly series (ug/m^3).

    Returns a list of one value per day: 24-hour mean for PM,
    8-hour maximum for O3/CO, 1-hour maximum for NO2/SO2.
    """
    if len(hourly) % 24 != 0:
        raise ValueError("hourly series length must be a multiple of 24")
    days = len(hourly) // 24
    out = []
    for d in range(days):
        chunk = hourly[d * 24:(d + 1) * 24]
        if pollutant in ("PM2.5", "PM10"):
            out.append(sum(chunk) / 24.0)
        elif pollutant in ("O3", "CO"):
            out.append(_rolling_max_8h(chunk))
        else:
            out.append(max(chunk))
    return out


def daily_aqi_series(hourly_by_pollutant):
    """Daily AQI values from {pollutant: hourly ug/m^3 series}.

    Hourly ug/m^3 are converted to the breakpoint units (ppm for
    O3/CO, ppb for NO2/SO2) before the daily aggregation. Returns
    (aqi_values, daily_ug_m3): the daily AQI list and the daily
    aggregated concentrations converted BACK to ug/m^3, so callers
    always report concentrations in a single unit.
    """
    from aqflab.constants import ppm_to_ug_m3, ppb_to_ug_m3
    daily = {}
    for pollutant, hourly in hourly_by_pollutant.items():
        if pollutant in ("O3", "CO"):
            converted = [ug_m3_to_ppm(v, MOLAR_MASS[pollutant])
                         for v in hourly]
        elif pollutant in ("NO2", "SO2"):
            converted = [ug_m3_to_ppb(v, MOLAR_MASS[pollutant])
                         for v in hourly]
        else:
            converted = list(hourly)
        daily[pollutant] = daily_aggregates(converted, pollutant)
    daily_ug_m3 = {}
    for pollutant, values in daily.items():
        if pollutant in ("O3", "CO"):
            daily_ug_m3[pollutant] = [
                ppm_to_ug_m3(v, MOLAR_MASS[pollutant]) for v in values]
        elif pollutant in ("NO2", "SO2"):
            daily_ug_m3[pollutant] = [
                ppb_to_ug_m3(v, MOLAR_MASS[pollutant]) for v in values]
        else:
            daily_ug_m3[pollutant] = list(values)
    n_days = len(next(iter(daily.values())))
    aqi_values = []
    for d in range(n_days):
        conc = {pol: series[d] for pol, series in daily.items()}
        aqi_values.append(aqi_from_concentrations(conc)["aqi"])
    return aqi_values, daily_ug_m3


def persistence_forecast(series, horizon):
    """Forecast the next ``horizon`` steps as the last observed value."""
    if not series:
        raise ValueError("series must be non-empty")
    return [series[-1]] * horizon


def fit_ar1(series):
    """OLS AR(1) fit: x_t = c + phi * x_{t-1} + eps.

    Returns (c, phi). Raises ValueError for series shorter than 3 or
    with zero variance in the lagged values.
    """
    if len(series) < 3:
        raise ValueError("AR(1) needs at least 3 observations")
    x = series[:-1]
    y = series[1:]
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    num = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    den = sum((a - mean_x) ** 2 for a in x)
    if den == 0:
        raise ValueError("AR(1) undefined: lagged values are constant")
    phi = num / den
    c = mean_y - phi * mean_x
    return c, phi


def ar1_forecast(series, horizon):
    """Iterated AR(1) forecast for the next ``horizon`` steps.

    Falls back to persistence when the series has no variance to fit
    (a constant training series has no identifiable AR(1)).
    """
    try:
        c, phi = fit_ar1(series)
    except ValueError:
        return persistence_forecast(series, horizon)
    out = []
    last = series[-1]
    for _ in range(horizon):
        last = c + phi * last
        out.append(last)
    return out


def evaluate(observed, predicted):
    """MAE, RMSE and bias of a forecast against observations."""
    if len(observed) != len(predicted) or not observed:
        raise ValueError("observed and predicted must be non-empty "
                         "and of equal length")
    errors = [p - o for o, p in zip(observed, predicted)]
    mae = sum(abs(e) for e in errors) / len(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    bias = sum(errors) / len(errors)
    return {"mae": mae, "rmse": rmse, "bias": bias,
            "n": len(observed)}


def skill_score(observed, predicted, baseline_predicted):
    """Skill score 1 - MSE(model)/MSE(baseline); > 0 beats baseline."""
    model = evaluate(observed, predicted)
    base = evaluate(observed, baseline_predicted)
    if base["rmse"] == 0:
        return 0.0
    return 1.0 - (model["rmse"] ** 2) / (base["rmse"] ** 2)


def run_forecast(sources, receptor, pollutants, backgrounds, days=10,
                 horizon=3, scenario="calm_morning", seed=42,
                 noise_std=2.0, urban=False):
    """End-to-end forecast experiment at one receptor.

    Builds ``days`` of synthetic hourly data, fits persistence and
    AR(1) on all but the last ``horizon`` days, forecasts them, and
    evaluates both methods. Returns a dict with the daily AQI series,
    both forecasts and the evaluation metrics.
    """
    met = generate_met_series(days, scenario=scenario, seed=seed)
    hourly_by_pollutant = {}
    for pollutant in pollutants:
        hourly_by_pollutant[pollutant] = build_hourly_series(
            sources, receptor, pollutant, met,
            backgrounds.get(pollutant, 0.0), noise_std=noise_std,
            seed=seed, urban=urban)
    aqi_series, daily = daily_aqi_series(hourly_by_pollutant)
    train, test = aqi_series[:-horizon], aqi_series[-horizon:]
    persistence = persistence_forecast(train, horizon)
    ar1 = ar1_forecast(train, horizon)
    metrics = {
        "persistence": evaluate(test, persistence),
        "ar1": evaluate(test, ar1),
    }
    metrics["ar1_skill_vs_persistence"] = skill_score(
        test, ar1, persistence)
    return {"daily_aqi": aqi_series, "daily_conc": daily,
            "train": train, "test": test,
            "persistence_forecast": persistence,
            "ar1_forecast": ar1, "metrics": metrics,
            "horizon": horizon}
