from flask import Flask, request, jsonify
import jwt
import datetime

app = Flask(__name__)

# In a real system: LDAP, Active Directory, or a proper user store
USERS = {
    "alice":   {"password": "alice123",   "role": "user",  "mfa": True},
    "bob":     {"password": "bob123",     "role": "admin", "mfa": True},
    "charlie": {"password": "charlie123", "role": "user",  "mfa": False},
}

with open("/certs/jwt_private.key", "r") as f:
    JWT_PRIVATE_KEY = f.read()
with open("/certs/jwt_public.key", "r") as f:
    JWT_PUBLIC_KEY = f.read()


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "identity-provider"})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = USERS.get(username)
    if not user or user["password"] != password:
        return jsonify({"error": "Invalid credentials"}), 401

    now = datetime.datetime.utcnow()
    payload = {
        "sub":  username,
        "role": user["role"],
        "mfa":  user["mfa"],
        "iat":  now,
        "exp":  now + datetime.timedelta(minutes=5),   # short-lived!
        "iss":  "zero-trust-idp",
    }
    token = jwt.encode(payload, JWT_PRIVATE_KEY, algorithm="RS256")
    return jsonify({"token": token, "expires_in": 300, "token_type": "Bearer"})


@app.route("/verify", methods=["POST"])
def verify():
    """Called by the PDP to verify a token cryptographically."""
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")
    try:
        payload = jwt.decode(token, JWT_PUBLIC_KEY, algorithms=["RS256"],
                             options={"verify_iss": True}, issuer="zero-trust-idp")
        return jsonify({"valid": True, "payload": payload})
    except jwt.ExpiredSignatureError:
        return jsonify({"valid": False, "error": "Token expired"}), 401
    except jwt.InvalidTokenError as e:
        return jsonify({"valid": False, "error": str(e)}), 401


@app.route("/public-key")
def public_key():
    return jsonify({"public_key": JWT_PUBLIC_KEY})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
