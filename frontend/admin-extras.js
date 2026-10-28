"use strict";

/* =========================================
   ADMIN EXTRAS: profile, logout, assignment, activity timeline
   Runs after admin.js; admin.js calls window.fmcOnReportOpen(report)
   whenever the report-details modal opens.
========================================= */

(function setupAdminExtras() {
  const auth = FMC.getAuth();
  if (!auth || !FMC.isStaff(auth.user)) return; // admin.js is already redirecting

  const isAdmin = auth.user.role === "admin";

  /* Sidebar profile + logout */
  document.getElementById("profile-name").textContent = auth.user.full_name;
  document.getElementById("profile-role").textContent =
    auth.user.role === "admin" ? "Administrator" : "Staff member";
  document.getElementById("profile-avatar").textContent =
    auth.user.full_name.charAt(0).toUpperCase();
  document.getElementById("logout-link").addEventListener("click", event => {
    event.preventDefault();
    FMC.logout();
  });

  const timelineList = document.getElementById("detail-timeline");
  const assignedLabel = document.getElementById("detail-assigned");
  const assignBox = document.getElementById("assign-box");
  const assignSelect = document.getElementById("assign-staff");
  const assignNote = document.getElementById("assign-note");
  const assignSave = document.getElementById("assign-save");
  const assignMessage = document.getElementById("assign-message");

  let currentTrackingId = null;
  let staffLoaded = false;

  async function api(path, options = {}) {
    const response = await fetch(`${FMC.API_BASE}${path}`, {
      ...options,
      headers: FMC.authHeaders({ "Content-Type": "application/json", ...(options.headers || {}) })
    });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) FMC.logout();
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
    return data;
  }

  async function loadStaff() {
    if (staffLoaded) return;
    const staff = await api("/staff");
    assignSelect.innerHTML = "";
    staff.forEach(member => {
      const option = document.createElement("option");
      option.value = member.id;
      option.textContent = member.department
        ? `${member.full_name} (${member.department})`
        : member.full_name;
      assignSelect.appendChild(option);
    });
    staffLoaded = true;
  }

  async function loadTimeline(trackingId) {
    timelineList.innerHTML = "<li>Loading...</li>";
    try {
      const events = await api(`/issues/${encodeURIComponent(trackingId)}/history`);
      timelineList.innerHTML = "";
      events.forEach(event => {
        const item = document.createElement("li");

        const title = document.createElement("strong");
        title.textContent = event.status;
        item.appendChild(title);

        const meta = document.createElement("span");
        meta.className = "timeline-time";
        meta.textContent = `${new Date(event.created_at).toLocaleString([], {
          dateStyle: "medium", timeStyle: "short"
        })} · ${event.actor}`;
        item.appendChild(meta);

        if (event.note) {
          const note = document.createElement("p");
          note.textContent = event.note;
          item.appendChild(note);
        }
        timelineList.appendChild(item);
      });
    } catch (error) {
      timelineList.innerHTML = "";
      const item = document.createElement("li");
      item.textContent = error.message;
      timelineList.appendChild(item);
    }
  }

  window.fmcOnReportOpen = function (report) {
    currentTrackingId = report.tracking_id;
    assignedLabel.textContent = report.assigned_staff_name || "Not assigned";
    assignMessage.textContent = "";
    assignNote.value = "";
    loadTimeline(report.tracking_id);

    assignBox.hidden = !isAdmin; // only administrators can assign
    if (isAdmin) {
      loadStaff().catch(error => { assignMessage.textContent = error.message; });
    }
  };

  assignSave.addEventListener("click", async () => {
    if (!currentTrackingId || !assignSelect.value) return;

    assignSave.disabled = true;
    assignMessage.textContent = "Assigning...";
    try {
      const updated = await api(`/issues/${encodeURIComponent(currentTrackingId)}/assign`, {
        method: "PATCH",
        body: JSON.stringify({
          assigned_to_id: Number(assignSelect.value),
          note: assignNote.value.trim() || null
        })
      });
      assignedLabel.textContent = updated.assigned_staff_name || "Not assigned";
      document.getElementById("detail-status").textContent = updated.status;
      assignMessage.textContent = "Assigned successfully.";
      assignNote.value = "";
      await loadTimeline(currentTrackingId);
      if (typeof loadAdminReports === "function") loadAdminReports(); // refresh table
    } catch (error) {
      assignMessage.textContent = error.message;
    } finally {
      assignSave.disabled = false;
    }
  });
})();
