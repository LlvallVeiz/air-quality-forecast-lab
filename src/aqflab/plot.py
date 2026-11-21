"""Plotting (matplotlib) and ASCII map fallback.

All plots use the non-interactive Agg backend so they run headless.
When matplotlib is unavailable the CLI still works: maps are
rendered as ASCII grids and time series as tables.
"""


try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except Exception:  # pragma: no cover - exercised only without mpl
    HAS_MATPLOTLIB = False


def ascii_map(xs, ys, values, width=60, height=20, levels=" .:-=+*#%@"):
    """Render a concentration field as an ASCII grid (text fallback)."""
    if not values:
        return "(empty field)"
    vmin, vmax = min(values), max(values)
    span = vmax - vmin if vmax > vmin else 1.0
    # Bin values onto a coarse grid by nearest receptor.
    grid = [[" "] * width for _ in range(height)]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    for x, y, v in zip(xs, ys, values):
        col = int((x - x0) / (x1 - x0 + 1e-9) * (width - 1))
        row = int((y - y0) / (y1 - y0 + 1e-9) * (height - 1))
        idx = int((v - vmin) / span * (len(levels) - 1))
        grid[height - 1 - row][col] = levels[idx]
    lines = ["".join(row) for row in grid]
    lines.append(f"min {vmin:.2f}  max {vmax:.2f} ug/m^3 "
                 f"(low '{levels[0]}' -> high '{levels[-1]}')")
    return "\n".join(lines)


def plot_concentration_map(xs, ys, values, path, title, xlabel="x (m)",
                           ylabel="y (m)"):
    """Filled-contour concentration map (PNG). Requires matplotlib."""
    if not HAS_MATPLOTLIB:
        raise RuntimeError("matplotlib is required for PNG maps")
    x_unique = sorted(set(xs))
    y_unique = sorted(set(ys))
    grid = np.array(values, dtype=float).reshape(
        len(y_unique), len(x_unique))
    fig, ax = plt.subplots(figsize=(8, 6))
    contour = ax.contourf(x_unique, y_unique, grid, levels=20,
                          cmap="YlOrRd")
    fig.colorbar(contour, ax=ax, label="ug/m^3")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_daily_aqi(days, aqi_values, path, title="Daily AQI"):
    """Bar chart of the daily AQI with EPA category colours."""
    if not HAS_MATPLOTLIB:
        raise RuntimeError("matplotlib is required for PNG plots")
    colours = []
    for value in aqi_values:
        if value <= 50:
            colours.append("#00E400")
        elif value <= 100:
            colours.append("#FFFF00")
        elif value <= 150:
            colours.append("#FF7E00")
        elif value <= 200:
            colours.append("#FF0000")
        elif value <= 300:
            colours.append("#8F3F97")
        else:
            colours.append("#7E0023")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(days, aqi_values, color=colours, edgecolor="black")
    for band, label in ((50, "Good"), (100, "Moderate"),
                        (150, "USG"), (200, "Unhealthy"),
                        (300, "Very Unhealthy")):
        ax.axhline(band, color="grey", linestyle="--", linewidth=0.7)
    ax.set_title(title)
    ax.set_xlabel("Day")
    ax.set_ylabel("AQI")
    ax.set_ylim(0, max(320, max(aqi_values) * 1.1))
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_hourly_series(hours, values, path, title, ylabel="ug/m^3"):
    """Line plot of an hourly concentration series."""
    if not HAS_MATPLOTLIB:
        raise RuntimeError("matplotlib is required for PNG plots")
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(hours, values, linewidth=1.2)
    ax.set_title(title)
    ax.set_xlabel("Hour")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
