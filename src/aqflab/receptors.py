"""Receptor grids and concentration fields.

Receptors live in the local synthetic-city frame (x east, y north,
metres). For each source the receptor coordinates are rotated into
the plume frame (downwind x', crosswind y') using the wind direction
(the direction the wind blows TOWARD, degrees clockwise from north),
the wind speed is adjusted to the release height with the ISC3 power
law, the Briggs plume rise gives the effective height, and the
Gaussian plume equation gives the contribution. Contributions from
all sources and the background add up linearly (superposition holds
for the linear Gaussian model).
"""

import math

from aqflab.dispersion import gaussian_plume
from aqflab.emissions import AreaSource, LineSource, PointSource
from aqflab.plume_rise import plume_rise
from aqflab.stability import wind_speed_at_height


class Receptor:
    """A point where the concentration is evaluated."""

    def __init__(self, x, y, z=0.0, name=None):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.name = name or f"({x:.0f}, {y:.0f})"

    def __repr__(self):
        return f"Receptor({self.name}, x={self.x}, y={self.y}, z={self.z})"


def make_grid(x_min, x_max, y_min, y_max, step, z=0.0):
    """Regular receptor grid; returns a list of Receptor objects."""
    if step <= 0:
        raise ValueError("step must be > 0")
    receptors = []
    nx = int(round((x_max - x_min) / step)) + 1
    ny = int(round((y_max - y_min) / step)) + 1
    for j in range(ny):
        for i in range(nx):
            x = x_min + i * step
            y = y_min + j * step
            receptors.append(Receptor(x, y, z, f"grid_{i}_{j}"))
    return receptors


def rotate_to_plume_frame(dx, dy, wind_direction_deg):
    """Rotate a source->receptor offset into plume coordinates.

    Returns (downwind, crosswind) in metres. Wind direction is the
    direction the wind blows TOWARD, clockwise from north.
    """
    theta = math.radians(wind_direction_deg)
    # Unit vector of the wind (toward): east = sin, north = cos.
    ux, uy = math.sin(theta), math.cos(theta)
    downwind = dx * ux + dy * uy
    crosswind = -dx * uy + dy * ux
    return downwind, crosswind


def _point_contribution(source_x, source_y, release_height, diameter,
                        exit_velocity, exit_temp_c, emission_rate,
                        receptor, met, urban=False,
                        use_plume_rise=True):
    """Gaussian plume contribution (g/m^3) of one point source."""
    dx = receptor.x - source_x
    dy = receptor.y - source_y
    downwind, crosswind = rotate_to_plume_frame(
        dx, dy, met.wind_direction_deg)
    if downwind <= 0 or emission_rate == 0.0:
        return 0.0
    height = release_height
    if use_plume_rise and diameter is not None:
        u_stack = wind_speed_at_height(
            met.wind_speed_10m, 10.0, max(release_height, 10.0),
            met.stability, urban=urban)
        rise = plume_rise(release_height, exit_velocity, diameter,
                          exit_temp_c + 273.15, met.temp_c + 273.15,
                          max(u_stack, 0.5), met.stability,
                          distance=downwind)
        height = rise["effective_height"]
        wind = u_stack
    else:
        wind = wind_speed_at_height(
            met.wind_speed_10m, 10.0, max(height, 10.0),
            met.stability, urban=urban)
    wind = max(wind, 0.5)  # screening floor for near-calm hours
    return gaussian_plume(emission_rate, wind, downwind, crosswind,
                          receptor.z, height, met.stability,
                          urban=urban,
                          mixing_height=met.mixing_height_m)


def concentration_at(receptor, sources, met, pollutant, urban=False,
                     background_ug_m3=0.0):
    """Total concentration (ug/m^3) at one receptor for one pollutant."""
    total_g_m3 = 0.0
    for source in sources:
        if isinstance(source, PointSource):
            total_g_m3 += _point_contribution(
                source.x, source.y, source.stack_height,
                source.diameter, source.exit_velocity,
                source.exit_temp_c, source.emission_rate(pollutant),
                receptor, met, urban=urban)
        elif isinstance(source, AreaSource):
            for px, py, q in source.virtual_points(pollutant):
                total_g_m3 += _point_contribution(
                    px, py, source.release_height, None, 0.0, 25.0,
                    q, receptor, met, urban=urban,
                    use_plume_rise=False)
        elif isinstance(source, LineSource):
            for px, py, q in source.virtual_points(pollutant):
                total_g_m3 += _point_contribution(
                    px, py, source.release_height, None, 0.0, 25.0,
                    q, receptor, met, urban=urban,
                    use_plume_rise=False)
        else:
            raise TypeError(f"unknown source type {type(source)}")
    return total_g_m3 * 1e6 + background_ug_m3


def concentration_field(receptors, sources, met, pollutant, urban=False,
                        background_ug_m3=0.0):
    """Concentrations (ug/m^3) at all receptors; returns a list."""
    return [concentration_at(r, sources, met, pollutant, urban=urban,
                             background_ug_m3=background_ug_m3)
            for r in receptors]


def find_peak(receptors, values):
    """(receptor, value) of the maximum concentration."""
    if not receptors or not values:
        raise ValueError("empty receptor/value lists")
    index = max(range(len(values)), key=lambda i: values[i])
    return receptors[index], values[index]
