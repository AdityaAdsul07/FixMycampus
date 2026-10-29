
const API_URL = FMC.API_BASE;

const trackingForm = document.getElementById("tracking-form");
const trackingInput = document.getElementById("tracking-id");
const trackingMessage = document.getElementById("tracking-message");
const trackingResult = document.getElementById("tracking-result");
const trackButton = document.getElementById("track-button");

trackingForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const trackingId = trackingInput.value.trim();

  if (!trackingId) {
    trackingMessage.textContent = "Please enter your tracking ID.";
    return;
  }

  trackingMessage.textContent = "";
  trackingResult.hidden = true;
  trackButton.disabled = true;
  trackButton.textContent = "Searching...";

  try {
    const response = await fetch(
      `${API_URL}/issues/${encodeURIComponent(trackingId)}`,
      { headers: FMC.authHeaders() }
    );

    const issue = await response.json();

    if (!response.ok) {
      throw new Error(
        typeof issue.detail === "string"
          ? issue.detail
          : "Issue not found. Please check your tracking ID."
      );
    }

    document.getElementById("issue-title").textContent = issue.title;
    document.getElementById("issue-description").textContent =
      issue.description || "No additional description provided.";

    document.getElementById("result-id").textContent =
      issue.tracking_id;

    document.getElementById("result-status").textContent =
      issue.status;

    document.getElementById("result-location").textContent =
      issue.location;

    document.getElementById("result-priority").textContent =
      issue.priority;

    const resolutionBox = document.getElementById("resolution-box");
    const resolutionText = document.getElementById("result-resolution");
    if (resolutionBox && resolutionText) {
      if (issue.resolution_notes) {
        resolutionText.textContent = issue.resolution_notes;
        resolutionBox.hidden = false;
      } else {
        resolutionBox.hidden = true;
      }
    }

    await renderTimeline(issue.tracking_id);
    trackingResult.hidden = false;
  } catch (error) {
    trackingMessage.textContent =
      error.message || "Unable to connect to the server. Please try again.";
  } finally {
    trackButton.disabled = false;
    trackButton.textContent = "Track issue";
  }
});


/* Progress timeline: one entry per status change, newest last. */
async function renderTimeline(trackingId) {
  const list = document.getElementById("tracking-timeline");
  list.innerHTML = "";

  try {
    const response = await fetch(
      `${API_URL}/issues/${encodeURIComponent(trackingId)}/history`,
      { headers: FMC.authHeaders() }
    );
    const events = await response.json();
    if (!response.ok || !Array.isArray(events)) throw new Error("No history");

    events.forEach(event => {
      const item = document.createElement("li");

      const title = document.createElement("strong");
      title.textContent = event.status;
      item.appendChild(title);

      const when = document.createElement("span");
      when.className = "timeline-time";
      when.textContent = new Date(event.created_at).toLocaleString([], {
        dateStyle: "medium", timeStyle: "short"
      });
      item.appendChild(when);

      if (event.note) {
        const note = document.createElement("p");
        note.textContent = event.note;
        item.appendChild(note);
      }
      list.appendChild(item);
    });
  } catch {
    const item = document.createElement("li");
    item.textContent = "Timeline is not available right now.";
    list.appendChild(item);
  }
}
