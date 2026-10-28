
const API_URL = "http://127.0.0.1:8000/api";

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
      `${API_URL}/issues/${encodeURIComponent(trackingId)}`
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

    trackingResult.hidden = false;
  } catch (error) {
    trackingMessage.textContent =
      error.message || "Unable to connect to the server. Please try again.";
  } finally {
    trackButton.disabled = false;
    trackButton.textContent = "Track issue";
  }
});
