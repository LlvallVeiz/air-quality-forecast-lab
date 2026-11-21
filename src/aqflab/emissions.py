"""Emission inventory: point, area and line sources.

Emission factors are taken from public sources and cited in
docs/RESEARCH.md:

- Stationary combustion: US EPA AP-42, Fifth Edition, Section 1.4
  "Natural Gas Combustion" (1998, corrected October 2026), Table 1.4-1
  (uncontrolled): NOx 100, CO 84, PM2.5 7.6, SO2 0.6, VOC 5.5
  lb per 10^6 scf of natural gas burned. (PM2.5 7.6 lb/MMscf confirmed
  in EPA WebFIRE, SCC 10200602.)
- Road transport: Euro 6 type-approval LIMITS (Regulation (EC)
  No 715/2007) for passenger cars -- petrol CO 1.0, NOx 0.06,
  PM 0.005 g/km; diesel CO 0.50, NOx 0.08, PM 0.005 g/km. These are
  legal limits, NOT measured real-world emission factors; real-world
  (RDE) emissions are typically higher. They are used here only as
  transparent screening factors for a synthetic fleet, and are
  labelled as such everywhere they appear.

Line sources are discretised into point sources (finite line source
approximation) and area sources into a grid of virtual point sources,
the standard screening approach.
"""

import json
import math

from aqflab.constants import LB_TO_G

# --- AP-42 Section 1.4, Table 1.4-1 (lb per 10^6 scf natural gas) -----
AP42_NATURAL_GAS_LB_PER_MMSCF = {
    "NO2": 100.0,   # as NOx, expressed as NO2
    "CO": 84.0,
    "PM2.5": 7.6,
    "SO2": 0.6,
    "VOC": 5.5,
}

# --- Euro 6 type-approval limits, passenger cars (g/km) -----------------
EURO6_LIMITS_G_PER_KM = {
    "petrol": {"CO": 1.0, "NO2": 0.06, "PM2.5": 0.005, "PM10": 0.005},
    "diesel": {"CO": 0.50, "NO2": 0.08, "PM2.5": 0.005, "PM10": 0.005},
}

MMSCF_PER_DAY_TO_SCF_PER_S = 1e6 / 86400.0


def ap42_gas_emission_rate(factor_lb_per_mmscf, fuel_mmscf_per_day):
    """Convert an AP-42 factor (lb/MMscf) to an emission rate (g/s)."""
    if factor_lb_per_mmscf < 0 or fuel_mmscf_per_day < 0:
        raise ValueError("factor and fuel rate must be >= 0")
    lb_per_day = factor_lb_per_mmscf * fuel_mmscf_per_day
    return lb_per_day * LB_TO_G / 86400.0


def gas_boiler_emissions(fuel_mmscf_per_day):
    """Emission rates (g/s) of a gas boiler from AP-42 Table 1.4-1."""
    return {pol: ap42_gas_emission_rate(f, fuel_mmscf_per_day)
            for pol, f in AP42_NATURAL_GAS_LB_PER_MMSCF.items()}


def fleet_emission_factor(pollutant, fleet_mix):
    """Fleet-average road factor (g/km/vehicle) from Euro 6 limits.

    ``fleet_mix`` maps fuel ("petrol"/"diesel") to a share in [0, 1];
    shares must sum to 1.
    """
    if abs(sum(fleet_mix.values()) - 1.0) > 1e-9:
        raise ValueError("fleet shares must sum to 1")
    total = 0.0
    for fuel, share in fleet_mix.items():
        if fuel not in EURO6_LIMITS_G_PER_KM:
            raise ValueError(f"unknown fuel {fuel!r}")
        factors = EURO6_LIMITS_G_PER_KM[fuel]
        if pollutant not in factors:
            raise ValueError(
                f"no Euro 6 limit for {pollutant!r} ({fuel})")
        total += share * factors[pollutant]
    return total


class PointSource:
    """A stack (point) source.

    Coordinates are metres in the local synthetic-city frame; ``x``
    east, ``y`` north. Emissions are g/s per pollutant.
    """

    kind = "point"

    def __init__(self, name, x, y, stack_height, diameter,
                 exit_velocity, exit_temp_c, emissions,
                 ambient_temp_c=25.0):
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.stack_height = float(stack_height)
        self.diameter = float(diameter)
        self.exit_velocity = float(exit_velocity)
        self.exit_temp_c = float(exit_temp_c)
        self.ambient_temp_c = float(ambient_temp_c)
        self.emissions = {k: float(v) for k, v in emissions.items()}
        if self.stack_height < 0 or self.diameter <= 0:
            raise ValueError("stack_height >= 0, diameter > 0 required")
        if self.exit_velocity < 0:
            raise ValueError("exit_velocity must be >= 0")
        for pol, rate in self.emissions.items():
            if rate < 0:
                raise ValueError(f"negative emission rate for {pol}")

    def emission_rate(self, pollutant):
        """Emission rate (g/s) of ``pollutant`` (0 if not emitted)."""
        return self.emissions.get(pollutant, 0.0)

    def to_dict(self):
        """JSON-serialisable representation."""
        return {"kind": self.kind, "name": self.name, "x": self.x,
                "y": self.y, "stack_height": self.stack_height,
                "diameter": self.diameter,
                "exit_velocity": self.exit_velocity,
                "exit_temp_c": self.exit_temp_c,
                "ambient_temp_c": self.ambient_temp_c,
                "emissions": self.emissions}

    @classmethod
    def from_dict(cls, data):
        """Rebuild a PointSource from :meth:`to_dict` output."""
        return cls(data["name"], data["x"], data["y"],
                   data["stack_height"], data["diameter"],
                   data["exit_velocity"], data["exit_temp_c"],
                   data["emissions"],
                   data.get("ambient_temp_c", 25.0))


class AreaSource:
    """An area source (e.g. an industrial yard), discretised into a
    grid of virtual point sources at ``release_height``."""

    kind = "area"

    def __init__(self, name, x, y, width, length, release_height,
                 emissions, cells_x=5, cells_y=5):
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.width = float(width)
        self.length = float(length)
        self.release_height = float(release_height)
        self.emissions = {k: float(v) for k, v in emissions.items()}
        self.cells_x = int(cells_x)
        self.cells_y = int(cells_y)
        if self.width <= 0 or self.length <= 0:
            raise ValueError("width and length must be > 0")
        if self.cells_x < 1 or self.cells_y < 1:
            raise ValueError("cells_x/cells_y must be >= 1")
        for pol, rate in self.emissions.items():
            if rate < 0:
                raise ValueError(f"negative emission rate for {pol}")

    def virtual_points(self, pollutant):
        """List of (x, y, Q g/s) virtual point sources for one pollutant."""
        total = self.emissions.get(pollutant, 0.0)
        n = self.cells_x * self.cells_y
        points = []
        for i in range(self.cells_x):
            for j in range(self.cells_y):
                px = self.x - self.width / 2.0 \
                    + (i + 0.5) * self.width / self.cells_x
                py = self.y - self.length / 2.0 \
                    + (j + 0.5) * self.length / self.cells_y
                points.append((px, py, total / n))
        return points

    def emission_rate(self, pollutant):
        """Total emission rate (g/s) of ``pollutant``."""
        return self.emissions.get(pollutant, 0.0)

    def to_dict(self):
        """JSON-serialisable representation."""
        return {"kind": self.kind, "name": self.name, "x": self.x,
                "y": self.y, "width": self.width, "length": self.length,
                "release_height": self.release_height,
                "emissions": self.emissions,
                "cells_x": self.cells_x, "cells_y": self.cells_y}

    @classmethod
    def from_dict(cls, data):
        """Rebuild an AreaSource from :meth:`to_dict` output."""
        return cls(data["name"], data["x"], data["y"], data["width"],
                   data["length"], data["release_height"],
                   data["emissions"], data.get("cells_x", 5),
                   data.get("cells_y", 5))


class LineSource:
    """A road (line) source, discretised into point sources.

    Emissions are given per vehicle-kilometre (g/km/vehicle) and a
    traffic flow (vehicles/hour); the line emission rate is
    q = flow * factor / 3.6e6 g/(s m).
    """

    kind = "line"

    def __init__(self, name, x1, y1, x2, y2, traffic_veh_per_hour,
                 fleet_mix, release_height=2.0, segments=20):
        self.name = name
        self.x1, self.y1 = float(x1), float(y1)
        self.x2, self.y2 = float(x2), float(y2)
        self.traffic = float(traffic_veh_per_hour)
        self.fleet_mix = dict(fleet_mix)
        self.release_height = float(release_height)
        self.segments = int(segments)
        if self.traffic < 0:
            raise ValueError("traffic must be >= 0")
        if self.segments < 1:
            raise ValueError("segments must be >= 1")
        if math.hypot(self.x2 - self.x1, self.y2 - self.y1) <= 0:
            raise ValueError("line source must have non-zero length")
        # Validate the fleet mix now so bad input fails fast.
        fleet_emission_factor("NO2", self.fleet_mix)

    @property
    def length(self):
        """Road length (m)."""
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    def line_emission_rate(self, pollutant):
        """Emission rate per unit length (g/(s m)) of ``pollutant``.

        Pollutants without a Euro 6 road factor (e.g. SO2, O3) are
        taken as zero for the road: SO2 from modern low-sulfur fuel
        is negligible at screening level and O3 is secondary.
        """
        if pollutant not in ("CO", "NO2", "PM2.5", "PM10"):
            return 0.0
        factor = fleet_emission_factor(pollutant, self.fleet_mix)
        return self.traffic * factor / 3.6e6

    def emission_rate(self, pollutant):
        """Total emission rate (g/s) of ``pollutant`` along the road."""
        return self.line_emission_rate(pollutant) * self.length

    def virtual_points(self, pollutant):
        """List of (x, y, Q g/s) point sources along the road."""
        total = self.emission_rate(pollutant)
        points = []
        for i in range(self.segments):
            t = (i + 0.5) / self.segments
            px = self.x1 + t * (self.x2 - self.x1)
            py = self.y1 + t * (self.y2 - self.y1)
            points.append((px, py, total / self.segments))
        return points

    def to_dict(self):
        """JSON-serialisable representation."""
        return {"kind": self.kind, "name": self.name,
                "x1": self.x1, "y1": self.y1,
                "x2": self.x2, "y2": self.y2,
                "traffic_veh_per_hour": self.traffic,
                "fleet_mix": self.fleet_mix,
                "release_height": self.release_height,
                "segments": self.segments}

    @classmethod
    def from_dict(cls, data):
        """Rebuild a LineSource from :meth:`to_dict` output."""
        return cls(data["name"], data["x1"], data["y1"], data["x2"],
                   data["y2"], data["traffic_veh_per_hour"],
                   data["fleet_mix"], data.get("release_height", 2.0),
                   data.get("segments", 20))


def source_from_dict(data):
    """Rebuild any source from its :meth:`to_dict` output."""
    kind = data.get("kind")
    if kind == "point":
        return PointSource.from_dict(data)
    if kind == "area":
        return AreaSource.from_dict(data)
    if kind == "line":
        return LineSource.from_dict(data)
    raise ValueError(f"unknown source kind {kind!r}")


class Inventory:
    """A collection of sources with per-pollutant totals."""

    def __init__(self, sources=()):
        self.sources = list(sources)

    def add(self, source):
        """Add a source to the inventory."""
        self.sources.append(source)

    def total(self, pollutant):
        """Total emission rate (g/s) of ``pollutant`` over all sources."""
        return sum(s.emission_rate(pollutant) for s in self.sources)

    def totals(self):
        """Dict of total emission rates (g/s) for every pollutant."""
        pollutants = set()
        for source in self.sources:
            if isinstance(source, (PointSource, AreaSource)):
                pollutants.update(source.emissions)
            else:
                pollutants.update(("NO2", "CO", "PM2.5", "PM10"))
        return {pol: self.total(pol) for pol in sorted(pollutants)}

    def to_json(self, path):
        """Write the inventory to a JSON file."""
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([s.to_dict() for s in self.sources], fh, indent=2)

    @classmethod
    def from_json(cls, path):
        """Read an inventory from a JSON file."""
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls([source_from_dict(item) for item in data])
