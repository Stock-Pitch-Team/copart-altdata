/* ==========================================================================
   Chart runtime.

   Chart options arrive from the Python build as JSON with colour ROLE TOKENS
   like "@series-1" rather than hex. This file resolves those tokens from CSS
   custom properties at render time, which is what lets light and dark mode swap
   without rebuilding any data. On a theme change every chart is re-rendered
   against the new mode's values rather than being tinted.
   ========================================================================== */
(function () {
  "use strict";

  var charts = [];

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  /* Deep-walk an option object replacing "@token" with the resolved colour and
     expanding the few function placeholders the builder emits. */
  function resolve(node) {
    if (typeof node === "string") {
      return node.charAt(0) === "@" ? cssVar("--" + node.slice(1)) || node : node;
    }
    if (Array.isArray(node)) return node.map(resolve);
    if (node && typeof node === "object") {
      if (node.__fn === "signColor") {
        var pos = resolve(node.positive);
        var neg = resolve(node.negative);
        return function (params) {
          return params.value < 0 ? neg : pos;
        };
      }
      var out = {};
      for (var k in node) {
        if (Object.prototype.hasOwnProperty.call(node, k)) out[k] = resolve(node[k]);
      }
      return out;
    }
    return node;
  }

  function fmt(value, decimals, suffix) {
    if (value === null || value === undefined || value === "") return "n/a";
    var n = Number(value);
    if (isNaN(n)) return String(value);
    return n.toFixed(decimals) + (suffix || "");
  }

  /* Shared tooltip: one row per series, a colour dot for identity, values in
     ink rather than in the series colour. */
  function tooltipFormatter(decimals, suffix) {
    return function (params) {
      var rows = Array.isArray(params) ? params : [params];
      if (!rows.length) return "";
      var head = rows[0].axisValueLabel || rows[0].name || "";
      var html =
        '<div style="font-weight:650;margin-bottom:5px;font-size:11.5px">' +
        head +
        "</div>";
      var seen = {};
      rows.forEach(function (r) {
        if (r.seriesName && seen[r.seriesName]) return;
        if (r.seriesName) seen[r.seriesName] = true;
        var v = Array.isArray(r.value) ? r.value[r.value.length - 1] : r.value;
        if (v === null || v === undefined) return;
        html +=
          '<div style="display:flex;align-items:center;gap:7px;margin:2px 0">' +
          '<span style="width:9px;height:9px;border-radius:3px;background:' +
          (r.color || "transparent") +
          ';display:inline-block;flex:none"></span>' +
          '<span style="flex:1;padding-right:14px">' +
          (r.seriesName || "") +
          "</span>" +
          '<span style="font-variant-numeric:tabular-nums;font-weight:600">' +
          fmt(v, decimals, suffix) +
          "</span></div>";
      });
      return html;
    };
  }

  function build(el, rawOption) {
    var option = resolve(rawOption);
    var decimals =
      (rawOption.tooltip && rawOption.tooltip.valueDecimals !== undefined)
        ? rawOption.tooltip.valueDecimals
        : 1;
    var suffix =
      (rawOption.tooltip && rawOption.tooltip.valueSuffix) || "";
    if (option.tooltip) {
      option.tooltip.formatter = tooltipFormatter(decimals, suffix);
      // Enlarge the hover target so users are not chasing an 8px dot.
      option.tooltip.enterable = false;
      option.tooltip.confine = true;
    }
    var inst = echarts.init(el, null, { renderer: "svg" });
    inst.setOption(option);
    return inst;
  }

  function renderAll() {
    charts.forEach(function (c) {
      c.inst.dispose();
      c.inst = build(c.el, c.raw);
    });
  }

  /* ------------------------------------------------- chart library loading */
  /* Tried in order. Both were verified to serve a 200 with a JavaScript MIME
     type; if one goes away the next is used, and if all fail the site falls
     back to table views rather than showing empty boxes. */
  var CDNS = [
    "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/echarts/6.1.0/echarts.min.js"
  ];

  function loadLib(i, done) {
    if (typeof echarts !== "undefined") return done(true);
    if (i >= CDNS.length) return done(false);
    var s = document.createElement("script");
    s.src = CDNS[i];
    s.async = false;
    s.crossOrigin = "anonymous";
    s.referrerPolicy = "no-referrer";
    s.onload = function () {
      if (typeof echarts !== "undefined") done(true);
      else loadLib(i + 1, done);
    };
    s.onerror = function () {
      loadLib(i + 1, done);
    };
    document.head.appendChild(s);
  }

  function tablesOnly() {
    document.querySelectorAll(".chart").forEach(function (el) {
      el.innerHTML =
        '<p style="color:var(--text-muted);font-size:12.5px;padding:12px 0">' +
        "The chart library could not be loaded, so these figures are shown as a table." +
        "</p>";
    });
    document.querySelectorAll(".card[data-view]").forEach(function (card) {
      card.setAttribute("data-view", "table");
      card.querySelectorAll("[data-view-btn]").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.getAttribute("data-view-btn") === "table"));
      });
    });
  }

  function initCharts() {
    document.querySelectorAll("script[data-chart]").forEach(function (tag) {
      var el = document.getElementById(tag.getAttribute("data-chart"));
      if (!el) return;
      var raw;
      try {
        raw = JSON.parse(tag.textContent);
      } catch (e) {
        return;
      }
      charts.push({ el: el, raw: raw, inst: build(el, raw) });
    });

    window.addEventListener("resize", function () {
      charts.forEach(function (c) {
        c.inst.resize();
      });
    });
  }

  /* ----------------------------------------------------------- view toggle */
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-view-btn]");
    if (!btn) return;
    var card = btn.closest(".card");
    if (!card) return;
    var mode = btn.getAttribute("data-view-btn");
    card.setAttribute("data-view", mode);
    card.querySelectorAll("[data-view-btn]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b === btn));
    });
    if (mode === "chart") {
      charts.forEach(function (c) {
        if (card.contains(c.el)) c.inst.resize();
      });
    }
  });

  /* ---------------------------------------------------------- theme toggle */
  function currentTheme() {
    var stamped = document.documentElement.getAttribute("data-theme");
    if (stamped) return stamped;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("cprt-theme", theme);
    } catch (e) {
      /* private mode: the toggle still works for this page view */
    }
    var btn = document.querySelector(".theme-toggle");
    if (btn) {
      btn.textContent = theme === "dark" ? "☀" : "☽";
      btn.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
      );
    }
    renderAll();
  }

  document.addEventListener("click", function (e) {
    if (!e.target.closest(".theme-toggle")) return;
    applyTheme(currentTheme() === "dark" ? "light" : "dark");
  });

  /* Restore the saved theme before first paint of the charts. */
  try {
    var saved = localStorage.getItem("cprt-theme");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  } catch (e) {
    /* ignore */
  }

  function boot() {
    var btn = document.querySelector(".theme-toggle");
    if (btn) btn.textContent = currentTheme() === "dark" ? "☀" : "☽";
    loadLib(0, function (ok) {
      if (ok) initCharts();
      else tablesOnly();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
