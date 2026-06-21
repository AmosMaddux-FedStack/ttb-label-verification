const form = document.querySelector("#verify-form");
const submitButton = document.querySelector("#submit-button");
const resetButton = document.querySelector("#reset-button");
const message = document.querySelector("#message");
const resultPanel = document.querySelector("#result-panel");
const extractedList = document.querySelector("#extracted-list");
const verdictBadge = document.querySelector("#verdict-badge");
const latency = document.querySelector("#latency");
const healthBadge = document.querySelector("#health-badge");
const imageInput = document.querySelector("#image");
const fileName = document.querySelector("#file-name");
const imagePreview = document.querySelector("#image-preview");
const formStatus = document.querySelector("#form-status");
const countrySelect = document.querySelector("#country");
const countryOther = document.querySelector("#country-other");
const inlineResults = document.querySelectorAll("[data-result-for]");

const fieldLabels = {
  brand_name: "Brand name",
  product_class: "Product type",
  producer: "Producer or company",
  country_of_origin: "Country",
  abv: "Alcohol percentage",
  net_contents: "Bottle size",
  government_warning: "Government warning",
};

function setMessage(text, type = "info") {
  message.hidden = !text;
  message.textContent = text || "";
  message.className = `message ${type}`;
}

async function checkHealth() {
  try {
    const response = await fetch("/health", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Backend unavailable");
    }
    healthBadge.textContent = "Backend ready";
    healthBadge.className = "health-badge ok";
  } catch {
    healthBadge.textContent = "Backend unavailable";
    healthBadge.className = "health-badge error";
  }
}

function valueOrDash(value) {
  return value === null || value === undefined || value === "" ? "Not found on label" : value;
}

function clearInlineResults() {
  inlineResults.forEach((item) => {
    item.className = "inline-result pending";
    item.querySelector(".result-status").textContent = "Not checked";
    item.querySelector(".result-value").textContent = "Found on label will appear here.";
    item.querySelector(".result-message").textContent = "";
  });
}

function renderFields(fields) {
  clearInlineResults();

  fields.forEach((field) => {
    const item = document.querySelector(`[data-result-for="${field.field}"]`);
    if (!item) {
      return;
    }
    const approved = field.status === "PASS";
    item.className = `inline-result ${approved ? "approved" : "review"}`;
    item.querySelector(".result-status").textContent = approved ? "Looks good" : "Needs review";
    item.querySelector(".result-value").textContent = valueOrDash(field.extracted_value);
    item.querySelector(".result-message").textContent = field.message || "";
  });
}

function renderExtracted(extracted) {
  extractedList.innerHTML = "";

  Object.entries(fieldLabels).forEach(([key, label]) => {
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = label;
    detail.textContent = valueOrDash(extracted[key]);
    extractedList.append(term, detail);
  });
}

function renderResult(body) {
  resultPanel.hidden = false;
  const verdict = body.verification.verdict;
  verdictBadge.textContent = verdict === "PASS" ? "APPROVED" : "NEEDS REVIEW";
  verdictBadge.className = `verdict-badge ${verdict === "PASS" ? "pass" : "review"}`;
  latency.textContent = `Checked in ${(body.latency_ms / 1000).toFixed(1)} seconds`;
  renderFields(body.verification.fields);
  renderExtracted(body.extracted_label);
}

function renderErrors(body) {
  const errors = body.errors || {};
  const parts = Object.entries(errors).map(([field, text]) => {
    return plainError(field, text);
  });
  setMessage(parts.length ? parts.join(" ") : body.message || "Request failed.", "error");
  message.focus();
}

function plainError(field, text) {
  const label = fieldLabels[field] || (field === "image" ? "Label photo" : field);
  if (field === "image" && text.includes("Unsupported")) {
    return "Please choose a JPG, PNG, or WebP photo.";
  }
  if (field === "image" && text.includes("larger")) {
    return "The photo is too large. Please choose one under 8 MB.";
  }
  if (field === "image") {
    return "Please choose a label photo.";
  }
  if (text.includes("required") || text.includes("empty")) {
    return `Please fill in ${label}.`;
  }
  return `${label}: ${text}`;
}

async function submitVerification(event) {
  event.preventDefault();
  if (!isFormComplete()) {
    updateSubmitState();
    return;
  }
  setMessage("", "info");
  resultPanel.hidden = true;
  clearInlineResults();
  submitButton.disabled = true;
  submitButton.textContent = "Checking...";
  formStatus.textContent = "Checking the label. This may take a few seconds.";

  try {
    const formData = buildFormData();
    const response = await fetch("/verify", {
      method: "POST",
      body: formData,
    });
    const body = await response.json();

    if (!response.ok) {
      renderErrors(body);
      return;
    }

    renderResult(body);
    setMessage("", "success");
  } catch {
    setMessage("The checking service is unavailable. Please try again.", "error");
    message.focus();
  } finally {
    submitButton.textContent = "Check Label";
    updateSubmitState();
  }
}

function resetForm() {
  form.reset();
  fileName.textContent = "Choose label photo";
  imagePreview.removeAttribute("src");
  imagePreview.classList.remove("visible");
  countryOther.hidden = true;
  countryOther.value = "";
  resultPanel.hidden = true;
  clearInlineResults();
  setMessage("", "info");
  updateSubmitState();
}

function selectedCountryValue() {
  if (countrySelect.value === "__other__") {
    return countryOther.value.trim();
  }
  return countrySelect.value.trim();
}

function buildFormData() {
  const formData = new FormData(form);
  formData.set("country_of_origin", selectedCountryValue());
  const abv = String(formData.get("abv") || "").trim();
  if (abv) {
    formData.set("abv", `${abv}%`);
  }
  return formData;
}

function isFormComplete() {
  const formData = new FormData(form);
  if (!imageInput.files.length) {
    return false;
  }
  return Object.keys(fieldLabels).every((name) => {
    if (name === "country_of_origin") {
      return selectedCountryValue();
    }
    return String(formData.get(name) || "").trim();
  });
}

function updateSubmitState() {
  const complete = isFormComplete();
  submitButton.disabled = !complete;
  formStatus.textContent = complete ? "" : "Add the missing items to check this label.";
}

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (!file) {
    fileName.textContent = "Choose label photo";
    imagePreview.removeAttribute("src");
    imagePreview.classList.remove("visible");
    updateSubmitState();
    return;
  }

  fileName.textContent = file.name;
  imagePreview.src = URL.createObjectURL(file);
  imagePreview.classList.add("visible");
  updateSubmitState();
});

countrySelect.addEventListener("change", () => {
  const showOther = countrySelect.value === "__other__";
  countryOther.hidden = !showOther;
  if (showOther) {
    countryOther.focus();
  } else {
    countryOther.value = "";
  }
  updateSubmitState();
});

form.addEventListener("submit", submitVerification);
form.addEventListener("input", updateSubmitState);
resetButton.addEventListener("click", resetForm);
checkHealth();
clearInlineResults();
updateSubmitState();
