# Research notes — air-quality-forecast-lab

All methods in this package are textbook/regulatory methods with
verifiable sources. Nothing here measures a real city: the city
("Kota Sinar"), its sources and its meteorology are synthetic, and
every output is labelled as such. This file records what was checked
on 2026-11-20, so a reader can reproduce every number.

## 1. Gaussian plume dispersion

The steady-state Gaussian plume equation for a continuous point
source with total ground reflection (method of images) is the
standard screening model taught in every air-pollution textbook
(Seinfeld & Pandis 2006; Beychok 2005):

    C(x,y,z) = Q / (2*pi*u*sy*sz) * exp(-y^2/(2*sy^2))
               * [exp(-(z-H)^2/(2*sz^2)) + exp(-(z+H)^2/(2*sz^2))]

Assumptions: steady state, continuous release, homogeneous wind,
flat terrain, inert pollutant, no deposition, no chemistry.
The model is a screening tool, not a regulatory model; for permits
the US EPA requires AERMOD.

## 2. Dispersion coefficients — Briggs (1973)

Sigma-y and sigma-z use the Briggs (1973) formulas recommended in
Hanna, Briggs & Hosker, *Handbook on Atmospheric Diffusion*,
DOE/TIC-11223 (1982), Table 4.5, valid for 100 m < x < 10 000 m.
The table was verified against the NRC-hosted excerpt of the
handbook on 2026-11-20 (open-country and urban sets, classes A-F).

Reference: https://ww2.nrc.gov/docs/ML1119/ML11194A167.pdf

Cross-check: the same Briggs open-country/urban formulas are used
in the open-source GasDispersion.jl documentation, which also gives
the Spicer & Havens (1988) / Seinfeld (1986) power-law alternatives
that were NOT used here (the Briggs set was chosen because it is
the one embedded in EPA screening models).

Reference: https://aefarrell.github.io/GasDispersion.jl/dev/plume/

## 3. Plume rise — Briggs (1969/1971/1972)

Implemented as in US EPA screening models (SCREEN3, ISC3) and
documented in Beychok (2005) *Fundamentals of Stack Gas Dispersion*:

- Buoyancy flux Fb = g*vs*d^2*(Ts-Ta)/(4*Ts) [m^4/s^3];
  momentum flux Fm = vs^2*d^2*Ta/(4*Ts) [m^4/s^2].
- Unstable/neutral, buoyant: dh = 1.6*Fb^(1/3)*xf^(2/3)/u with
  xf = 49*Fb^(5/8) (Fb < 55) or 119*Fb^(2/5) (Fb >= 55).
  Closed forms: 21.425*Fb^0.75/u and 38.71*Fb^0.6/u.
- Unstable/neutral, momentum: dh = 3*d^(2/3)*(vs/u)^(1/3).
- Stable, buoyant: dh = min(2.6*(Fb/(u*s))^(1/3),
  5*Fb^(1/4)*s^(-3/8)); stable momentum:
  dh = 1.5*Fm^(1/3)*s^(-1/6)/u^(1/3); calm buoyant:
  dh = 5*Fb^(1/4)*s^(-3/8); calm jet: dh = 4*Fm^(1/4)*s^(-1/4).
- Buoyancy vs momentum is decided by the crossover temperature
  difference dTc (SCREEN3): 0.0297*Ts*vs^(2/3)/d^(1/3) for
  unstable/neutral with Fb < 55, otherwise
  0.00575*Ts*vs^(2/3)/d^(1/3).
- Stack-tip downwash (Briggs): if vs < 1.5*u, subtract
  2*d*(1.5 - vs/u) from the effective height.
- Stability parameter s = (g/Ta)*d(theta)/dz; gradients 0.02 K/m
  (class E) and 0.035 K/m (class F) are the SCREEN3 defaults.

Verification: the worked example in the Mustansiriyah University
lecture notes (Fb = 50 m^4/s^3, u = 4.92 m/s, slightly unstable)
gives dh = 81.78 m; the code's direct formula gives 81.88 m, a
0.1 m difference from the notes' rounded intermediate values
(xf = 565 m). The test suite asserts agreement within 0.15 m and
also asserts the algebraic equivalence with the closed forms
21.425*Fb^0.75/u and 38.71*Fb^0.6/u.

References:
- https://metricgate.com/docs/briggs-plume-rise/
- https://uomustansiriyah.edu.iq/media/lectures/6/6_2023_03_23!11_43_43_PM.pdf
- Gordon (2017), "A comparison of plume rise algorithms",
  Atmos. Chem. Phys. Discuss., https://acp.copernicus.org/preprints/acp-2017-1093/acp-2017-1093-manuscript-version3.pdf
  (documents that Briggs underestimates observed rise by ~50% in
  some field campaigns -- a known limitation, see DESIGN.md).

## 4. Stability classes and wind profile

- Pasquill-Gifford classes A-F (Pasquill 1961; Gifford 1961).
- Turner (1964) classification from surface wind speed, solar
  insolation and cloud cover, as reproduced in Beychok (2005) and
  EPA SCREEN3 documentation. Intermediate entries (A-B, B-C, C-D)
  are resolved to the more stable letter, the conservative
  screening choice.
- Wind-profile power law u(z) = u_ref*(z/z_ref)^p with ISC3
  exponents: rural A 0.10, B 0.15, C 0.20, D 0.25, E 0.30, F 0.30;
  urban A 0.15, B 0.15, C 0.20, D 0.25, E 0.30, F 0.30
  (EPA ISC3 User's Guide, EPA-454/B-95-003).
- Screening mixing heights (A 1500 m ... F 200 m) are typical
  climatological values in the Holzworth tradition, used only when
  a mixing-layer cap is requested; they are not measurements.

## 5. US EPA Air Quality Index (2024 revision)

Breakpoints: 40 CFR Part 58, Appendix G, Table 2, as reproduced in
US EPA, *Technical Assistance Document for the Reporting of Daily
Air Quality -- the Air Quality Index (AQI)*, EPA-454/B-24-002
(May 2024), including the revised PM2.5 breakpoints effective
6 May 2024 (Good ends at 9.0 ug/m^3; AQI 500 at 325.4 ug/m^3).
The table was verified against the EPA document on 2026-11-20.

Reference: https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P101AP0Q.TXT

Rules implemented, exactly as EPA specifies:
- Sub-index: I = (Ihi-Ilo)/(BPhi-Bplo)*(Cp-Bplo)+Ilo, rounded to
  the nearest integer (halves up).
- Truncation before lookup: PM2.5 to 1 decimal, PM10 to integer,
  O3 to 3 decimals, CO to 1 decimal, SO2/NO2 to integer.
- Averaging periods: PM2.5/PM10 24-hour; O3 8-hour (1-hour used
  for AQI > 300); CO 8-hour; NO2 1-hour; SO2 1-hour up to AQI 200,
  24-hour above that.
- Above the last breakpoint, the 301-500 segment slope is continued
  to AQI 500 (except O3 8-hour and SO2 1-hour, which require the
  other averaging period).
- Category colours are the EPA/AirNow standard hex values
  (Good #00E400, Moderate #FFFF00, USG #FF7E00, Unhealthy #FF0000,
  Very Unhealthy #8F3F97, Hazardous #7E0023).

The test suite checks every PM2.5 breakpoint edge (9.0 -> 50,
9.1 -> 51, 35.4 -> 100, 35.5 -> 101, 55.4 -> 150, 55.5 -> 151,
125.4 -> 200, 125.5 -> 201, 225.4 -> 300, 225.5 -> 301,
325.4 -> 500) plus edges for the other five pollutants.

## 6. Emission factors

### 6.1 Stationary combustion — US EPA AP-42

AP-42, Fifth Edition, Section 1.4 "Natural Gas Combustion"
(1998, corrected October 2026), Table 1.4-1, uncontrolled
(lb per 10^6 scf): NOx 100, CO 84, PM2.5 7.6, SO2 0.6, VOC 5.5.
The PM2.5 value (7.6 lb/MMscf) was confirmed in EPA WebFIRE
(SCC 10200602, quality rating D).

References:
- https://www.epa.gov/air-emissions-factors-and-quantification/ap-42-fifth-edition-volume-i-chapter-1-external-0
- https://gaftp.epa.gov/ap42/ch01/s04/bgdocs/b01s04_mar1998.pdf
- https://cfpub.epa.gov/webfire/index.cfm?action=fire.showfactor&factorid=3349

### 6.2 Road transport — Euro 6 type-approval limits

Passenger-car limits in Regulation (EC) No 715/2007 (g/km):
petrol CO 1.0, NOx 0.06, PM 0.005; diesel CO 0.50, NOx 0.08,
PM 0.005. These are LEGAL LIMITS, not measured real-world
emission factors; real-driving (RDE) emissions are typically
higher. They are used here only as transparent screening factors
for a synthetic fleet and are labelled as such in the code, the
scenarios and the README. The EMEP/EEA Guidebook (2023) is the
reference for Tier 1-3 road-transport factors; its Tier 2 table
for passenger cars reports exhaust PM2.5 in g/km by Euro class.

Reference: https://efdb.apps.eea.europa.eu/

### 6.3 Line and area sources

A road is discretised into point sources (finite line source
approximation) and an area source into a grid of virtual point
sources -- the standard screening approach used, for example, in
EPA's SCREEN3 workbook procedures. SO2 from roads is taken as
zero (modern low-sulfur fuel; negligible at screening level) and
O3 is not emitted directly (it is secondary, formed from NOx +
VOC in sunlight -- see DESIGN.md).

## 7. Forecasting

The forecast target is the daily AQI at one receptor. The
"observed" series is synthetic: hourly plume concentrations from
the scenario meteorology, a two-peak diurnal emission profile,
a background level and seeded Gaussian noise, aggregated to the
EPA daily metric (24-hour mean PM, 8-hour max O3/CO, 1-hour max
NO2/SO2). Methods: persistence (tomorrow = today) and AR(1) by
ordinary least squares, iterated forward. Evaluation: MAE, RMSE,
bias and the skill score 1 - MSE(model)/MSE(persistence).
No claim is made about forecast skill for any real city.

## 8. References (full list)

- Beychok, M.R. (2005). *Fundamentals of Stack Gas Dispersion*,
  4th ed.
- Briggs, G.A. (1969). *Plume Rise*. U.S. Atomic Energy Commission.
- Briggs, G.A. (1971, 1972). Plume rise formulas; see also
  Briggs (1975) in *Lectures on Air Pollution and Environmental
  Impact Analysis*.
- Gifford, F.A. (1961). Use of routine meteorological observations
  for estimating atmospheric dispersion. *Nuclear Safety* 2(4).
- Gordon, M. et al. (2017). A comparison of plume rise algorithms.
  *Atmos. Chem. Phys. Discuss.*
- Hanna, S.R., Briggs, G.A. & Hosker, R.P. (1982). *Handbook on
  Atmospheric Diffusion*, DOE/TIC-11223.
- Pasquill, F. (1961). The estimation of the dispersion of windborne
  material. *Meteorological Magazine* 90.
- Seinfeld, J.H. & Pandis, S.N. (2006). *Atmospheric Chemistry and
  Physics*, 2nd ed., Wiley.
- Spicer, T. & Havens, J. (1988). Dispersion coefficients, as
  tabulated in GasDispersion.jl documentation.
- Turner, D.B. (1964). A diffusion model for an urban area.
  *J. Appl. Meteorol.* 3.
- US EPA (1995). *User's Guide for the Industrial Source Complex
  (ISC3) Dispersion Models*, EPA-454/B-95-003.
- US EPA (1995). *SCREEN3 Model User's Guide*, EPA-454/B-95-004.
- US EPA (1998, corr. Oct 2026). AP-42, Fifth Edition, Section 1.4,
  *Natural Gas Combustion*, Table 1.4-1.
- US EPA (2024). *Technical Assistance Document for the Reporting
  of Daily Air Quality -- the Air Quality Index (AQI)*,
  EPA-454/B-24-002.
- US EPA (2024). 40 CFR Part 58, Appendix G, Table 2 (AQI
  breakpoints, incl. the 6 May 2024 PM2.5 revision).
- EMEP/EEA (2023). *Air Pollutant Emission Inventory Guidebook*,
  Chapter 1.A.3.b (road transport).
- European Union (2007). Regulation (EC) No 715/2007 (Euro 5/6
  type-approval emission limits).
