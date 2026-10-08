document.addEventListener("DOMContentLoaded", () => {
  const dataElement = document.querySelector("#statistics-chart-data");
  if (!dataElement || typeof Chart === "undefined") return;

  const chartData = JSON.parse(dataElement.textContent);

  const renderChart = (canvasId, labels, values, label, color, borderColor) => {
    const canvas = document.querySelector(`#${canvasId}`);
    if (!canvas) return;
    if (labels.length === 0) {
      const emptyState = document.createElement("p");
      emptyState.className = "sf-empty-state";
      emptyState.textContent = "Sin datos para el período seleccionado.";
      canvas.replaceWith(emptyState);
      return;
    }
    new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label,
            data: values,
            backgroundColor: color,
            borderColor,
            borderWidth: 1,
            borderRadius: 6,
            borderSkipped: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "#cbd5df",
              usePointStyle: true,
              pointStyle: "rectRounded",
            },
          },
          tooltip: {
            backgroundColor: "#061829",
            borderColor: "rgba(142, 160, 181, 0.35)",
            borderWidth: 1,
            titleColor: "#f4f7fa",
            bodyColor: "#cbd5df",
          },
        },
        scales: {
          x: {
            border: { color: "rgba(142, 160, 181, 0.2)" },
            grid: { display: false },
            ticks: { color: "#8ea0b5" },
          },
          y: {
            beginAtZero: true,
            border: { color: "rgba(142, 160, 181, 0.2)" },
            grid: { color: "rgba(142, 160, 181, 0.12)" },
            ticks: { color: "#8ea0b5" },
          },
        },
      },
    });
  };

  renderChart(
    "daily-sales-chart",
    chartData.daily_sales.labels,
    chartData.daily_sales.values,
    "Total vendido",
    "rgba(18, 226, 160, 0.58)",
    "#12e2a0",
  );
  renderChart(
    "top-products-chart",
    chartData.top_products.labels,
    chartData.top_products.values,
    "Unidades vendidas",
    "rgba(78, 164, 255, 0.58)",
    "#4ea4ff",
  );
});
