
from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

API_URL = "http://127.0.0.1:8000"


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/api/dashboard-data")
def dashboard_data():
    try:
        stats_response = requests.get(
            f"{API_URL}/stats",
            timeout=5
        )

        events_response = requests.get(
            f"{API_URL}/events",
            params={"page": 1, "page_size": 100},
            timeout=5
        )

        stats_response.raise_for_status()
        events_response.raise_for_status()

        stats = stats_response.json()
        events_data = events_response.json()

        events = events_data.get("events", [])
        counts = stats.get("event_counts", {})

        return jsonify({
            "connected": True,
            "total_events": stats.get("total_events", 0),
            "unknown_events": counts.get("UNKNOWN_DETECTED", 0),
            "authorized_events": counts.get("AUTHORIZED_DETECTED", 0),
            "alert_events": counts.get("UNKNOWN_ALERT", 0),
            "system_events": counts.get("SYSTEM", 0),
            "events": events
        })

    except requests.RequestException as error:
        return jsonify({
            "connected": False,
            "error": str(error)
        }), 503


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
