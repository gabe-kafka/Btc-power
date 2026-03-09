const zoneBands = [
  { start: 0, end: 20, color: "#3B82F6" },
  { start: 20, end: 40, color: "#60A5FA" },
  { start: 40, end: 60, color: "#A3A3A3" },
  { start: 60, end: 80, color: "#D97706" },
  { start: 80, end: 100, color: "#DC2626" },
];

const dom = {
  statusLine: document.getElementById("status-line"),
  stamp: document.getElementById("stamp"),
  lede: document.getElementById("lede"),
  metricsBody: document.getElementById("metrics-body"),
  detailBody: document.getElementById("detail-body"),
  gauge: document.getElementById("gauge"),
  priceChart: document.getElementById("price-chart"),
  scoreChart: document.getElementById("score-chart"),
  oneYearNote: document.getElementById("one-year-note"),
  dataNote: document.getElementById("data-note"),
  refreshButton: document.getElementById("refresh-button"),
};

function formatDollar(value) {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}k`;
  return `$${Math.round(value).toLocaleString()}`;
}

function formatGap(value) {
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}${value.toFixed(1)}%`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

function setTableRows(tbody, rows) {
  tbody.innerHTML = rows
    .map(
      ([label, value, note]) => `
        <tr>
          <th>${label}</th>
          <td>${value}</td>
          ${note === undefined ? "" : `<td>${note}</td>`}
        </tr>
      `
    )
    .join("");
}

function createSvgNode(tag, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
  return node;
}

function polar(cx, cy, radius, angleDegrees) {
  const radians = ((angleDegrees - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians),
  };
}

function arcPath(cx, cy, radius, startAngle, endAngle) {
  const start = polar(cx, cy, radius, endAngle);
  const end = polar(cx, cy, radius, startAngle);
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1;
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

function renderGauge(snapshot) {
  const svg = dom.gauge;
  svg.innerHTML = "";
  const width = 480;
  const height = 300;
  const cx = 240;
  const cy = 244;
  const radius = 148;

  zoneBands.forEach((band) => {
    const start = 180 - band.end * 1.8;
    const end = 180 - band.start * 1.8;
    svg.appendChild(
      createSvgNode("path", {
        d: arcPath(cx, cy, radius, start, end),
        stroke: band.color,
        "stroke-width": 30,
        fill: "none",
      })
    );
  });

  [0, 20, 40, 60, 80, 100].forEach((tick) => {
    const point = polar(cx, cy, radius + 26, 180 - tick * 1.8);
    const label = createSvgNode("text", {
      x: point.x,
      y: point.y,
      "text-anchor": "middle",
      "dominant-baseline": "middle",
      fill: "#808080",
      "font-family": "monospace",
      "font-size": 11,
    });
    label.textContent = String(tick);
    svg.appendChild(label);
  });

  const needlePoint = polar(cx, cy, 112, 180 - snapshot.heat_score * 1.8);
  svg.appendChild(
    createSvgNode("line", {
      x1: cx,
      y1: cy,
      x2: needlePoint.x,
      y2: needlePoint.y,
      stroke: "#E5E5E5",
      "stroke-width": 3,
    })
  );
  svg.appendChild(createSvgNode("circle", { cx, cy, r: 8, fill: "#E5E5E5" }));

  const heatValue = createSvgNode("text", {
    x: cx,
    y: 128,
    "text-anchor": "middle",
    fill: snapshot.zone.color,
    "font-family": "monospace",
    "font-size": 42,
    "font-weight": "700",
  });
  heatValue.textContent = Math.round(snapshot.heat_score);
  svg.appendChild(heatValue);

  const zoneLabel = createSvgNode("text", {
    x: cx,
    y: 160,
    "text-anchor": "middle",
    fill: "#E5E5E5",
    "font-family": "monospace",
    "font-size": 18,
    "font-weight": "700",
  });
  zoneLabel.textContent = snapshot.zone.label.toUpperCase();
  svg.appendChild(zoneLabel);

  const caption = createSvgNode("text", {
    x: cx,
    y: 184,
    "text-anchor": "middle",
    fill: "#808080",
    "font-family": "monospace",
    "font-size": 12,
  });
  caption.textContent = snapshot.relative_sentence;
  svg.appendChild(caption);

  const fairValue = createSvgNode("text", {
    x: cx,
    y: 208,
    "text-anchor": "middle",
    fill: "#808080",
    "font-family": "monospace",
    "font-size": 12,
  });
  fairValue.textContent = `MODEL VALUE TODAY ${formatDollar(snapshot.curve_price)}`;
  svg.appendChild(fairValue);
}

function polylinePoints(xValues, yValues, xMap, yMap) {
  return xValues.map((x, index) => `${xMap(x)},${yMap(yValues[index])}`).join(" ");
}

function renderPriceChart(payload) {
  const svg = dom.priceChart;
  svg.innerHTML = "";

  const width = 1200;
  const height = 440;
  const margin = { top: 24, right: 24, bottom: 40, left: 88 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const historyDates = payload.history.dates.map((value) => new Date(value).getTime());
  const historyPrices = payload.history.prices;
  const curveDates = payload.curve.dates.map((value) => new Date(value).getTime());
  const curvePrices = payload.curve.prices;
  const currentX = new Date(payload.snapshot.as_of).getTime();
  const allDates = historyDates.concat(curveDates, currentX);
  const minX = Math.min(...allDates);
  const maxX = Math.max(...allDates);
  const maxY = Math.max(payload.snapshot.current_price * 1.55, ...historyPrices, ...curvePrices);
  const minY = 0.08;
  const yTicks = [0.1, 1, 10, 100, 1000, 10000, 100000];

  const xMap = (value) => margin.left + ((value - minX) / (maxX - minX)) * plotWidth;
  const yMap = (value) => {
    const minLog = Math.log10(minY);
    const maxLog = Math.log10(maxY);
    return margin.top + (1 - (Math.log10(value) - minLog) / (maxLog - minLog)) * plotHeight;
  };

  const years = [];
  const startYear = new Date(minX).getUTCFullYear();
  const endYear = new Date(maxX).getUTCFullYear();
  for (let year = startYear; year <= endYear; year += 2) years.push(year);

  yTicks
    .filter((tick) => tick <= maxY)
    .forEach((tick) => {
      const y = yMap(tick);
      svg.appendChild(createSvgNode("line", { x1: margin.left, y1: y, x2: width - margin.right, y2: y, stroke: "#2A2A2A" }));
      const label = createSvgNode("text", {
        x: margin.left - 12,
        y: y + 4,
        "text-anchor": "end",
        fill: "#808080",
        "font-family": "monospace",
        "font-size": 11,
      });
      label.textContent = formatDollar(tick);
      svg.appendChild(label);
    });

  years.forEach((year) => {
    const x = xMap(Date.UTC(year, 0, 1));
    svg.appendChild(createSvgNode("line", { x1: x, y1: margin.top, x2: x, y2: height - margin.bottom, stroke: "#2A2A2A" }));
    const label = createSvgNode("text", {
      x,
      y: height - 16,
      "text-anchor": "middle",
      fill: "#808080",
      "font-family": "monospace",
      "font-size": 11,
    });
    label.textContent = String(year);
    svg.appendChild(label);
  });

  svg.appendChild(
    createSvgNode("polyline", {
      points: polylinePoints(curveDates, curvePrices, xMap, yMap),
      fill: "none",
      stroke: "#3B82F6",
      "stroke-width": 2,
      "stroke-dasharray": "4 4",
    })
  );

  svg.appendChild(
    createSvgNode("polyline", {
      points: polylinePoints(historyDates, historyPrices, xMap, yMap),
      fill: "none",
      stroke: "#E5E5E5",
      "stroke-width": 1.6,
    })
  );

  svg.appendChild(
    createSvgNode("circle", {
      cx: xMap(currentX),
      cy: yMap(payload.snapshot.current_price),
      r: 5,
      fill: payload.snapshot.zone.color,
    })
  );

  const title = createSvgNode("text", {
    x: margin.left,
    y: 16,
    fill: "#E5E5E5",
    "font-family": "monospace",
    "font-size": 12,
  });
  title.textContent = "BTC PRICE VS POWER CURVE";
  svg.appendChild(title);
}

function renderScoreChart(payload) {
  const svg = dom.scoreChart;
  svg.innerHTML = "";

  const width = 1200;
  const height = 320;
  const margin = { top: 24, right: 24, bottom: 40, left: 88 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const historyDates = payload.history.dates.map((value) => new Date(value).getTime());
  const historyScores = payload.history.scores;
  const currentX = new Date(payload.snapshot.as_of).getTime();
  const minX = Math.min(...historyDates);
  const maxX = Math.max(currentX, ...historyDates);
  const xMap = (value) => margin.left + ((value - minX) / (maxX - minX)) * plotWidth;
  const yMap = (value) => margin.top + (1 - value / 100) * plotHeight;

  zoneBands.forEach((band) => {
    svg.appendChild(
      createSvgNode("rect", {
        x: margin.left,
        y: yMap(band.end),
        width: plotWidth,
        height: yMap(band.start) - yMap(band.end),
        fill: band.color,
        opacity: 0.12,
      })
    );
  });

  [0, 20, 40, 60, 80, 100].forEach((tick) => {
    const y = yMap(tick);
    svg.appendChild(createSvgNode("line", { x1: margin.left, y1: y, x2: width - margin.right, y2: y, stroke: "#2A2A2A" }));
    const label = createSvgNode("text", {
      x: margin.left - 12,
      y: y + 4,
      "text-anchor": "end",
      fill: "#808080",
      "font-family": "monospace",
      "font-size": 11,
    });
    label.textContent = String(tick);
    svg.appendChild(label);
  });

  const years = [];
  const startYear = new Date(minX).getUTCFullYear();
  const endYear = new Date(maxX).getUTCFullYear();
  for (let year = startYear; year <= endYear; year += 2) years.push(year);
  years.forEach((year) => {
    const x = xMap(Date.UTC(year, 0, 1));
    svg.appendChild(createSvgNode("line", { x1: x, y1: margin.top, x2: x, y2: height - margin.bottom, stroke: "#2A2A2A" }));
    const label = createSvgNode("text", {
      x,
      y: height - 16,
      "text-anchor": "middle",
      fill: "#808080",
      "font-family": "monospace",
      "font-size": 11,
    });
    label.textContent = String(year);
    svg.appendChild(label);
  });

  svg.appendChild(
    createSvgNode("polyline", {
      points: polylinePoints(historyDates, historyScores, xMap, yMap),
      fill: "none",
      stroke: "#E5E5E5",
      "stroke-width": 1.6,
    })
  );

  svg.appendChild(
    createSvgNode("circle", {
      cx: xMap(currentX),
      cy: yMap(payload.snapshot.heat_score),
      r: 5,
      fill: payload.snapshot.zone.color,
    })
  );

  const title = createSvgNode("text", {
    x: margin.left,
    y: 16,
    fill: "#E5E5E5",
    "font-family": "monospace",
    "font-size": 12,
  });
  title.textContent = "HISTORICAL HEAT SCORE";
  svg.appendChild(title);
}

function render(payload) {
  const snapshot = payload.snapshot;
  dom.statusLine.innerHTML = `STATUS: <span style="color:${snapshot.zone.color}">${snapshot.zone.label.toUpperCase()}</span> | HEAT ${Math.round(snapshot.heat_score)}/100 | GAP ${formatGap(snapshot.gap_pct)}`;
  dom.stamp.textContent = `UPDATED ${formatDate(snapshot.as_of)}`;
  dom.lede.textContent = `${snapshot.zone.summary} ${snapshot.relative_sentence} ${snapshot.zone.detail}`;

  setTableRows(dom.metricsBody, [
    ["SPOT PRICE", formatDollar(snapshot.current_price), "Live BTC/USD when available."],
    ["MODEL FAIR VALUE", formatDollar(snapshot.curve_price), "Power-curve value for the current date."],
    ["POWER CURVE +1Y", formatDollar(snapshot.curve_price_1y), "Same model carried forward one calendar year."],
    ["PREMIUM / DISCOUNT", formatGap(snapshot.gap_pct), "Distance from model fair value."],
    ["YEARS AHEAD", snapshot.years_ahead_value.toFixed(2), "How far ahead of the curve price is trading."],
    ["HEAT SCORE", `${Math.round(snapshot.heat_score)}/100`, "Historical percentile of BTC's deviation from the curve."],
  ]);

  setTableRows(dom.detailBody, [
    ["SUMMARY", snapshot.zone.summary],
    ["HISTORICAL POSITION", `${snapshot.relative_sentence} ${snapshot.years_ahead_value.toFixed(2)} years ahead of the curve.`],
    ["FAIR VALUE ASSUMPTION", `The model treats the power-curve price as fair value: ${formatDollar(snapshot.curve_price)} today and ${formatDollar(snapshot.curve_price_1y)} one year out.`],
    ["DATA SOURCE", snapshot.source_note],
  ]);

  dom.oneYearNote.textContent = `Following the power curve one year out implies ${formatDollar(snapshot.curve_price_1y)}.`;
  dom.dataNote.textContent = snapshot.source_note;

  renderGauge(snapshot);
  renderPriceChart(payload);
  renderScoreChart(payload);
}

async function loadSnapshot(forceRefresh = false) {
  dom.refreshButton.disabled = true;
  dom.refreshButton.textContent = "LOADING";
  try {
    const query = forceRefresh ? "?refresh=1" : "";
    const response = await fetch(`/api/snapshot${query}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`API ${response.status}`);
    const payload = await response.json();
    render(payload);
  } catch (error) {
    dom.statusLine.textContent = "STATUS: API ERROR";
    dom.lede.textContent = "Failed to load the market snapshot from /api/snapshot.";
    console.error(error);
  } finally {
    dom.refreshButton.disabled = false;
    dom.refreshButton.textContent = "REFRESH DATA";
  }
}

dom.refreshButton.addEventListener("click", () => loadSnapshot(true));
window.addEventListener("load", () => loadSnapshot(false));
