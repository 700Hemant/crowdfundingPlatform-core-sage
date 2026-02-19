/* Dashboard controller:
 * - Handles image upload for AI detection endpoint
 * - Renders Leaflet map pins
 * - Displays stats, alerts, suggestions, and admin controls
 */
const sageCenter = [23.2114, 77.4341];
const map = L.map("map").setView(sageCenter, 15);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const markers = L.layerGroup().addTo(map);
const uploadForm = document.getElementById("uploadForm");
const uploadStatus = document.getElementById("uploadStatus");
const overlayPreview = document.getElementById("overlayPreview");

function toTitleCase(value) {
  return value
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(errorBody || `Request failed: ${res.status}`);
  }
  return res.json();
}

function renderMap(data) {
  markers.clearLayers();
  data.forEach((d) => {
    const marker = L.marker([d.latitude, d.longitude]).addTo(markers);
    marker.bindPopup(`
      <strong>${toTitleCase(d.waste_type)}</strong><br/>
      Confidence: ${(d.confidence * 100).toFixed(1)}%<br/>
      Priority: ${d.priority}<br/>
      Time: ${new Date(d.created_at).toLocaleString()}
    `);
  });
}

function renderStats(stats) {
  const statsPanel = document.getElementById("statsPanel");
  const byTypeHTML = Object.entries(stats.by_type)
    .map(([type, count]) => `<div class="stat"><strong>${toTitleCase(type)}:</strong> ${count}</div>`)
    .join("");

  statsPanel.innerHTML = `
    <div class="stat"><strong>Total:</strong> ${stats.total}</div>
    <div class="stat"><strong>Resolved:</strong> ${stats.resolved}</div>
    <div class="stat"><strong>Open:</strong> ${stats.unresolved}</div>
    ${byTypeHTML}
  `;
}

function renderAlerts(stats) {
  const panel = document.getElementById("alertPanel");
  if (stats.alerts.length === 0) {
    panel.innerHTML = "<p>No high-priority alerts.</p>";
    return;
  }

  panel.innerHTML = stats.alerts
    .map(
      (a) => `<div class="suggestion priority-high"><strong>⚠ ${a.priority.toUpperCase()}</strong><br/>${a.message}<br/><small>${a.time}</small></div>`
    )
    .join("");
}

function renderSuggestions(data) {
  const panel = document.getElementById("suggestionPanel");
  if (data.length === 0) {
    panel.innerHTML = "<p>No suggestions available yet.</p>";
    return;
  }

  panel.innerHTML = data
    .slice(0, 7)
    .map(
      (d) => `<div class="suggestion priority-${d.priority}"><strong>${toTitleCase(d.waste_type)}</strong><br/>${d.suggestion}</div>`
    )
    .join("");
}

function renderTable(data) {
  const target = document.getElementById("detectionTable");
  const rows = data
    .slice(0, 20)
    .map((d) => {
      const resolveButton =
        USER_ROLE === "admin" && !d.resolved
          ? `<button class="btn-secondary" onclick="resolveDetection(${d.id})">Mark Resolved</button>`
          : d.resolved
          ? "Resolved"
          : "Staff View";

      return `<tr>
        <td>${d.id}</td>
        <td>${toTitleCase(d.waste_type)}</td>
        <td>${(d.confidence * 100).toFixed(1)}%</td>
        <td>${d.priority}</td>
        <td>${d.resolved ? "Yes" : "No"}</td>
        <td>${resolveButton}</td>
      </tr>`;
    })
    .join("");

  target.innerHTML = `
    <table>
      <thead><tr><th>ID</th><th>Type</th><th>Confidence</th><th>Priority</th><th>Resolved</th><th>Action</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

async function refreshDashboard() {
  try {
    const [detections, stats] = await Promise.all([
      fetchJSON("/api/detections"),
      fetchJSON("/api/stats"),
    ]);
    renderMap(detections);
    renderStats(stats);
    renderAlerts(stats);
    renderSuggestions(detections);
    renderTable(detections);

    if (stats.alerts.length > 0) {
      uploadStatus.innerHTML = `<div class="alert error">${stats.alerts.length} high-priority alert(s) need immediate action.</div>`;
    }
  } catch (err) {
    uploadStatus.innerHTML = `<div class="alert error">Dashboard refresh failed: ${err.message}</div>`;
  }
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const imageInput = document.getElementById("imageInput");
  const file = imageInput.files[0];
  if (!file) {
    uploadStatus.innerHTML = `<div class="alert error">Please select an image file first.</div>`;
    return;
  }

  const formData = new FormData();
  formData.append("image", file);

  try {
    uploadStatus.textContent = "Processing image with AI model...";
    const payload = await fetchJSON("/api/upload", { method: "POST", body: formData });
    uploadStatus.innerHTML = `<p>${payload.message} (${payload.detections.length} items detected)</p>`;
    overlayPreview.src = payload.overlay_image;
    overlayPreview.style.display = "block";
    await refreshDashboard();
  } catch (err) {
    uploadStatus.innerHTML = `<div class="alert error">Upload failed: ${err.message}</div>`;
  }
});

document.getElementById("seedDemo").addEventListener("click", async () => {
  try {
    await fetchJSON("/api/seed-demo", { method: "POST" });
    await refreshDashboard();
  } catch (err) {
    uploadStatus.innerHTML = `<div class="alert error">Demo seed failed: ${err.message}</div>`;
  }
});

window.resolveDetection = async (id) => {
  try {
    await fetchJSON(`/api/resolve/${id}`, { method: "POST" });
    await refreshDashboard();
  } catch (err) {
    uploadStatus.innerHTML = `<div class="alert error">Resolve failed: ${err.message}</div>`;
  }
};

refreshDashboard();
setInterval(refreshDashboard, 30000);
