from flask import Flask, request, jsonify
import requests as http_client

app = Flask(__name__)

PDP_URL      = "https://pdp:5001/authorize"
PDP_CERT     = ("/certs/resource.crt", "/certs/resource.key")  # client cert for mTLS
CA_CERT      = "/certs/ca.crt"

# Simulated protected resources
RESOURCES = {
    "/files/report.txt":  "Q3 Revenue: $4.2M. EBITDA: $1.1M. See CFO for details.",
    "/files/secret.txt":  "[CLASSIFIED] Project Nighthawk — acquisition target: Acme Corp.",
    "/files/public.txt":  "Welcome to Zero Trust Corp. This file is readable by all staff.",
    "/admin/users":       '[{"id":1,"user":"alice","role":"user"},{"id":2,"user":"bob","role":"admin"}]',
}


def call_pdp(token, resource, method, client_ip):
    """Ask the PDP for an access decision. Presents mTLS cert."""
    try:
        resp = http_client.post(
            PDP_URL,
            json={"token": token, "resource": resource,
                  "method": method, "client_ip": client_ip},
            cert=PDP_CERT,
            verify=CA_CERT,
            timeout=5,
        )
        return resp.json()
    except Exception as e:
        return {"decision": "DENY", "reason": f"PDP unreachable: {e}"}


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "resource-server"})


@app.route("/files/<path:filename>", methods=["GET"])
def get_file(filename):
    return handle_request(f"/files/{filename}")


@app.route("/admin/<path:subpath>", methods=["GET"])
def admin(subpath):
    return handle_request(f"/admin/{subpath}")


def handle_request(resource):
    # Extract Bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or malformed Authorization header"}), 401

    token     = auth_header[7:]
    client_ip = request.remote_addr

    # Ask the PDP — every single time, not cached
    result = call_pdp(token, resource, request.method, client_ip)

    if result.get("decision") != "ALLOW":
        return jsonify({
            "error":  "Access denied",
            "reason": result.get("reason", "Policy denied request"),
        }), 403

    # Serve the resource
    content = RESOURCES.get(resource)
    if content is None:
        return jsonify({"error": "Resource not found"}), 404

    return jsonify({
        "resource": resource,
        "content":  content,
        "served_to": result.get("username"),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
