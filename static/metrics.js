let lotValueChart;
let priceDistributionChart;
let lotSizeChart;
let volatilityChart;
let gearChart;
let gearValueChart;

const SMOOTHING_WINDOW = 21;

function movingAverage(values, windowSize) {
  const result = [];
  const safeWindow = Math.max(1, windowSize);

  for (let i = 0; i < values.length; i += 1) {
    const start = Math.max(0, i - safeWindow + 1);
    const slice = values.slice(start, i + 1);
    const valid = slice.filter((value) => Number.isFinite(value));
    if (valid.length === 0) {
      result.push(null);
      continue;
    }
    const sum = valid.reduce((acc, value) => acc + value, 0);
    result.push(sum / valid.length);
  }

  return result;
}

function setMessage(text, isError = false) {
  const messageEl = document.getElementById("message");
  messageEl.textContent = text || "";
  messageEl.className = "message" + (isError ? " error" : " success");
}

function toISODateInput(daysDelta = 0) {
  const now = new Date();
  now.setDate(now.getDate() + daysDelta);
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDate(d) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getPresetRange(presetId) {
  const today = new Date();
  let start;
  let end;

  switch (presetId) {
    case "last_week": {
      const startDate = new Date(today);
      startDate.setDate(startDate.getDate() - 7);
      start = formatDate(startDate);
      end = formatDate(today);
      break;
    }
    case "last_month": {
      const prevMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      start = formatDate(prevMonth);
      const lastDay = new Date(today.getFullYear(), today.getMonth(), 0);
      end = formatDate(lastDay);
      break;
    }
    case "last_3_months": {
      const startDate = new Date(today);
      startDate.setMonth(startDate.getMonth() - 3);
      start = formatDate(startDate);
      end = formatDate(today);
      break;
    }
    case "this_month": {
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
      start = formatDate(firstDay);
      end = formatDate(today);
      break;
    }
    case "last_year": {
      const prevYear = today.getFullYear() - 1;
      start = `${prevYear}-01-01`;
      end = `${prevYear}-12-31`;
      break;
    }
    case "last_12_months": {
      const startDate = new Date(today);
      startDate.setDate(startDate.getDate() - 365);
      start = formatDate(startDate);
      end = formatDate(today);
      break;
    }
    case "year_to_date": {
      start = `${today.getFullYear()}-01-01`;
      end = formatDate(today);
      break;
    }
    default:
      return null;
  }

  return { start, end };
}

function applyPreset(presetId) {
  const range = getPresetRange(presetId);
  if (!range) return;
  document.getElementById("start_date").value = range.start;
  document.getElementById("end_date").value = range.end;
}

async function loadSpecies() {
  const speciesEl = document.getElementById("species");
  speciesEl.innerHTML = "<option value=''>Select species</option>";

  const response = await fetch("/api/species");
  if (!response.ok) {
    throw new Error("Unable to load species list.");
  }

  const speciesList = await response.json();
  speciesList.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    speciesEl.appendChild(option);
  });
}

function destroyCharts() {
  [lotValueChart, priceDistributionChart, lotSizeChart, volatilityChart, gearChart, gearValueChart].forEach(
    (ch) => {
      if (ch) ch.destroy();
    }
  );
}

function renderSummary(payload) {
  const s = payload.summary;
  const section = document.getElementById("summarySection");
  section.style.display = "flex";
  section.innerHTML = "";

  const cards = [
    { label: "Total Lots", value: s.total_lots.toLocaleString() },
    { label: "Total Tonnage (kg)", value: s.total_tonnage.toLocaleString() },
    { label: "Total Value", value: "£" + s.total_value.toLocaleString() },
    { label: "Avg Price/KG", value: "£" + s.overall_avg_price_per_kg.toFixed(2) },
  ];

  if (payload.wow_change_pct != null) {
    cards.push({
      label: "WoW Value Change",
      value: (payload.wow_change_pct >= 0 ? "+" : "") + payload.wow_change_pct + "%",
    });
  }
  if (payload.mom_change_pct != null) {
    cards.push({
      label: "MoM Value Change",
      value: (payload.mom_change_pct >= 0 ? "+" : "") + payload.mom_change_pct + "%",
    });
  }
  if (payload.price_tonnage_correlation != null) {
    cards.push({
      label: "Price-Tonnage Correlation",
      value: payload.price_tonnage_correlation.toFixed(2),
    });
  }

  cards.forEach((c) => {
    const div = document.createElement("div");
    div.className = "summary-card";
    div.innerHTML = `<div class="label">${c.label}</div><div class="value">${c.value}</div>`;
    section.appendChild(div);
  });
}

function renderLotValueChart(labels, lotCounts, totalValues) {
  const smoothedLots = movingAverage(lotCounts, SMOOTHING_WINDOW);
  const smoothedValues = movingAverage(totalValues, SMOOTHING_WINDOW);
  const ctx = document.getElementById("lotValueChart");
  lotValueChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Lot Count (21-day avg)",
          data: smoothedLots,
          borderColor: "#0b84f3",
          backgroundColor: "rgba(11, 132, 243, 0.1)",
          borderWidth: 2,
          tension: 0.35,
          yAxisID: "yLots",
        },
        {
          label: "Total Value (£) (21-day avg)",
          data: smoothedValues,
          borderColor: "#34a853",
          backgroundColor: "rgba(52, 168, 83, 0.1)",
          borderWidth: 2,
          tension: 0.35,
          yAxisID: "yValue",
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true } },
      scales: {
        x: {
          ticks: {
            callback: function (_, idx) {
              const raw = this.getLabelForValue(idx);
              const d = new Date(raw);
              return isNaN(d.getTime()) ? raw : d.toLocaleDateString("en-GB", { month: "short", day: "numeric" });
            },
          },
        },
        yLots: { type: "linear", position: "left", title: { display: true, text: "Lot Count" } },
        yValue: {
          type: "linear",
          position: "right",
          title: { display: true, text: "Total Value (£)" },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

function renderPriceDistributionChart(labels, minPrices, maxPrices, medians, avgs) {
  const smoothedMin = movingAverage(minPrices, SMOOTHING_WINDOW);
  const smoothedMax = movingAverage(maxPrices, SMOOTHING_WINDOW);
  const smoothedMedian = movingAverage(medians, SMOOTHING_WINDOW);
  const smoothedAvg = movingAverage(avgs, SMOOTHING_WINDOW);
  const ctx = document.getElementById("priceDistributionChart");
  priceDistributionChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Min Price/KG (21-day avg)", data: smoothedMin, borderColor: "#ea4335", borderWidth: 1.5, tension: 0.35, fill: false },
        { label: "Max Price/KG (21-day avg)", data: smoothedMax, borderColor: "#4285f4", borderWidth: 1.5, tension: 0.35, fill: false },
        { label: "Median Price/KG (21-day avg)", data: smoothedMedian, borderColor: "#fbbc04", borderWidth: 2, tension: 0.35, fill: false },
        { label: "Avg Price/KG (21-day avg)", data: smoothedAvg, borderColor: "#34a853", borderWidth: 2, tension: 0.35, fill: false, borderDash: [4, 2] },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true } },
      scales: {
        x: {
          ticks: {
            callback: function (_, idx) {
              const raw = this.getLabelForValue(idx);
              const d = new Date(raw);
              return isNaN(d.getTime()) ? raw : d.toLocaleDateString("en-GB", { month: "short" });
            },
          },
        },
        y: { title: { display: true, text: "Price/KG (£)" } },
      },
    },
  });
}

function renderLotSizeChart(labels, avgLotSizes) {
  const smoothed = movingAverage(avgLotSizes, SMOOTHING_WINDOW);
  const ctx = document.getElementById("lotSizeChart");
  lotSizeChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Avg Lot Size (kg) (21-day avg)",
          data: smoothed,
          borderColor: "#4285f4",
          backgroundColor: "rgba(66, 133, 244, 0.1)",
          borderWidth: 2,
          tension: 0.35,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true } },
      scales: {
        x: {
          ticks: {
            callback: function (_, idx) {
              const raw = this.getLabelForValue(idx);
              const d = new Date(raw);
              return isNaN(d.getTime()) ? raw : d.toLocaleDateString("en-GB", { month: "short" });
            },
          },
        },
        y: { title: { display: true, text: "Avg Lot Size (kg)" }, beginAtZero: true },
      },
    },
  });
}

function renderVolatilityChart(labels, stdDevs, cvs) {
  const smoothedStd = movingAverage(stdDevs, SMOOTHING_WINDOW);
  const smoothedCV = movingAverage(cvs, SMOOTHING_WINDOW);
  const ctx = document.getElementById("volatilityChart");
  volatilityChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Price Std Dev (21-day avg)", data: smoothedStd, borderColor: "#9c27b0", borderWidth: 2, tension: 0.35, yAxisID: "yStd" },
        { label: "Coefficient of Variation % (21-day avg)", data: smoothedCV, borderColor: "#ff9800", borderWidth: 2, tension: 0.35, yAxisID: "yCV" },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true } },
      scales: {
        x: {
          ticks: {
            callback: function (_, idx) {
              const raw = this.getLabelForValue(idx);
              const d = new Date(raw);
              return isNaN(d.getTime()) ? raw : d.toLocaleDateString("en-GB", { month: "short" });
            },
          },
        },
        yStd: { type: "linear", position: "left", title: { display: true, text: "Std Dev (£/kg)" } },
        yCV: {
          type: "linear",
          position: "right",
          title: { display: true, text: "CV (%)" },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

function renderGearCharts(gearBreakdown) {
  const gears = gearBreakdown.map((g) => g.gear);
  const tonnages = gearBreakdown.map((g) => g.tonnage);
  const values = gearBreakdown.map((g) => g.total_value);

  const colors = [
    "#4285f4", "#ea4335", "#fbbc04", "#34a853", "#9c27b0",
    "#00acc1", "#ff9800", "#795548",
  ];

  gearChart = new Chart(document.getElementById("gearChart"), {
    type: "doughnut",
    data: {
      labels: gears,
      datasets: [{ data: tonnages, backgroundColor: colors.slice(0, gears.length), borderWidth: 1 }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "right" },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const pct = gearBreakdown[ctx.dataIndex].share_of_tonnage_pct;
              return ` ${ctx.label}: ${ctx.raw} kg (${pct}%)`;
            },
          },
        },
      },
    },
  });

  const totalValue = values.reduce((a, b) => a + b, 0);
  gearValueChart = new Chart(document.getElementById("gearValueChart"), {
    type: "bar",
    data: {
      labels: gears,
      datasets: [
        {
          label: "Total Value (£)",
          data: values,
          backgroundColor: colors.slice(0, gears.length).map((c) => c + "99"),
          borderColor: colors.slice(0, gears.length),
          borderWidth: 1,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => {
              const v = values[ctx.dataIndex];
              const pct = totalValue ? ((v / totalValue) * 100).toFixed(1) : 0;
              return ` ${pct}% of total value`;
            },
          },
        },
      },
      scales: {
        x: { beginAtZero: true, title: { display: true, text: "Total Value (£)" } },
      },
    },
  });
}

function renderAllCharts(payload) {
  destroyCharts();

  const daily = payload.daily;
  if (!daily || daily.length === 0) return;

  const labels = daily.map((d) => d.date);

  renderLotValueChart(
    labels,
    daily.map((d) => d.lot_count),
    daily.map((d) => d.total_value),
  );

  renderPriceDistributionChart(
    labels,
    daily.map((d) => d.min_price_per_kg),
    daily.map((d) => d.max_price_per_kg),
    daily.map((d) => d.median_price_per_kg),
    daily.map((d) => d.avg_price_per_kg),
  );

  renderLotSizeChart(
    labels,
    daily.map((d) => d.avg_lot_size),
  );

  renderVolatilityChart(
    labels,
    daily.map((d) => d.price_std_dev),
    daily.map((d) => d.coefficient_of_variation_pct),
  );

  if (payload.gear_breakdown && payload.gear_breakdown.length > 0) {
    document.getElementById("gearSection").style.display = "block";
    document.getElementById("gearValueSection").style.display = "block";
    renderGearCharts(payload.gear_breakdown);
  } else {
    document.getElementById("gearSection").style.display = "none";
    document.getElementById("gearValueSection").style.display = "none";
  }
}

async function fetchMetrics(event) {
  event.preventDefault();
  setMessage("");

  const species = document.getElementById("species").value;
  const startDate = document.getElementById("start_date").value;
  const endDate = document.getElementById("end_date").value;

  if (!species || !startDate || !endDate) {
    setMessage("Please select species and both dates.", true);
    return;
  }
  if (startDate > endDate) {
    setMessage("Start date must be before or equal to end date.", true);
    return;
  }

  const params = new URLSearchParams({
    species,
    start_date: startDate,
    end_date: endDate,
  });

  const response = await fetch(`/api/metrics?${params.toString()}`);
  const payload = await response.json();

  if (!response.ok) {
    setMessage(payload.error || "Failed to load metrics.", true);
    return;
  }

  if (!payload.daily || payload.daily.length === 0) {
    destroyCharts();
    document.getElementById("summarySection").style.display = "none";
    document.getElementById("chartsSection").style.display = "none";
    setMessage("No data found for selected filters.");
    return;
  }

  renderSummary(payload);
  renderAllCharts(payload);
  document.getElementById("chartsSection").style.display = "block";
  setMessage("Metrics updated.");
}

async function initialize() {
  document.getElementById("start_date").value = "2025-01-01";
  document.getElementById("end_date").value = "2025-12-31";
  document.getElementById("filters").addEventListener("submit", fetchMetrics);
  document.getElementById("filters").addEventListener("click", (e) => {
    const btn = e.target.closest(".preset-btn");
    if (btn && btn.dataset.preset) {
      applyPreset(btn.dataset.preset);
    }
  });

  try {
    await loadSpecies();
    setMessage("Select filters and click Load Metrics.");
  } catch (err) {
    setMessage(err.message || "Initialization error.", true);
  }
}

initialize();
