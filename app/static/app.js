const form = document.querySelector("#verify-form");
const cardsContainer = document.querySelector("#label-cards");
const cardTemplate = document.querySelector("#label-card-template");
const addLabelButton = document.querySelector("#add-label-button");
const submitButton = document.querySelector("#submit-button");
const resetButton = document.querySelector("#reset-button");
const message = document.querySelector("#message");
const resultPanel = document.querySelector("#result-panel");
const batchSummary = document.querySelector("#batch-summary");
const batchResults = document.querySelector("#batch-results");
const extractedList = document.querySelector("#extracted-list");
const extractedDetails = document.querySelector("#single-extracted-details");
const verdictBadge = document.querySelector("#verdict-badge");
const latency = document.querySelector("#latency");
const healthBadge = document.querySelector("#health-badge");
const formStatus = document.querySelector("#form-status");
const progressPanel = document.querySelector("#progress-panel");
const progressText = document.querySelector("#progress-text");

const maxLabels = 5;
let cardCount = 0;
let progressTimer = null;
let elapsedTimer = null;
let progressStartedAt = 0;

const fieldLabels = {
  brand_name: "Brand name",
  product_class: "Product type",
  producer: "Producer or company",
  country_of_origin: "Country",
  abv: "Alcohol percentage",
  net_contents: "Bottle size",
  government_warning: "Government warning",
};

const fieldNames = Object.keys(fieldLabels);

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

function labelCards() {
  return [...cardsContainer.querySelectorAll(".label-card")];
}

function cardNumber(card) {
  return labelCards().indexOf(card) + 1;
}

function clearInlineResults(card = null) {
  const scope = card || document;
  scope.querySelectorAll("[data-result-for]").forEach((item) => {
    item.className = "inline-result pending";
    item.querySelector(".result-status").textContent = "Not checked";
    item.querySelector(".result-value").textContent = "Found on label will appear here.";
    item.querySelector(".result-message").textContent = "";
  });
}

function renderFields(card, fields) {
  clearInlineResults(card);

  fields.forEach((field) => {
    const item = card.querySelector(`[data-result-for="${field.field}"]`);
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

function renderSingleResult(item, summary) {
  resultPanel.hidden = false;
  batchSummary.hidden = true;
  batchResults.innerHTML = "";
  extractedDetails.hidden = false;

  const verdict = item.verification?.verdict || item.status;
  verdictBadge.textContent = verdict === "PASS" ? "APPROVED" : "NEEDS REVIEW";
  verdictBadge.className = `verdict-badge ${verdict === "PASS" ? "pass" : "review"}`;
  latency.textContent = `Checked in ${(summary.latency_ms / 1000).toFixed(1)} seconds`;

  const firstCard = labelCards()[0];
  if (firstCard && item.verification) {
    renderFields(firstCard, item.verification.fields);
  }
  renderExtracted(item.extracted_label || {});
}

function renderBatchResult(body) {
  resultPanel.hidden = false;
  extractedDetails.hidden = true;
  batchSummary.hidden = false;
  batchResults.innerHTML = "";

  verdictBadge.textContent = body.summary.needs_review ? "NEEDS REVIEW" : "APPROVED";
  verdictBadge.className = `verdict-badge ${body.summary.needs_review ? "review" : "pass"}`;
  latency.textContent = `Checked in ${(body.summary.latency_ms / 1000).toFixed(1)} seconds`;
  batchSummary.innerHTML = `
    <div><strong>${body.summary.passed}</strong><span>approved</span></div>
    <div><strong>${body.summary.needs_review}</strong><span>needs review</span></div>
    <div><strong>${body.summary.total}</strong><span>total</span></div>
  `;

  body.results.forEach((item) => {
    const details = document.createElement("details");
    details.className = `batch-result ${item.status === "PASS" ? "approved" : "review"}`;

    const label = item.filename || `Label ${item.index + 1}`;
    details.innerHTML = `
      <summary>
        <span>${label}</span>
        <span>${item.status === "PASS" ? "APPROVED" : "NEEDS REVIEW"}</span>
        <span class="details-action">View details</span>
      </summary>
      <div class="batch-detail"></div>
    `;

    const detail = details.querySelector(".batch-detail");
    if (item.verification) {
      const failed = item.verification.fields.filter((field) => field.status === "FAIL");
      const passed = item.verification.fields.filter((field) => field.status === "PASS");
      [...failed, ...passed].forEach((field) => {
        const row = document.createElement("article");
        row.className = `field-result ${field.status.toLowerCase()}`;
        row.innerHTML = `
          <div class="field-heading">
            <h3>${fieldLabels[field.field] || field.field}</h3>
            <span>${field.status === "PASS" ? "Looks good" : "Needs review"}</span>
          </div>
          <dl class="comparison-values">
            <div>
              <dt>Expected</dt>
              <dd></dd>
            </div>
            <div>
              <dt>Found on label</dt>
              <dd></dd>
            </div>
          </dl>
          <p class="field-message">${field.message || ""}</p>
        `;
        row.querySelectorAll("dd")[0].textContent = valueOrDash(field.application_value);
        row.querySelectorAll("dd")[1].textContent = valueOrDash(field.extracted_value);
        detail.append(row);
      });
    }

    if (Object.keys(item.errors || {}).length) {
      const errorList = document.createElement("ul");
      errorList.className = "item-errors";
      Object.entries(item.errors).forEach(([field, text]) => {
        const li = document.createElement("li");
        li.textContent = plainError(field, text);
        errorList.append(li);
      });
      detail.append(errorList);
    }

    batchResults.append(details);
  });
}

function renderResult(body) {
  if (body.results.length === 1) {
    renderSingleResult(body.results[0], body.summary);
    return;
  }
  labelCards().forEach((card, index) => {
    const item = body.results[index];
    if (item?.verification) {
      renderFields(card, item.verification.fields);
    }
  });
  renderBatchResult(body);
}

function renderErrors(body) {
  const errors = body.errors || {};
  const parts = Object.entries(errors).map(([field, text]) => plainError(field, text));
  setMessage(parts.length ? parts.join(" ") : body.message || "Request failed.", "error");
  message.focus();
}

function plainError(field, text) {
  const label = fieldLabels[field] || (field === "images" ? "Label photos" : field === "image" ? "Label photo" : field);
  if ((field === "image" || field === "images") && text.includes("Unsupported")) {
    return field === "image"
      ? "Please choose a JPG, PNG, or WebP photo."
      : "Please choose JPG, PNG, or WebP photos.";
  }
  if (field === "image" && (text.includes("larger") || text.includes("large"))) {
    return "The photo is too large. Please choose one under 8 MB.";
  }
  if (field === "images" && text.includes("25 MB")) {
    return "The selected photos are too large. Please keep the batch under 25 MB.";
  }
  if (field === "images" && (text.includes("larger") || text.includes("large"))) {
    return "The selected photos are too large.";
  }
  if (field === "image" || field === "images") {
    return "Please choose a label photo.";
  }
  if (text.includes("required") || text.includes("empty")) {
    return `Please fill in ${label}.`;
  }
  return `${label}: ${text}`;
}

function setBusy(isBusy) {
  form.querySelectorAll("input, select, textarea, button").forEach((control) => {
    control.disabled = isBusy;
  });
  if (!isBusy) {
    updateSubmitState();
  }
}

function startProgress(count) {
  progressStartedAt = Date.now();
  progressTimer = setTimeout(() => {
    progressPanel.hidden = false;
    progressText.textContent = `Checking ${count} ${count === 1 ? "label" : "labels"}. This may take a few seconds.`;
    elapsedTimer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - progressStartedAt) / 1000);
      progressText.textContent = `Checking ${count} ${count === 1 ? "label" : "labels"}. ${elapsed} seconds elapsed.`;
    }, 1000);
  }, 700);
}

function stopProgress() {
  clearTimeout(progressTimer);
  clearInterval(elapsedTimer);
  progressPanel.hidden = true;
}

async function submitVerification(event) {
  event.preventDefault();
  if (!isFormComplete()) {
    updateSubmitState();
    return;
  }

  const count = labelCards().length;
  setMessage("", "info");
  resultPanel.hidden = true;
  batchResults.innerHTML = "";
  clearInlineResults();
  submitButton.textContent = count === 1 ? "Checking..." : "Checking all...";
  formStatus.textContent = `Checking ${count} ${count === 1 ? "label" : "labels"}. This may take a few seconds.`;
  setBusy(true);
  startProgress(count);

  try {
    const response = await fetch("/verify/batch", {
      method: "POST",
      body: buildBatchFormData(),
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
    stopProgress();
    setBusy(false);
    updateSubmitState();
  }
}

function resetForm() {
  cardsContainer.innerHTML = "";
  cardCount = 0;
  addLabelCard();
  resultPanel.hidden = true;
  batchResults.innerHTML = "";
  setMessage("", "info");
  updateSubmitState();
}

function selectedCountryValue(card) {
  const countrySelect = card.querySelector('[data-field="country_of_origin"]');
  const countryOther = card.querySelector(".other-input");
  if (countrySelect.value === "__other__") {
    return countryOther.value.trim();
  }
  return countrySelect.value.trim();
}

function cardData(card) {
  const values = {};
  fieldNames.forEach((name) => {
    if (name === "country_of_origin") {
      values[name] = selectedCountryValue(card);
      return;
    }
    const input = card.querySelector(`[data-field="${name}"]`);
    values[name] = String(input.value || "").trim();
  });

  if (values.abv) {
    values.abv = `${values.abv}%`;
  }

  return values;
}

function buildBatchFormData() {
  const formData = new FormData();
  const items = [];
  labelCards().forEach((card) => {
    const image = card.querySelector('[data-field="image"]');
    formData.append("images", image.files[0]);
    items.push(cardData(card));
  });
  formData.append("items_json", JSON.stringify(items));
  return formData;
}

function isCardComplete(card) {
  const image = card.querySelector('[data-field="image"]');
  if (!image.files.length) {
    return false;
  }
  return fieldNames.every((name) => {
    if (name === "country_of_origin") {
      return selectedCountryValue(card);
    }
    const input = card.querySelector(`[data-field="${name}"]`);
    return String(input.value || "").trim();
  });
}

function isFormComplete() {
  return labelCards().every(isCardComplete);
}

function updateCardTitles() {
  const cards = labelCards();
  cards.forEach((card, index) => {
    card.querySelector(".card-heading h2").textContent = `Label ${index + 1}`;
    card.querySelector(".remove-label").hidden = cards.length === 1;
  });
}

function updateSubmitState() {
  const cards = labelCards();
  const complete = cards.length > 0 && isFormComplete();
  const multiple = cards.length > 1;
  submitButton.disabled = !complete;
  submitButton.textContent = multiple ? "Check All Labels" : "Check Label";
  resetButton.textContent = multiple ? "Check Another Batch" : "Check Another Label";
  addLabelButton.disabled = cards.length >= maxLabels;
  formStatus.textContent = complete
    ? cards.length >= maxLabels
      ? "Maximum 5 labels at a time."
      : ""
    : "Add the missing items to check this label.";
}

function addLabelCard() {
  if (labelCards().length >= maxLabels) {
    updateSubmitState();
    return;
  }

  cardCount += 1;
  const card = cardTemplate.content.firstElementChild.cloneNode(true);
  cardsContainer.append(card);
  updateCardTitles();
  clearInlineResults(card);

  const imageInput = card.querySelector('[data-field="image"]');
  const fileName = card.querySelector("[data-file-name]");
  const imagePreview = card.querySelector(".image-preview");
  const countrySelect = card.querySelector('[data-field="country_of_origin"]');
  const countryOther = card.querySelector(".other-input");

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

  card.querySelector(".remove-label").addEventListener("click", () => {
    card.remove();
    updateCardTitles();
    updateSubmitState();
  });

  updateSubmitState();
}

addLabelButton.addEventListener("click", addLabelCard);
form.addEventListener("submit", submitVerification);
form.addEventListener("input", updateSubmitState);
resetButton.addEventListener("click", resetForm);
checkHealth();
addLabelCard();
