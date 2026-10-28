
"use strict";

/* =========================================
   FIXMYCAMPUS — ADMIN DASHBOARD
========================================= */

const API_URL = FMC.API_BASE;

/* Only staff and administrators may use this page. */
const session = FMC.getAuth();
if (!session || !FMC.isStaff(session.user)) {
  window.location.replace("login.html?next=admin.html");
}

/* DOM ELEMENTS */

const reportsBody = document.getElementById("admin-reports");
const message = document.getElementById("admin-message");
const analyticsMessage = document.getElementById("analytics-message");

const searchInput = document.getElementById("report-search");
const statusFilter = document.getElementById("status-filter");
const priorityFilter = document.getElementById("priority-filter");

const refreshButton = document.getElementById("admin-refresh");
const analyticsRefreshButton = document.getElementById("analytics-refresh");
const clearFiltersButton = document.getElementById("clear-filters");

const allowedStatuses = [
  "Submitted",
  "Under Review",
  "Assigned",
  "In Progress",
  "Resolved",
  "Closed",
  "Rejected"
];

/* APPLICATION STATE */

let allReports = [];
let statusChart = null;
let priorityChart = null;
let categoryChart = null;
let trendsChart = null;
let loadingReports = false;


/* =========================================
   HELPERS
========================================= */

function setMessage(text, isError = false) {
  if (!message) return;

  message.textContent = text;
  message.classList.toggle("error", isError);
}

function setAnalyticsMessage(text) {
  if (analyticsMessage) {
    analyticsMessage.textContent = text;
  }
}

function setCounter(id, value) {
  const element = document.getElementById(id);

  if (element) {
    element.textContent = String(value);
  } else {
    console.error(`FixMyCampus: missing counter #${id}`);
  }
}

function getReportCategory(report) {
  return report.category || report.issue_type || "Unspecified";
}

function getReportPriority(report) {
  return report.priority || "Unspecified";
}

function formatDate(value) {
  if (!value) return "Not available";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

async function readResponse(response) {
  const text = await response.text();

  let data = {};

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (response.status === 401) {
    FMC.logout(); // token missing, invalid or expired
  }

  if (!response.ok) {
    throw new Error(
      data.detail || `Request failed with status ${response.status}`
    );
  }

  return data;
}


/* =========================================
   LOAD REPORTS
========================================= */

async function loadAdminReports() {
  if (loadingReports) return;

  loadingReports = true;

  if (reportsBody) {
    reportsBody.innerHTML =
      '<tr><td colspan="5">Loading reports...</td></tr>';
  }

  setMessage("");
  setAnalyticsMessage("");

  if (refreshButton) {
    refreshButton.disabled = true;
  }

  try {
    const response = await fetch(`${API_URL}/issues`, {
      headers: FMC.authHeaders({ Accept: "application/json" })
    });

    const reports = await readResponse(response);

    if (!Array.isArray(reports)) {
      throw new Error("The reports API did not return a list.");
    }

    allReports = reports;
    window.allReports = allReports;

    updateCounters(allReports);
    renderReports();
    updateAnalyticsCharts(allReports);

    console.log(
      `FixMyCampus: loaded ${allReports.length} report(s).`
    );
  } catch (error) {
    console.error("FixMyCampus report-loading error:", error);

    if (reportsBody) {
      reportsBody.innerHTML =
        '<tr><td colspan="5">Unable to load reports. Check that the backend is running.</td></tr>';
    }

    setMessage(
      `${error.message}. Check the backend at http://127.0.0.1:8000/docs`,
      true
    );

    setAnalyticsMessage("Reports could not be loaded, so charts were not updated.");
  } finally {
    loadingReports = false;

    if (refreshButton) {
      refreshButton.disabled = false;
    }
  }
}


/* =========================================
   UPDATE DASHBOARD COUNTERS
========================================= */

function updateCounters(reports) {
  setCounter("admin-total", reports.length);

  setCounter(
    "admin-submitted",
    reports.filter(report => report.status === "Submitted").length
  );

  setCounter(
    "admin-progress",
    reports.filter(report => report.status === "In Progress").length
  );

  setCounter(
    "admin-resolved",
    reports.filter(report => report.status === "Resolved").length
  );
}


/* =========================================
   SEARCH AND FILTER
========================================= */

function renderReports() {
  if (!reportsBody) {
    console.error("FixMyCampus: #admin-reports was not found.");
    return;
  }

  const searchText = (searchInput?.value || "").trim().toLowerCase();
  const selectedStatus = statusFilter?.value || "All";
  const selectedPriority = priorityFilter?.value || "All";

  const filteredReports = allReports.filter(report => {
    const searchableText = [
      report.title,
      report.description,
      report.location,
      report.tracking_id,
      report.category,
      report.reporter_name
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    const matchesSearch = searchableText.includes(searchText);

    const matchesStatus =
      selectedStatus === "All" ||
      report.status === selectedStatus;

    const matchesPriority =
      selectedPriority === "All" ||
      String(getReportPriority(report)).toLowerCase() ===
        selectedPriority.toLowerCase();

    return matchesSearch && matchesStatus && matchesPriority;
  });

  reportsBody.replaceChildren();

  if (filteredReports.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");

    cell.colSpan = 5;
    cell.textContent = allReports.length
      ? "No matching reports found."
      : "No reports have been submitted yet.";

    row.appendChild(cell);
    reportsBody.appendChild(row);
    return;
  }

  for (const report of filteredReports) {
    const row = document.createElement("tr");

    /* ISSUE TITLE AND DESCRIPTION */

    const issueCell = document.createElement("td");

    const titleButton = document.createElement("button");
    titleButton.type = "button";
    titleButton.className = "report-title-link";
    titleButton.dataset.reportDetails = report.tracking_id || "";
    titleButton.textContent = report.title || "Untitled issue";
    titleButton.title = "View report details";

    const description = document.createElement("p");
    description.className = "muted";
    description.textContent = report.description || "";

    issueCell.append(titleButton, description);

    /* LOCATION */

    const locationCell = document.createElement("td");
    locationCell.textContent = report.location || "Not specified";

    /* PRIORITY */

    const priorityCell = document.createElement("td");
    priorityCell.textContent = getReportPriority(report);

    /* TRACKING ID */

    const trackingCell = document.createElement("td");
    const trackingButton = document.createElement("button");

    trackingButton.type = "button";
    trackingButton.className = "tracking-badge-btn";
    trackingButton.dataset.reportDetails = report.tracking_id || "";
    trackingButton.textContent = report.tracking_id || "N/A";
    trackingButton.title = "View report details";

    trackingCell.appendChild(trackingButton);

    /* STATUS SELECT */

    const statusCell = document.createElement("td");
    const statusSelect = document.createElement("select");

    statusSelect.setAttribute(
      "aria-label",
      `Status for ${report.tracking_id || "report"}`
    );

    for (const status of allowedStatuses) {
      const option = document.createElement("option");
      option.value = status;
      option.textContent = status;
      statusSelect.appendChild(option);
    }

    if (
      report.status &&
      !allowedStatuses.includes(report.status)
    ) {
      const extraOption = document.createElement("option");
      extraOption.value = report.status;
      extraOption.textContent = report.status;
      statusSelect.appendChild(extraOption);
    }

    statusSelect.value = report.status || "Submitted";

    statusSelect.addEventListener("change", () => {
      updateReportStatus(report.tracking_id, statusSelect);
    });

    statusCell.appendChild(statusSelect);

    row.append(
      issueCell,
      locationCell,
      priorityCell,
      trackingCell,
      statusCell
    );

    reportsBody.appendChild(row);
  }
}


/* =========================================
   UPDATE REPORT STATUS
========================================= */

async function updateReportStatus(trackingId, select) {
  if (!trackingId) {
    setMessage("This report has no tracking ID.", true);
    await loadAdminReports();
    return;
  }

  const newStatus = select.value;

  select.disabled = true;
  setMessage(`Updating report ${trackingId}...`);

  try {
    const response = await fetch(
      `${API_URL}/issues/${encodeURIComponent(trackingId)}/status`,
      {
        method: "PATCH",
        headers: FMC.authHeaders({
          "Content-Type": "application/json",
          Accept: "application/json"
        }),
        body: JSON.stringify({ status: newStatus })
      }
    );

    const result = await readResponse(response);

    setMessage(
      `Report ${trackingId} updated to ${result.status || newStatus}.`
    );

    await loadAdminReports();
  } catch (error) {
    console.error("FixMyCampus status-update error:", error);
    setMessage(error.message || "Could not update the report status.", true);
    await loadAdminReports();
  } finally {
    select.disabled = false;
  }
}


/* =========================================
   COUNT REPORTS BY FIELD
========================================= */

function countBy(reports, primaryField, fallbackField = null) {
  const counts = {};

  for (const report of reports) {
    let value = report[primaryField];

    if (
      (value === undefined || value === null || value === "") &&
      fallbackField
    ) {
      value = report[fallbackField];
    }

    const label =
      value === undefined || value === null || value === ""
        ? "Unspecified"
        : String(value);

    counts[label] = (counts[label] || 0) + 1;
  }

  return counts;
}


/* =========================================
   CHART HELPERS
========================================= */

function destroyChart(chart) {
  if (chart) {
    chart.destroy();
  }
}

function chartOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "bottom"
      }
    }
  };
}


/* =========================================
   ANALYTICS CHARTS
========================================= */

function updateAnalyticsCharts(reports) {
  if (typeof Chart === "undefined") {
    setAnalyticsMessage(
      "Chart.js did not load. Check your internet connection and refresh the page."
    );
    return;
  }

  const statusCanvas = document.getElementById("status-chart");
  const priorityCanvas = document.getElementById("priority-chart");
  const categoryCanvas = document.getElementById("category-chart");
  const trendsCanvas = document.getElementById("trends-chart");

  if (
    !statusCanvas ||
    !priorityCanvas ||
    !categoryCanvas ||
    !trendsCanvas
  ) {
    setAnalyticsMessage(
      "One or more chart canvases are missing from admin.html."
    );
    return;
  }

  const statusCounts = countBy(reports, "status");
  const priorityCounts = countBy(reports, "priority");
  const categoryCounts = countBy(reports, "category", "issue_type");

  const standardStatuses = [
    "Submitted",
    "Under Review",
    "Assigned",
    "In Progress",
    "Resolved",
    "Closed",
    "Rejected"
  ];

  const statusLabels = [
    ...standardStatuses,
    ...Object.keys(statusCounts).filter(
      label => !standardStatuses.includes(label)
    )
  ];

  const statusValues = statusLabels.map(
    label => statusCounts[label] || 0
  );

  const priorityLabels = Object.keys(priorityCounts);
  const priorityValues = priorityLabels.map(
    label => priorityCounts[label]
  );

  const categoryLabels = Object.keys(categoryCounts);
  const categoryValues = categoryLabels.map(
    label => categoryCounts[label]
  );

  /* REPORTING TRENDS */

  const dailyCounts = {};

  for (const report of reports) {
    if (!report.created_at) continue;

    const date = String(report.created_at).slice(0, 10);

    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) continue;

    dailyCounts[date] = (dailyCounts[date] || 0) + 1;
  }

  const sortedDates = Object.keys(dailyCounts).sort();

  const trendLabels = sortedDates.map(date =>
    new Date(`${date}T00:00:00`).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric"
    })
  );

  const trendValues = sortedDates.map(date => dailyCounts[date]);

  /* CLEAR OLD CHARTS */

  destroyChart(statusChart);
  destroyChart(priorityChart);
  destroyChart(categoryChart);
  destroyChart(trendsChart);

  statusChart = null;
  priorityChart = null;
  categoryChart = null;
  trendsChart = null;

  try {
    /* 1. STATUS CHART */

    statusChart = new Chart(statusCanvas, {
      type: "doughnut",
      data: {
        labels: statusLabels,
        datasets: [{
          label: "Reports",
          data: statusValues,
          backgroundColor: [
            "#64748b",
            "#f59e0b",
            "#10b981",
            "#ef4444",
            "#8b5cf6",
            "#06b6d4",
            "#ec4899",
            "#a3a3a3"
          ],
          borderWidth: 2,
          borderColor: "#ffffff"
        }]
      },
      options: chartOptions()
    });

    /* 2. PRIORITY CHART */

    priorityChart = new Chart(priorityCanvas, {
      type: "doughnut",
      data: {
        labels: priorityLabels.length
          ? priorityLabels
          : ["No reports"],
        datasets: [{
          label: "Reports",
          data: priorityLabels.length
            ? priorityValues
            : [1],
          backgroundColor: [
            "#94a3b8",
            "#22c55e",
            "#f59e0b",
            "#ef4444",
            "#8b5cf6",
            "#06b6d4"
          ],
          borderWidth: 2,
          borderColor: "#ffffff"
        }]
      },
      options: chartOptions()
    });

    /* 3. CATEGORY CHART */

    categoryChart = new Chart(categoryCanvas, {
      type: "bar",
      data: {
        labels: categoryLabels.length
          ? categoryLabels
          : ["No category data"],
        datasets: [{
          label: "Number of reports",
          data: categoryLabels.length
            ? categoryValues
            : [0],
          backgroundColor: "#6366f1",
          borderRadius: 6,
          maxBarThickness: 48
        }]
      },
      options: {
        ...chartOptions(),
        indexAxis: "y",
        scales: {
          x: {
            beginAtZero: true,
            ticks: { precision: 0 }
          },
          y: {
            grid: { display: false }
          }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });

    /* 4. REPORTING TRENDS CHART */

    trendsChart = new Chart(trendsCanvas, {
      type: "line",
      data: {
        labels: trendLabels,
        datasets: [{
          label: "Issues reported",
          data: trendValues,
          borderColor: "#6366f1",
          backgroundColor: "rgba(99, 102, 241, 0.14)",
          borderWidth: 3,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointBackgroundColor: "#6366f1",
          fill: true,
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: "index"
        },
        scales: {
          x: {
            title: {
              display: true,
              text: "Report creation date"
            }
          },
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: "Number of reports"
            },
            ticks: {
              precision: 0
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: "bottom"
          },
          tooltip: {
            callbacks: {
              label: context =>
                `Issues reported: ${context.raw}`
            }
          }
        }
      }
    });

    if (reports.length === 0) {
      setAnalyticsMessage(
        "No reports yet. Charts will update when reports are submitted."
      );
    } else if (sortedDates.length === 0) {
      setAnalyticsMessage(
        `Charts use ${reports.length} report(s), but no valid creation dates were found for Issue Trends.`
      );
    } else {
      setAnalyticsMessage(
        `Charts updated using ${reports.length} report(s) across ${sortedDates.length} reporting date(s).`
      );
    }
  } catch (error) {
    console.error("FixMyCampus chart error:", error);

    setAnalyticsMessage(
      "Could not draw one or more charts. Open the browser console for details."
    );
  }
}


/* =========================================
   SEARCH, FILTER AND CLEAR
========================================= */

if (searchInput) {
  searchInput.addEventListener("input", renderReports);
}

if (statusFilter) {
  statusFilter.addEventListener("change", renderReports);
}

if (priorityFilter) {
  priorityFilter.addEventListener("change", renderReports);
}

if (clearFiltersButton) {
  clearFiltersButton.addEventListener("click", () => {
    if (searchInput) searchInput.value = "";
    if (statusFilter) statusFilter.value = "All";
    if (priorityFilter) priorityFilter.value = "All";

    renderReports();
  });
}

if (refreshButton) {
  refreshButton.addEventListener("click", loadAdminReports);
} else {
  console.warn("FixMyCampus: #admin-refresh was not found.");
}

if (analyticsRefreshButton) {
  analyticsRefreshButton.addEventListener("click", async () => {
    await loadAdminReports();
  });
}


/* =========================================
   REPORT DETAILS MODAL
========================================= */

(function setupReportDetailsModal() {
  const modal = document.getElementById("report-details-modal");

  if (!modal) {
    console.warn(
      "FixMyCampus: #report-details-modal was not found."
    );
    return;
  }

  const closeButton = document.getElementById("close-report-details");
  const footerCloseButton = document.getElementById(
    "close-report-details-footer"
  );

  const fields = {
    tracking_id: document.getElementById("detail-tracking-id"),
    title: document.getElementById("detail-title"),
    description: document.getElementById("detail-description"),
    category: document.getElementById("detail-category"),
    location: document.getElementById("detail-location"),
    reporter: document.getElementById("detail-reporter"),
    priority: document.getElementById("detail-priority"),
    status: document.getElementById("detail-status"),
    created_at: document.getElementById("detail-created"),
    updated_at: document.getElementById("detail-updated")
  };

  let previouslyFocusedElement = null;

  function setField(name, value) {
    const element = fields[name];

    if (!element) return;

    if (name === "created_at" || name === "updated_at") {
      element.textContent = formatDate(value);
      return;
    }

    element.textContent =
      value === undefined || value === null || value === ""
        ? "Not available"
        : String(value);
  }

  function closeDetails() {
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";

    if (
      previouslyFocusedElement &&
      typeof previouslyFocusedElement.focus === "function"
    ) {
      previouslyFocusedElement.focus();
    }
  }

  function openDetails(trackingId) {
    const report = allReports.find(
      item => String(item.tracking_id) === String(trackingId)
    );

    if (!report) {
      setMessage(
        `Could not find report ${trackingId}. Refresh and try again.`,
        true
      );
      return;
    }

    previouslyFocusedElement = document.activeElement;

    setField("tracking_id", report.tracking_id);
    setField("title", report.title);
    setField("description", report.description);
    setField("category", getReportCategory(report));
    setField("location", report.location);

    setField(
      "reporter",
      report.reporter_name ||
      report.reporter ||
      report.name ||
      report.email
    );

    setField("priority", report.priority);
    setField("status", report.status);
    setField("created_at", report.created_at);
    setField("updated_at", report.updated_at);

    if (window.fmcOnReportOpen) window.fmcOnReportOpen(report);

    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";

    if (closeButton) {
      closeButton.focus();
    }
  }

  if (closeButton) {
    closeButton.addEventListener("click", closeDetails);
  }

  if (footerCloseButton) {
    footerCloseButton.addEventListener("click", closeDetails);
  }

  modal.addEventListener("click", event => {
    if (
      event.target instanceof Element &&
      event.target.matches("[data-close-modal]")
    ) {
      closeDetails();
    }
  });

  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !modal.hidden) {
      closeDetails();
    }
  });

  if (reportsBody) {
    reportsBody.addEventListener("click", event => {
      if (!(event.target instanceof Element)) return;

      const trigger = event.target.closest("[data-report-details]");

      if (!trigger) return;

      const trackingId = trigger.dataset.reportDetails;

      if (trackingId) {
        openDetails(trackingId);
      }
    });
  }

  window.openFixMyCampusReportDetails = openDetails;
})();


/* =========================================
   INITIALIZE DASHBOARD
========================================= */

if (session && FMC.isStaff(session.user)) {
  loadAdminReports();
}
