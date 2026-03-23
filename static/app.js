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
  setMessage("Charts updated.");
}

async function initialize() {
  document.getElementById("start_date").value = "2025-01-01";
  document.getElementById("end_date").value = "2025-12-31";
  document.getElementById("filters").addEventListener("submit", fetchTimeseries);

  try {
    await loadSpecies();
    setMessage("Select filters and click Load Charts.");
  } catch (err) {
    setMessage(err.message || "Initialization error.", true);
  }
}

initialize();
