// Comportamiento progresivo del Punto de Venta; el backend conserva la autoridad.
document.addEventListener("DOMContentLoaded", () => {
  const paymentMethod = document.querySelector("#medio_pago");
  const cashGroup = document.querySelector("#cash-received-group");
  const cashReceived = document.querySelector("#dinero_recibido");
  const changePreview = document.querySelector("#change-preview");
  const totalElement = document.querySelector("#pos-total");

  const updatePaymentFields = () => {
    if (!paymentMethod || !cashGroup || !cashReceived) return;
    const isCash = paymentMethod.value === "EFECTIVO";
    cashGroup.hidden = !isCash;
    cashReceived.disabled = !isCash;
    cashReceived.required = isCash;
  };

  const updateChangePreview = () => {
    if (!cashReceived || !changePreview || !totalElement) return;
    const total = Number.parseFloat(totalElement.dataset.total || "0");
    const received = Number.parseFloat(cashReceived.value || "0");
    const change = received - total;
    changePreview.textContent = change >= 0
      ? `Vuelto estimado: $ ${change.toFixed(2)}`
      : `Faltan: $ ${Math.abs(change).toFixed(2)}`;
    changePreview.classList.toggle("text-danger", change < 0);
  };

  paymentMethod?.addEventListener("change", updatePaymentFields);
  cashReceived?.addEventListener("input", updateChangePreview);
  updatePaymentFields();
  updateChangePreview();

  document.querySelector("[data-confirm-cart-cancel]")?.addEventListener(
    "submit",
    (event) => {
      if (!window.confirm("¿Querés cancelar y vaciar el carrito?")) {
        event.preventDefault();
      }
    },
  );

  document.querySelector("#pos-checkout-form")?.addEventListener(
    "submit",
    () => {
      const button = document.querySelector("#confirm-sale-button");
      if (button) button.disabled = true;
    },
  );
});
