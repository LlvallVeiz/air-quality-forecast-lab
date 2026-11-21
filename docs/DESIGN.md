# Design decisions, limitations and future work

## Design decisions

1. **Stdlib-first core.** The dispersion, AQI, plume-rise,
   emissions, meteorology and forecast modules use only the Python
   standard library. NumPy/Matplotlib are optional and used only
   for plots; pytest is needed only for the test suite. This keeps
   the package runnable anywhere Python 3.10+ exists.
2. **SI internally, ug/m^3 in outputs.** Emission rates are g/s,
   concentrations g/m^3 internally and ug/m^3 in every output.
   AQI inputs use the EPA breakpoint units (ug/m^3 PM, ppm O3/CO,
   ppb SO2/NO2) and the conversions use the EPA 25 degC convention
   (molar volume 24.45 L/mol).
3. **Briggs (1973) sigma set, not the PG curve fits.** The Briggs
   open-country/urban formulas are the set embedded in EPA
   screening models (SCREEN3/ISC3) and are closed-form, so every
   value is reproducible without curve digitisation. The
   Spicer-Havens/Seinfeld power-law alternative is documented in
   RESEARCH.md but not implemented.
4. **Gradual plume rise.** In unstable/neutral air the rise is
   evaluated at the receptor's downwind distance (capped at the
   final-rise distance), following the EPA guidance that plume
   rise must be computed at the receptor distance, not only as a
   final value.
5. **Turner intermediates resolve to the more stable class**
   (A-B -> B). Conservative for screening: less dispersion, higher
   ground-level values.
6. **"Mixed" meteorology for multi-day runs.** A 10-day run that
   repeats one day is unrealistic; the `mixed` mode rotates the
   three scenarios day by day with seeded jitter, so the daily AQI
   actually varies and the forecast comparison is meaningful.
7. **AR(1) falls back to persistence** on a constant training
   series (no variance to fit). The strict fitter still raises;
   the forecaster is the robust layer.
8. **Ozone is not modelled photochemically.** O3 appears only in
   the AQI module (from a given concentration) and in the forecast
   through its background level. A real O3 forecast needs a
   photochemical model (NOx + VOC + sunlight); that is out of
   scope and stated in the README.

## Limitations (honest list)

- **Screening model, not regulatory.** No terrain, no building
  downwash (except the stack-tip correction), no deposition, no
  chemistry, no fumigation, no calm-wind meandering. For permits
  use AERMOD/CALPUFF.
- **Briggs formulas are valid for 100 m < x < 10 km** and flat
  terrain. The grid extends to 4 km downwind; peaks that fall on
  the grid edge (e.g. NO2 in the industrial park, which peaks at
  x = 3000-4000 m) are "peak within the grid", not the true
  far-field maximum -- see `dispersion.peak_distance` for the
  centreline maximum.
- **Briggs plume rise underestimates observed rise** in some field
  campaigns (Gordon et al. 2017: >50% of predictions below half
  the observed height for oil-sands stacks). Treat effective
  heights as screening estimates.
- **Emission factors are screening values.** AP-42 natural-gas
  factors are averages with quality ratings as low as D; Euro 6
  road factors are type-approval limits, not real-world
  measurements. The yard dust rates are scenario assumptions.
- **Meteorology is synthetic.** The three scenarios are textbook
  diurnal patterns, not observations. No result here describes
  any real city.
- **Forecast skill is measured against a synthetic truth.**
  AR(1) beating persistence by a skill score of +0.397 on this
  10-day synthetic series says the method works on this series,
  nothing about real-world predictability.
- **Wind is steady per hour and uniform in space.** No
  hourly-varying wind direction within a day except the scenario
  pattern; the plume axis is fixed per hour.
- **SO2 from roads is zero** and **O3 has no source term** in the
  plume model (see RESEARCH.md 6.3).

## Future work

- AERMOD-style sigma curves (PG curve fits) as an alternative set.
- Simple O3 parameterisation (e.g. EKMA-style or a NOx-limited
  empirical curve) with clearly labelled uncertainty.
- Building downwash (Schulman-Scire / PRIME-style screening).
- Deposition and a first-order decay term for SO2/NO2.
- Wind-direction rotation per hour in the forecast series.
- NetCDF/GeoTIFF grid export for GIS use.
