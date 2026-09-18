"""ECharts option builders that follow the project's visualization rules.

The rules these functions enforce so individual pages cannot break them:

  * NO DUAL AXIS, ever. Two measures on different scales become two charts.
    There is deliberately no API here for a second y-axis.
  * Colour follows the ENTITY, not the rank. Copart is always series slot 1
    (blue); RB Global / IAA is always slot 2 (orange). Filtering or reordering
    never repaints a company.
  * Thin marks: 2px lines, >=8px markers, 4px rounded bar ends anchored to the
    baseline, hairline solid gridlines (never dashed).
  * A legend whenever there are 2+ series; none for a single series, because the
    title already names it.
  * Every chart ships a hover tooltip AND a table-view twin, so no value is
    reachable only by hovering.
  * Text keeps text tokens; it never wears the series colour.

Colours are emitted as role tokens like "@series-1". The page's JavaScript
resolves them from CSS custom properties at render time, which is what lets
light and dark mode swap without rebuilding the data.
"""

from __future__ import annotations

from typing import Any, Iterable

# Role tokens resolved client-side against CSS custom properties.
SERIES = ["@series-1", "@series-2", "@series-3", "@series-4", "@series-5"]
INK_PRIMARY = "@text-primary"
INK_SECONDARY = "@text-secondary"
INK_MUTED = "@text-muted"
GRIDLINE = "@gridline"
BASELINE = "@baseline"
SURFACE = "@surface-1"
STATUS = {
    "good": "@status-good",
    "warning": "@status-warning",
    "serious": "@status-serious",
    "critical": "@status-critical",
}

# Fixed entity -> colour slot. This is the "colour follows the entity" rule made
# explicit, so every chart in the deck agrees.
ENTITY_COLOR = {
    "Copart": SERIES[0],
    "CPRT": SERIES[0],
    "RB Global": SERIES[1],
    "RB Global / IAA": SERIES[1],
    "IAA": SERIES[1],
    "RBA": SERIES[1],
    "Consensus": SERIES[2],
    "ACV Auctions": SERIES[2],
    "Progressive": SERIES[2],
}


def entity_color(name: str, fallback_index: int = 0) -> str:
    return ENTITY_COLOR.get(name, SERIES[fallback_index % len(SERIES)])


# --------------------------------------------------------------------------
# Shared chrome
# --------------------------------------------------------------------------
def _axis_label(extra: dict | None = None) -> dict:
    base = {
        "color": INK_MUTED,
        "fontSize": 11,
        # tabular figures so axis ticks align vertically
        "fontFamily": 'system-ui, -apple-system, "Segoe UI", sans-serif',
    }
    if extra:
        base.update(extra)
    return base


def _category_axis(categories: Iterable[str], *, rotate: int = 0) -> dict:
    return {
        "type": "category",
        "data": list(categories),
        "axisLine": {"show": True, "lineStyle": {"color": BASELINE, "width": 1}},
        "axisTick": {"show": False},
        "axisLabel": _axis_label({"rotate": rotate, "hideOverlap": True}),
        "splitLine": {"show": False},
    }


def _value_axis(
    *,
    name: str = "",
    formatter: str = "{value}",
    min_: Any = None,
    max_: Any = None,
) -> dict:
    # Deliberately NO axis name. An axis name sits at the top-left of the value
    # axis, which is exactly where the legend sits, and the two collide. Units
    # ride on the tick formatter instead (a "%" suffix or a "$" prefix), with
    # the full unit spelled out in the card subtitle and the table header.
    axis = {
        "type": "value",
        "axisLine": {"show": False},
        "axisTick": {"show": False},
        "axisLabel": _axis_label({"formatter": formatter}),
        # Solid hairline grid, one shade off the surface. Never dashed.
        "splitLine": {"show": True, "lineStyle": {"color": GRIDLINE, "width": 1, "type": "solid"}},
    }
    if min_ is not None:
        axis["min"] = min_
    if max_ is not None:
        axis["max"] = max_
    return axis


def _tooltip(*, trigger: str = "axis", value_suffix: str = "", decimals: int = 1) -> dict:
    return {
        "trigger": trigger,
        "axisPointer": {
            "type": "line",
            "lineStyle": {"color": BASELINE, "width": 1},
        },
        "backgroundColor": SURFACE,
        "borderColor": GRIDLINE,
        "borderWidth": 1,
        "padding": [8, 10],
        "textStyle": {"color": INK_PRIMARY, "fontSize": 12},
        "extraCssText": "box-shadow:0 4px 16px rgba(0,0,0,0.10);border-radius:6px;",
        # valueSuffix/decimals are read by the page's shared formatter
        "valueSuffix": value_suffix,
        "valueDecimals": decimals,
    }


def _legend(show: bool) -> dict:
    if not show:
        return {"show": False}
    return {
        "show": True,
        "top": 0,
        "left": 0,
        "itemWidth": 10,
        "itemHeight": 10,
        "itemGap": 16,
        "icon": "roundRect",
        "textStyle": {"color": INK_SECONDARY, "fontSize": 11},
    }


def _grid(*, legend: bool, rotate: int = 0, left: int = 8) -> dict:
    return {
        "left": left,
        "right": 14,
        "top": 26 if legend else 16,
        # Leave room for the x-axis band so labels are never clipped.
        "bottom": 34 if rotate else 6,
        "containLabel": True,
    }


def _base_option(*, legend: bool, rotate: int = 0) -> dict:
    return {
        "animationDuration": 400,
        "textStyle": {"fontFamily": 'system-ui, -apple-system, "Segoe UI", sans-serif'},
        "legend": _legend(legend),
        "grid": _grid(legend=legend, rotate=rotate),
    }


# --------------------------------------------------------------------------
# Bar
# --------------------------------------------------------------------------
def bar(
    categories: list[str],
    series: list[dict],
    *,
    value_suffix: str = "",
    value_prefix: str = "",
    decimals: int = 1,
    y_name: str = "",
    rotate: int = 0,
    horizontal: bool = False,
    color_by_sign: bool = False,
) -> dict:
    """Grouped bar chart.

    series: [{"name": str, "data": [...], "color": token (optional)}]
    color_by_sign: single-series only. Positive bars take the 'good' status
    colour and negative bars 'critical'. Only use this where the sign genuinely
    means good/bad (unit growth, surprise vs consensus) - never for identity.
    """
    show_legend = len(series) > 1
    opt = _base_option(legend=show_legend, rotate=rotate)
    opt["tooltip"] = _tooltip(trigger="axis", value_suffix=value_suffix, decimals=decimals)

    cat = _category_axis(categories, rotate=rotate)
    val = _value_axis(formatter=(value_prefix or "") + "{value}" + (value_suffix or ""))
    if horizontal:
        opt["xAxis"], opt["yAxis"] = val, cat
        opt["yAxis"]["inverse"] = True
    else:
        opt["xAxis"], opt["yAxis"] = cat, val

    out = []
    for i, s in enumerate(series):
        color = s.get("color") or entity_color(s["name"], i)
        radius = [0, 4, 4, 0] if horizontal else [4, 4, 0, 0]
        item_style: dict = {"borderRadius": radius}
        if color_by_sign and len(series) == 1:
            item_style["color"] = {
                "__fn": "signColor",
                "positive": STATUS["good"],
                "negative": STATUS["critical"],
            }
        else:
            item_style["color"] = color
        out.append(
            {
                "name": s["name"],
                "type": "bar",
                "data": s["data"],
                "itemStyle": item_style,
                "barMaxWidth": 34,
                # A visible gap between adjacent bars rather than a border.
                "barGap": "12%",
                "barCategoryGap": "34%",
                **({"label": s["label"]} if "label" in s else {}),
                **({"markLine": s["markLine"]} if "markLine" in s else {}),
            }
        )
    opt["series"] = out
    return opt


# --------------------------------------------------------------------------
# Line / area
# --------------------------------------------------------------------------
def line(
    categories: list[str],
    series: list[dict],
    *,
    value_suffix: str = "",
    value_prefix: str = "",
    decimals: int = 1,
    y_name: str = "",
    rotate: int = 0,
    y_min: Any = None,
    y_max: Any = None,
    zero_line: bool = False,
) -> dict:
    """Multi-series line chart.

    series entries may set:
      color, dashed (bool), area (bool), show_symbol (bool), width (int),
      label_last (bool) to direct-label the final point.
    """
    show_legend = len(series) > 1
    opt = _base_option(legend=show_legend, rotate=rotate)
    opt["tooltip"] = _tooltip(trigger="axis", value_suffix=value_suffix, decimals=decimals)
    opt["xAxis"] = _category_axis(categories, rotate=rotate)
    opt["xAxis"]["boundaryGap"] = False
    opt["yAxis"] = _value_axis(
        formatter=(value_prefix or "") + "{value}" + (value_suffix or ""),
        min_=y_min, max_=y_max,
    )

    out = []
    for i, s in enumerate(series):
        color = s.get("color") or entity_color(s["name"], i)
        spec: dict = {
            "name": s["name"],
            "type": "line",
            "data": s["data"],
            "smooth": False,
            "connectNulls": s.get("connect_nulls", False),
            "symbol": "circle",
            "symbolSize": 8,
            "showSymbol": s.get("show_symbol", len(categories) <= 20),
            "lineStyle": {
                "width": s.get("width", 2),
                "color": color,
                **({"type": "dashed"} if s.get("dashed") else {}),
            },
            "itemStyle": {
                "color": color,
                # 2px surface ring keeps overlapping markers readable.
                "borderColor": SURFACE,
                "borderWidth": 2,
            },
            "emphasis": {"focus": "series"},
            "z": s.get("z", 3),
        }
        if s.get("area"):
            spec["areaStyle"] = {"color": color, "opacity": 0.10}
        if s.get("label_last"):
            spec["endLabel"] = {
                "show": True,
                "color": INK_SECONDARY,
                "fontSize": 11,
                "formatter": "{a}",
            }
        if s.get("stack"):
            spec["stack"] = s["stack"]
        if s.get("line_only_band"):
            spec["lineStyle"]["opacity"] = 0
            spec["showSymbol"] = False
        out.append(spec)

    if zero_line:
        out[0].setdefault("markLine", {
            "silent": True,
            "symbol": "none",
            "data": [{"yAxis": 0}],
            "lineStyle": {"color": BASELINE, "width": 1, "type": "solid"},
            "label": {"show": False},
        })

    opt["series"] = out
    return opt


def band_line(
    categories: list[str],
    *,
    lower: list,
    upper: list,
    actual: list,
    fitted: list,
    actual_name: str = "Published actual",
    fitted_name: str = "Model fit",
    band_name: str = "Approx. 95% residual band",
    value_suffix: str = "%",
    y_name: str = "",
    rotate: int = 0,
) -> dict:
    """Actual vs fitted with a confidence band, drawn as a stacked area.

    Used for the total-loss-frequency nowcast. The band is rendered as an
    invisible baseline plus a translucent fill so it reads as uncertainty rather
    than as a third data series.
    """
    opt = _base_option(legend=True, rotate=rotate)
    opt["tooltip"] = _tooltip(trigger="axis", value_suffix=value_suffix, decimals=1)
    opt["xAxis"] = _category_axis(categories, rotate=rotate)
    opt["xAxis"]["boundaryGap"] = False
    opt["yAxis"] = _value_axis(formatter="{value}" + value_suffix)

    span = [
        (None if (u is None or l is None) else round(u - l, 3))
        for l, u in zip(lower, upper)
    ]

    opt["series"] = [
        {
            "name": band_name + " (baseline)",
            "type": "line",
            "data": lower,
            "stack": "band",
            "lineStyle": {"opacity": 0},
            "showSymbol": False,
            "itemStyle": {"color": "transparent"},
            "areaStyle": {"color": "transparent"},
            "tooltip": {"show": False},
            "silent": True,
            "z": 1,
        },
        {
            "name": band_name,
            "type": "line",
            "data": span,
            "stack": "band",
            "lineStyle": {"opacity": 0},
            "showSymbol": False,
            "itemStyle": {"color": SERIES[0]},
            "areaStyle": {"color": SERIES[0], "opacity": 0.14},
            "silent": True,
            "z": 1,
        },
        {
            "name": fitted_name,
            "type": "line",
            "data": fitted,
            "lineStyle": {"width": 2, "color": INK_MUTED, "type": "dashed"},
            "itemStyle": {"color": INK_MUTED},
            "showSymbol": False,
            "z": 2,
        },
        {
            "name": actual_name,
            "type": "line",
            "data": actual,
            "connectNulls": False,
            "symbol": "circle",
            "symbolSize": 8,
            "showSymbol": True,
            "lineStyle": {"width": 2, "color": SERIES[0]},
            "itemStyle": {"color": SERIES[0], "borderColor": SURFACE, "borderWidth": 2},
            "z": 4,
        },
    ]
    # Legend must not advertise the invisible baseline twice.
    opt["legend"]["data"] = [actual_name, fitted_name, band_name]
    return opt


def scatter(
    points: list[dict],
    *,
    x_name: str = "",
    y_name: str = "",
    x_suffix: str = "",
    y_suffix: str = "",
    diagonal: bool = False,
) -> dict:
    """Labelled scatter. points: [{"name","x","y","color"(opt),"highlight"(opt)}]

    Capped at three colour slots by the all-pairs rule; anything beyond that is
    drawn in muted ink with a direct label, so identity never rests on hue.
    """
    opt = _base_option(legend=False)
    opt["tooltip"] = _tooltip(trigger="item", value_suffix=y_suffix, decimals=1)
    opt["xAxis"] = _value_axis(formatter="{value}" + x_suffix)
    opt["xAxis"]["splitLine"] = {
        "show": True, "lineStyle": {"color": GRIDLINE, "width": 1, "type": "solid"}
    }
    opt["yAxis"] = _value_axis(formatter="{value}" + y_suffix)

    data = []
    for p in points:
        highlight = p.get("highlight", False)
        data.append(
            {
                "name": p["name"],
                "value": [p["x"], p["y"]],
                "itemStyle": {
                    "color": p.get("color") or (SERIES[0] if highlight else INK_MUTED),
                    "borderColor": SURFACE,
                    "borderWidth": 2,
                    "opacity": 1 if highlight else 0.75,
                },
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": p["name"],
                    "color": INK_PRIMARY if highlight else INK_MUTED,
                    "fontSize": 11,
                    "fontWeight": "bold" if highlight else "normal",
                },
                "symbolSize": 15 if highlight else 10,
            }
        )

    series: list[dict] = [{"name": "peers", "type": "scatter", "data": data, "z": 3}]

    if diagonal:
        xs = [p["x"] for p in points]
        ys = [p["y"] for p in points]
        lo = min(min(xs), min(ys))
        hi = max(max(xs), max(ys))
        series.append(
            {
                "name": "parity",
                "type": "line",
                "data": [[lo, lo], [hi, hi]],
                "showSymbol": False,
                "lineStyle": {"color": BASELINE, "width": 1, "type": "solid"},
                "silent": True,
                "tooltip": {"show": False},
                "z": 1,
            }
        )
    opt["series"] = series
    return opt
