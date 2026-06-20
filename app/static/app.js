const card = document.querySelector("#health-card");
const label = document.querySelector(".status-label");
const response = document.querySelector("#health-response");
const retryButton = document.querySelector("#retry-button");

async function checkHealth() {
  card.className = "health-card pending";
  label.textContent = "Checking backend";
  response.textContent = "{}";

  try {
    const result = await fetch("/health", {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });

    const body = await result.json();

    if (!result.ok) {
      throw new Error(`HTTP ${result.status}`);
    }

    card.className = "health-card ok";
    label.textContent = "Backend is healthy";
    response.textContent = JSON.stringify(body, null, 2);
  } catch (error) {
    card.className = "health-card error";
    label.textContent = "Backend unavailable. Please retry.";
    response.textContent = JSON.stringify({ error: error.message }, null, 2);
  }
}

retryButton.addEventListener("click", checkHealth);
checkHealth();
