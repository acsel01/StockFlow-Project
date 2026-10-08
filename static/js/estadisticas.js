document.addEventListener("DOMContentLoaded", () => {
  const dataElement = document.querySelector("#statistics-chart-data");
  if (!dataElement || typeof Chart === "undefined") return;

  const chartData = JSON.parse(dataElement.textContent);

  const renderChart = (canvasId, labels, values, label, color) => {
    const canvas = document.querySelector(`#${canvasId}`);
    if (!canvas) return;
    if (labels.length === 0) {
      const emptyState = document.createElement("p");
      emptyState.className = "text-secondary text-center py-5";
      emptyState.textContent = "Sin datos para el período seleccionado.";
      canvas.replaceWith(emptyState);
      return;
    }
    new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [{ label, data: values, backgroundColor: color }],
      },
      options: {
        responsive: true,
        scales: { y: { beginAtZero: true } },
      },
    });
  };

  renderChart(
    "daily-sales-chart",
    chartData.daily_sales.labels,
    chartData.daily_sales.values,
    "Total vendido",
    "rgba(25, 135, 84, 0.7)",
  );
  renderChart(
    "top-products-chart",
    chartData.top_products.labels,
    chartData.top_products.values,
    "Unidades vendidas",
    "rgba(13, 110, 253, 0.7)",
  );
});
