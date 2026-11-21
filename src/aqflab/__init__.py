"""air-quality-forecast-lab (aqflab).

End-to-end air-quality laboratory: Gaussian plume dispersion (Briggs),
US EPA Air Quality Index, and short-range AQI forecasting for a
synthetic city. All concentrations are SI (g/m^3 internally,
microgram/m^3 in outputs); the city, sources and meteorology are
synthetic and labelled as such.
"""

from aqflab.aqi import aqi_from_concentrations, category, sub_index
from aqflab.dispersion import gaussian_plume, ground_level_centerline
from aqflab.plume_rise import effective_stack_height

__version__ = "1.0.0"
__all__ = [
    "aqi_from_concentrations",
    "category",
    "effective_stack_height",
    "gaussian_plume",
    "ground_level_centerline",
    "sub_index",
]
