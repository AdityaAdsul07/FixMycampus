
const API = FMC.API_BASE;

const issueForm = document.getElementById("issue-form");
const submitButton = document.getElementById("submit-button");
const formMessage = document.getElementById("form-message");
const successBox = document.getElementById("success-box");
const issuesList = document.getElementById("issues-list");
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const statusFilter = document.getElementById("status-filter");
const searchResult = document.getElementById("search-result");

let allIssues = [];

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[character]);
}

function formatDate(value) {
  if (!value) return "Date unavailable";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";

  return date.toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short"
  });
}

function statusClass(status) {
  return "status-" + String(status)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function showMessage(message, type = "info") {
  formMessage.textContent = message;
  formMessage.className = "form-message " + type;
}

async function requestJSON(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    let message = data.detail || `Request failed (${response.status})`;

    if (Array.isArray(message)) {
      message = message.map(item => item.msg).join(", ");
    }

    throw new Error(message);
  }

  return data;
}

async function loadStats() {
  try {
    const stats = await requestJSON(`${API}/stats`);

    document.getElementById("total-count").textContent = stats.total ?? 0;
    document.getElementById("open-count").textContent = stats.open ?? 0;
    document.getElementById("resolved-count").textContent =
      stats.resolved ?? stats.by_status?.Resolved ?? 0;
  } catch (error) {
    document.getElementById("total-count").textContent = "—";
    document.getElementById("open-count").textContent = "—";
    document.getElementById("resolved-count").textContent = "—";
    console.error("Could not load statistics:", error);
  }
}

async function loadIssues() {
  issuesList.innerHTML = '<div class="loading">Loading campus reports...</div>';

  try {
    allIssues = await requestJSON(`${API}/issues`);
    renderIssues();
  } catch (error) {
    issuesList.innerHTML = `
      <div class="empty-state">
        <strong>Couldn't load reports</strong>
        ${escapeHTML(error.message)}<br>
        Check that your FastAPI server is running.
      </div>`;
  }
}

function renderIssues() {
  const selectedStatus = statusFilter.value;
  const query = searchInput.value.trim().toLowerCase();

  const filtered = allIssues.filter(issue => {
    const matchesStatus =
      selectedStatus === "All" || issue.status === selectedStatus;

    const searchable = [
      issue.title,
      issue.description,
      issue.category,
      issue.location,
      issue.tracking_id,
      issue.status
    ].join(" ").toLowerCase();

    return matchesStatus && searchable.includes(query);
  });

  if (filtered.length === 0) {
    issuesList.innerHTML = `
      <div class="empty-state">
        <strong>No matching reports</strong>
        Try another search or status filter.
      </div>`;
    return;
  }

  issuesList.innerHTML = filtered.map(issue => `
    <article class="issue-card">
      <div class="issue-top">
        <h3>${escapeHTML(issue.title)}</h3>
        <span class="status ${statusClass(issue.status)}">
          ${escapeHTML(issue.status)}
        </span>
      </div>
      <p class="issue-description">${escapeHTML(issue.description)}</p>
      <div class="issue-meta">
        <span>▦ ${escapeHTML(issue.category)}</span>
        <span>⌖ ${escapeHTML(issue.location)}</span>
      </div>
      <div class="issue-meta" style="margin-top:9px">
        <span>Priority: ${escapeHTML(issue.priority)}</span>
        <span>${escapeHTML(formatDate(issue.created_at))}</span>
      </div>
      <div class="tracking-line">
        Tracking ID: ${escapeHTML(issue.tracking_id)}
      </div>
    </article>
  `).join("");
}

issueForm.addEventListener("submit", async event => {
  event.preventDefault();

  if (!issueForm.reportValidity()) return;

  const formData = new FormData(issueForm);
  const payload = Object.fromEntries(formData.entries());

  payload.title = payload.title.trim();
  payload.description = payload.description.trim();
  payload.category = payload.category.trim();
  payload.location = payload.location.trim();
  payload.reporter_name = payload.reporter_name.trim();

  submitButton.disabled = true;
  submitButton.textContent = "Submitting...";
  successBox.classList.add("hidden");
  showMessage("Sending your report...", "info");

  try {
    const issue = await requestJSON(`${API}/issues`, {
      method: "POST",
      headers: FMC.authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });

    showMessage("Your issue has been saved successfully.", "info");
    document.getElementById("new-tracking-id").textContent =
      issue.tracking_id;
    successBox.classList.remove("hidden");

    issueForm.reset();
    prefillReporter();

    await Promise.all([loadStats(), loadIssues()]);

    // Bring the new report and its tracking ID into view.
    successBox.scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (error) {
    showMessage(
      `Could not submit the report: ${error.message}. Check that your backend is running.`,
      "error"
    );
  } finally {
    submitButton.disabled = false;
    submitButton.innerHTML = 'Submit report <span>→</span>';
  }
});

searchForm.addEventListener("submit", async event => {
  event.preventDefault();

  const query = searchInput.value.trim();
  searchResult.classList.add("hidden");

  // A full tracking ID searches the backend directly.
  if (/^FMC-[A-Z0-9]+$/i.test(query)) {
    searchResult.classList.remove("hidden");
    searchResult.innerHTML = '<p>Looking up tracking ID...</p>';

    try {
      const issue = await requestJSON(
        `${API}/issues/${encodeURIComponent(query)}`
      );

      searchResult.innerHTML = `
        <span class="status ${statusClass(issue.status)}">
          ${escapeHTML(issue.status)}
        </span>
        <h3>${escapeHTML(issue.title)}</h3>
        <p><strong>Tracking ID:</strong> ${escapeHTML(issue.tracking_id)}</p>
        <p><strong>Category:</strong> ${escapeHTML(issue.category)}</p>
        <p><strong>Location:</strong> ${escapeHTML(issue.location)}</p>
        <p><strong>Priority:</strong> ${escapeHTML(issue.priority)}</p>
        <p><strong>Reported:</strong> ${escapeHTML(formatDate(issue.created_at))}</p>
        <p>${escapeHTML(issue.description)}</p>`;
    } catch (error) {
      searchResult.innerHTML = `
        <p>${escapeHTML(error.message)}. Check the tracking ID and try again.</p>`;
    }
  }

  renderIssues();
});

searchInput.addEventListener("input", renderIssues);
statusFilter.addEventListener("change", renderIssues);

document.getElementById("refresh-button").addEventListener("click", async () => {
  await Promise.all([loadStats(), loadIssues()]);
});

document.getElementById("clear-search").addEventListener("click", () => {
  searchInput.value = "";
  statusFilter.value = "All";
  searchResult.classList.add("hidden");
  renderIssues();
});

document.getElementById("new-tracking-id").addEventListener("click", async event => {
  const button = event.currentTarget;
  const trackingID = button.textContent;

  try {
    await navigator.clipboard.writeText(trackingID);
    button.textContent = "Copied!";
    setTimeout(() => {
      button.textContent = trackingID;
    }, 1500);
  } catch {
    showMessage(`Your tracking ID is ${trackingID}. Please copy it manually.`, "info");
  }
});

// Logged-in users don't need to retype their name.
function prefillReporter() {
  const auth = FMC.getAuth();
  const nameField = document.getElementById("reporter_name");
  if (auth && nameField && !nameField.value) nameField.value = auth.user.full_name;
}

// Load the saved data when the page opens.
async function initializeDashboard() {
  prefillReporter();
  await Promise.all([loadStats(), loadIssues()]);
}

initializeDashboard();
