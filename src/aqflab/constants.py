"""Physical constants, pollutant properties and unit conversions.

All values are SI unless stated otherwise. Molar masses are standard
atomic-weight values; the ppb <-> microgram/m^3 conversion uses the
ideal-gas molar volume at 25 degC and 1 atm (24.45 L/mol), the
convention used by US EPA AirNow conversions.
"""

# --- Physical constants -------------------------------------------------
GRAVITY = 9.81  # m/s^2
GAS_CONSTANT = 8.314462618  # J/(mol K)
MOLAR_VOLUME_25C = 24.45  # L/mol at 25 degC, 1 atm (EPA convention)
KELVIN_OFFSET = 273.15
LB_TO_G = 453.59237  # exact
SCF_TO_M3 = 0.028316846592  # 1 ft^3 in m^3

# --- Pollutants ----------------------------------------------------------
# molar mass (g/mol); averaging period used for the EPA AQI of each
# pollutant; display unit of ambient concentration.
POLLUTANTS = ("PM2.5", "PM10", "O3", "NO2", "SO2", "CO")

MOLAR_MASS = {
    "O3": 48.00,
    "NO2": 46.01,
    "SO2": 64.07,
    "CO": 28.01,
}

AQI_AVERAGING = {
    "PM2.5": "24-hour",
    "PM10": "24-hour",
    "O3": "8-hour (1-hour above AQI 300)",
    "NO2": "1-hour",
    "SO2": "1-hour (24-hour above AQI 200)",
    "CO": "8-hour",
}

# --- Unit conversions ----------------------------------------------------


def ppb_to_ug_m3(ppb, molar_mass):
    """Convert a gas mixing ratio (ppb) to mass concentration (ug/m^3).

    Uses the EPA convention at 25 degC, 1 atm: ug/m^3 = ppb * MW / 24.45.
    """
    return ppb * molar_mass / MOLAR_VOLUME_25C


def ug_m3_to_ppb(ug_m3, molar_mass):
    """Convert a mass concentration (ug/m^3) to a mixing ratio (ppb)."""
    return ug_m3 * MOLAR_VOLUME_25C / molar_mass


def ppm_to_ug_m3(ppm, molar_mass):
    """Convert a gas mixing ratio (ppm) to mass concentration (ug/m^3)."""
    return ppm * 1000.0 * molar_mass / MOLAR_VOLUME_25C


def ug_m3_to_ppm(ug_m3, molar_mass):
    """Convert a mass concentration (ug/m^3) to a mixing ratio (ppm)."""
    return ug_m3 * MOLAR_VOLUME_25C / (1000.0 * molar_mass)


def celsius_to_kelvin(temp_c):
    """Convert degrees Celsius to kelvin."""
    return temp_c + KELVIN_OFFSET
