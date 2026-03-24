let combinedChart;
const SMOOTHING_WINDOW = 21;

function setMessage(text, isError = false) {
  const messageEl = document.getElementById("message");
  messageEl.textContent = text || "";
  messageEl.style.color = isError ? "#b00020" : "#1f6f3f";
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
  updatePrintHeading();
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
  if (combinedChart) {
    combinedChart.destroy();
  }
}

function updatePrintHeading() {
  const species = document.getElementById("species").value || "Unknown species";
  const startDate = document.getElementById("start_date").value || "N/A";
  const endDate = document.getElementById("end_date").value || "N/A";
  const heading = document.getElementById("printHeading");
  heading.textContent = `Species: ${species} | Date Range: ${startDate} to ${endDate}`;
}

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

function renderCharts(rows) {
  const labels = rows.map((row) => row.date);
  const avgPriceData = rows.map((row) => row.avg_price_per_kg);
  const tonnageData = rows.map((row) => row.total_tonnage);
  const smoothedPriceData = movingAverage(avgPriceData, SMOOTHING_WINDOW);
  const smoothedTonnageData = movingAverage(tonnageData, SMOOTHING_WINDOW);

  destroyCharts();

  const combinedCtx = document.getElementById("combinedChart");

  combinedChart = new Chart(combinedCtx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Avg Price per KG",
          data: smoothedPriceData,
          borderColor: "#0b84f3",
          backgroundColor: "rgba(11, 132, 243, 0.2)",
          borderWidth: 2,
          tension: 0.35,
          yAxisID: "yPrice"
        },
        {
          label: "Total Tonnage",
          data: smoothedTonnageData,
          borderColor: "#d93025",
          backgroundColor: "rgba(217, 48, 37, 0.2)",
          borderWidth: 2,
          tension: 0.35,
          yAxisID: "yTonnage"
        }
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true } },
      scales: {
        x: {
          ticks: {
            callback: function callback(value, index) {
              const rawLabel = this.getLabelForValue(value) || labels[index];
              const parsed = new Date(rawLabel);
              if (Number.isNaN(parsed.getTime())) {
                return rawLabel;
              }
              return parsed.toLocaleString("en-GB", { month: "short" });
            }
          }
        },
        yPrice: {
          type: "linear",
          position: "left",
          title: {
            display: true,
            text: "Avg Price per KG"
          }
        },
        yTonnage: {
          type: "linear",
          position: "right",
          title: {
            display: true,
            text: "Total Tonnage"
          },
          grid: {
            drawOnChartArea: false
          }
        }
      }
    }
  });
}

async function fetchTimeseries(event) {
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
    end_date: endDate
  });

  const response = await fetch(`/api/timeseries?${params.toString()}`);
  const payload = await response.json();

  if (!response.ok) {
    setMessage(payload.error || "Failed to load chart data.", true);
    return;
  }

  if (!payload.data || payload.data.length === 0) {
    destroyCharts();
    setMessage("No data found for selected filters.");
    return;
  }

  renderCharts(payload.data);
  updatePrintHeading();
  setMessage("Charts updated.");
}

function printChart() {
  if (!combinedChart) {
    setMessage("Load chart data before printing.", true);
    return;
  }
  updatePrintHeading();
  combinedChart.resize();
  window.print();
}

async function initialize() {
  document.getElementById("start_date").value = "2025-01-01";
  document.getElementById("end_date").value = "2025-12-31";
  document.getElementById("filters").addEventListener("submit", fetchTimeseries);
  document.getElementById("printChartButton").addEventListener("click", printChart);
  document.getElementById("filters").addEventListener("click", (e) => {
    const btn = e.target.closest(".preset-btn");
    if (btn && btn.dataset.preset) {
      applyPreset(btn.dataset.preset);
    }
  });

  try {
    await loadSpecies();
    updatePrintHeading();
    setMessage("Select filters and click Load Charts.");
  } catch (err) {
    setMessage(err.message || "Initialization error.", true);
  }
}

initialize();
