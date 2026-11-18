const API_BASE = "http://127.0.0.1:8000";


// ============================================
// LOAD DASHBOARD STATISTICS AND EVENTS
// ============================================

async function loadDashboard() {

    const connection = document.getElementById("connection");

    try {

        const response = await fetch("/api/dashboard-data");

        if (!response.ok) {
            throw new Error("Dashboard API connection failed");
        }

        const data = await response.json();

        connection.textContent = "● API Connected";
        connection.className = "status online";

        document.getElementById("total").textContent =
            data.total_events;

        document.getElementById("unknown").textContent =
            data.unknown_events;

        document.getElementById("authorized").textContent =
            data.authorized_events;

        document.getElementById("alerts").textContent =
            data.alert_events;

        const table = document.getElementById("events");

        table.replaceChildren();

        if (!data.events || data.events.length === 0) {

            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 6;
            cell.textContent = "No events recorded yet.";

            row.appendChild(cell);
            table.appendChild(row);

        } else {

            data.events.forEach(event => {

                const row = document.createElement("tr");

                let eventClass = "";

                if (event.event_type === "UNKNOWN_DETECTED") {
                    eventClass = "event-unknown";
                } else if (
                    event.event_type === "AUTHORIZED_DETECTED"
                ) {
                    eventClass = "event-authorized";
                } else if (
                    event.event_type === "UNKNOWN_ALERT"
                ) {
                    eventClass = "event-alert";
                }

                const values = [
                    event.id,
                    event.event_type,
                    event.person_name || "-",
                    event.track_id ?? "-",
                    event.timestamp || "-",
                    event.evidence_path || "-"
                ];

                values.forEach((value, index) => {

                    const cell = document.createElement("td");

                    cell.textContent = String(value);

                    if (index === 1) {
                        cell.className = eventClass;
                    }

                    row.appendChild(cell);

                });

                table.appendChild(row);

            });
        }

        document.getElementById("last-updated").textContent =
            "Last updated: " + new Date().toLocaleTimeString();

    } catch (error) {

        connection.textContent = "● API Disconnected";
        connection.className = "status offline";

        console.error("Dashboard error:", error);
    }
}


// ============================================
// LOAD CAMERA STATUS
// ============================================

async function loadCameraStatus() {

    const status = document.getElementById("camera-status");
    const message = document.getElementById("camera-message");

    try {

        const response = await fetch(
            `${API_BASE}/camera/status`
        );

        if (!response.ok) {
            throw new Error("Camera status unavailable");
        }

        const data = await response.json();

        status.textContent = data.camera;

        status.className =
            data.camera === "connected"
                ? "status online"
                : "status offline";

        message.textContent = data.message;

    } catch (error) {

        status.textContent = "Disconnected";
        status.className = "status offline";

        message.textContent =
            "Cannot connect to camera API.";

        console.error("Camera status error:", error);
    }
}


// ============================================
// LOAD EVIDENCE GALLERY
// ============================================

async function loadEvidence() {

    const gallery = document.getElementById("evidence-gallery");
    const count = document.getElementById("evidence-count");

    try {

        const response = await fetch(
            `${API_BASE}/evidence`
        );

        if (!response.ok) {
            throw new Error("Could not load evidence.");
        }

        const data = await response.json();

        const evidence = data.evidence || [];

        count.textContent =
            `${evidence.length} snapshots`;

        gallery.replaceChildren();

        if (evidence.length === 0) {

            const empty = document.createElement("div");

            empty.className = "gallery-message";

            empty.textContent =
                "No evidence snapshots saved yet. " +
                "An unknown face must remain continuously tracked " +
                "for 10 seconds before a snapshot is saved.";

            gallery.appendChild(empty);

            return;
        }

        evidence.forEach(item => {

            const card = document.createElement("article");

            card.className = "evidence-card";

            const imageURL =
                `${API_BASE}${item.image_url}`;

            // Evidence image
            const image = document.createElement("img");

            image.className = "evidence-image";
            image.src = imageURL;
            image.alt = `Unknown face evidence, track ${item.track_id}`;
            image.loading = "lazy";

            image.addEventListener("click", () => {
                openEvidencePreview(item, imageURL);
            });

            // Card information
            const info = document.createElement("div");

            info.className = "evidence-info";

            const tag = document.createElement("span");

            tag.className = "evidence-tag";
            tag.textContent = "UNKNOWN DETECTED";

            const heading = document.createElement("h3");

            heading.textContent =
                `Evidence #${item.id}`;

            const databaseID = document.createElement("p");

            databaseID.textContent =
                `Database Event ID: ${item.id}`;

            const trackID = document.createElement("p");

            trackID.textContent =
                `Face Track ID: ${item.track_id ?? "-"}`;

            const person = document.createElement("p");

            person.textContent =
                `Person: ${item.person_name || "UNKNOWN"}`;

            const timestamp = document.createElement("p");

            timestamp.textContent =
                `Time: ${item.timestamp || "-"}`;

            const similarity = document.createElement("p");

            similarity.textContent =
                `Similarity: ${
                    item.similarity == null
                        ? "-"
                        : Number(item.similarity).toFixed(3)
                }`;

            const download = document.createElement("a");

            download.className = "evidence-download";
            download.href = imageURL;
            download.download = `sentinelguard_evidence_${item.id}.jpg`;
            download.textContent = "Download snapshot";

            info.append(
                tag,
                heading,
                databaseID,
                trackID,
                person,
                timestamp,
                similarity,
                download
            );

            card.append(
                image,
                info
            );

            image.addEventListener("error", () => {
                image.alt = "Evidence image unavailable";
                image.style.opacity = "0.35";
            });

            gallery.appendChild(card);

        });

    } catch (error) {

        count.textContent = "Unavailable";

        gallery.replaceChildren();

        const message = document.createElement("div");

        message.className = "gallery-message";

        message.textContent =
            "Could not load evidence. Check that the API is running " +
            "and that the /evidence endpoint is available.";

        gallery.appendChild(message);

        console.error("Evidence gallery error:", error);
    }
}


// ============================================
// OPEN IMAGE PREVIEW
// ============================================

function openEvidencePreview(item, imageURL) {

    const modal = document.getElementById("image-modal");
    const image = document.getElementById("modal-image");
    const details = document.getElementById("modal-details");
    const download = document.getElementById("download-evidence");

    image.src = imageURL;

    details.textContent =
        `Database Event ID: ${item.id} | ` +
        `Track ID: ${item.track_id ?? "-"} | ` +
        `Person: ${item.person_name || "UNKNOWN"} | ` +
        `Timestamp: ${item.timestamp || "-"} | ` +
        `Similarity: ${
            item.similarity == null
                ? "-"
                : Number(item.similarity).toFixed(3)
        }`;

    download.href = imageURL;

    download.download =
        `sentinelguard_evidence_${item.id}.jpg`;

    modal.classList.add("visible");

    modal.setAttribute("aria-hidden", "false");
}


// ============================================
// CLOSE IMAGE PREVIEW
// ============================================

function closeEvidencePreview() {

    const modal = document.getElementById("image-modal");

    modal.classList.remove("visible");

    modal.setAttribute("aria-hidden", "true");

    document.getElementById("modal-image").src = "";
}


// ============================================
// REFRESH ALL DASHBOARD DATA
// ============================================

async function refreshDashboard() {

    await Promise.all([
        loadDashboard(),
        loadCameraStatus(),
        loadEvidence()
    ]);
}


// ============================================
// BUTTON EVENTS
// ============================================

document
    .getElementById("refresh-dashboard")
    .addEventListener("click", refreshDashboard);

document
    .getElementById("refresh-evidence")
    .addEventListener("click", loadEvidence);

document
    .getElementById("close-modal")
    .addEventListener("click", closeEvidencePreview);

document
    .getElementById("image-modal")
    .addEventListener("click", event => {

        if (event.target.id === "image-modal") {
            closeEvidencePreview();
        }

    });

document.addEventListener("keydown", event => {

    if (event.key === "Escape") {
        closeEvidencePreview();
    }

});


// ============================================
// INITIAL LOAD AND AUTOMATIC REFRESH
// ============================================

refreshDashboard();

setInterval(refreshDashboard, 5000);

setInterval(loadEvidence, 10000);