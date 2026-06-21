const form = document.querySelector("#verify-form");
const submitButton = document.querySelector("#submit-button");
const resetButton = document.querySelector("#reset-button");
const message = document.querySelector("#message");
const resultPanel = document.querySelector("#result-panel");
const fieldResults = document.querySelector("#field-results");
const extractedList = document.querySelector("#extracted-list");
const verdictBadge = document.querySelector("#verdict-badge");
const latency = document.querySelector("#latency");
const healthBadge = document.querySelector("#health-badge");
const imageInput = document.querySelector("#image");
const fileName = document.querySelector("#file-name");
const imagePreview = document.querySelector("#image-preview");
const formStatus = document.querySelector("#form-status");

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
  return value === null || value === undefined || value === "" ? "Not found" : value;
}

function renderFields(fields) {
  fieldResults.innerHTML = "";

  const sortedFields = [...fields].sort((a, b) => {
    if (a.status === b.status) {
      return 0;
    }
    return a.status === "FAIL" ? -1 : 1;
  });

  sortedFields.forEach((field) => {
    const item = document.createElement("article");
    item.className = `field-result ${field.status.toLowerCase()}`;

    const heading = document.createElement("div");
    heading.className = "field-heading";
    heading.innerHTML = `
      <h3>${fieldLabels[field.field] || field.field}</h3>
      <span>${field.status === "PASS" ? "Looks good" : "Needs review"}</span>
    `;

    const values = document.createElement("dl");
    values.className = "comparison-values";
    values.innerHTML = `
      <div>
        <dt>Expected</dt>
        <dd></dd>
      </div>
      <div>
        <dt>Found on label</dt>
        <dd></dd>
      </div>
    `;
    values.querySelectorAll("dd")[0].textContent = valueOrDash(field.application_value);
    values.querySelectorAll("dd")[1].textContent = valueOrDash(field.extracted_value);

    const note = document.createElement("p");
    note.className = "field-message";
    note.textContent = field.message;

    item.append(heading, values, note);
    fieldResults.appendChild(item);
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
  submitButton.disabled = true;
  submitButton.textContent = "Checking...";
  formStatus.textContent = "Checking the label. This may take a few seconds.";

  try {
    const response = await fetch("/verify", {
      method: "POST",
      body: new FormData(form),
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
  resultPanel.hidden = true;
  setMessage("", "info");
  updateSubmitState();
}

function isFormComplete() {
  const formData = new FormData(form);
  if (!imageInput.files.length) {
    return false;
  }
  return Object.keys(fieldLabels).every((name) => String(formData.get(name) || "").trim());
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

form.addEventListener("submit", submitVerification);
form.addEventListener("input", updateSubmitState);
resetButton.addEventListener("click", resetForm);
checkHealth();
updateSubmitState();
