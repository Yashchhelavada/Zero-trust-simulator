from flask import Flask, request, jsonify
import jwt, json, sqlite3, re, datetime, os

app = Flask(__name__)

with open("/certs/jwt_public.key", "r") as f:
    JWT_PUBLIC_KEY = f.read()

with open("/app/policies.json", "r") as f:
    POLICIES = json.load(f)["policies"]

DB_PATH = "/data/decisions.db"


def init_db():
    os.makedirs("/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT NOT NULL,
            username  TEXT NOT NULL,
            role      TEXT NOT NULL,
            resource  TEXT NOT NULL,
            method    TEXT NOT NULL,
            decision  TEXT NOT NULL,
            reason    TEXT NOT NULL,
            client_ip TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_decision(username, role, resource, method, decision, reason, client_ip):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO decisions (ts,username,role,resource,method,decision,reason,client_ip) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (datetime.datetime.utcnow().isoformat(), username, role,
         resource, method, decision, reason, client_ip)
    )
    conn.commit()
    conn.close()


def find_policy(resource, method):
    for p in POLICIES:
        if p["resource"] == resource and method in p["methods"]:
            return p
    return None


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "policy-decision-point"})


@app.route("/authorize", methods=["POST"])
def authorize():
    """
    Receives: { token, resource, method, client_ip }
    Returns:  { decision: "allow|deny", reason: "..." }

    This is called on EVERY request to the resource server.
    Never trust. Always verify.
    """
    data = request.get_json(silent=True) or {}
    token     = data.get("token", "")
    resource  = data.get("resource", "")
    method    = data.get("method", "GET")
    client_ip = data.get("client_ip", "unknown")

    # Step 1: Verify token cryptographically
    try:
        payload = jwt.decode(token, JWT_PUBLIC_KEY, algorithms=["RS256"],
                             options={"verify_iss": True}, issuer="zero-trust-idp")
    except jwt.ExpiredSignatureError:
        log_decision("unknown", "none", resource, method, "DENY",
                     "Token expired", client_ip)
        return jsonify({"decision": "DENY", "reason": "Token expired"}), 403
    except jwt.InvalidTokenError as e:
        log_decision("unknown", "none", resource, method, "DENY",
                     f"Invalid token: {e}", client_ip)
        return jsonify({"decision": "DENY", "reason": f"Invalid token: {e}"}), 403

    username = payload.get("sub", "unknown")
    role     = payload.get("role", "none")

    # Step 2: Find matching policy
    policy = find_policy(resource, method)
    if not policy:
        log_decision(username, role, resource, method, "DENY",
                     "No policy found for this resource", client_ip)
        return jsonify({"decision": "DENY", "reason": "No policy found for resource"}), 403

    # Step 3: Evaluate role against policy
    if role not in policy["required_roles"]:
        reason = f"Role '{role}' not in required roles {policy['required_roles']}"
        log_decision(username, role, resource, method, "DENY", reason, client_ip)
        return jsonify({"decision": "DENY", "reason": reason}), 403

    # Step 4: ALLOW
    reason = f"Role '{role}' satisfies policy '{policy['id']}'"
    log_decision(username, role, resource, method, "ALLOW", reason, client_ip)
    return jsonify({
        "decision": "ALLOW",
        "reason":   reason,
        "username": username,
        "role":     role,
    })


@app.route("/decisions")
def decisions():
    """Dashboard reads decisions from shared DB, but PDP also exposes them via API."""
    limit = int(request.args.get("limit", 50))
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
