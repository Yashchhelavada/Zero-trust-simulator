from flask import Flask, render_template, jsonify
import sqlite3, requests as http_client

app = Flask(__name__)
DB_PATH = "/data/decisions.db"
PDP_URL = "https://pdp:5001"
CA_CERT = "/certs/ca.crt"
DASH_CERT = ("/certs/dashboard.crt", "/certs/dashboard.key")

SERVICES = {
    "idp":      "https://idp:5000/health",
    "pdp":      "https://pdp:5001/health",
    "resource": "https://resource:5002/health",
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/decisions")
def api_decisions():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM decisions ORDER BY id DESC LIMIT 100"
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify([])


@app.route("/api/stats")
def api_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        total   = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        allowed = conn.execute("SELECT COUNT(*) FROM decisions WHERE decision='ALLOW'").fetchone()[0]
        denied  = conn.execute("SELECT COUNT(*) FROM decisions WHERE decision='DENY'").fetchone()[0]
        top_user = conn.execute(
            "SELECT username, COUNT(*) c FROM decisions GROUP BY username ORDER BY c DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return jsonify({
            "total": total, "allowed": allowed, "denied": denied,
            "allow_rate": round(allowed / total * 100, 1) if total else 0,
            "top_user": top_user[0] if top_user else "—"
        })
    except Exception:
        return jsonify({"total": 0, "allowed": 0, "denied": 0,
                        "allow_rate": 0, "top_user": "—"})


@app.route("/api/health")
def api_health():
    status = {}
    for name, url in SERVICES.items():
        try:
            r = http_client.get(url, cert=DASH_CERT, verify=CA_CERT, timeout=2)
            status[name] = "online" if r.status_code == 200 else "degraded"
        except Exception:
            status[name] = "offline"
    status["dashboard"] = "online"
    return jsonify(status)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
