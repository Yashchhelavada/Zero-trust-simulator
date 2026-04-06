import requests, json, time, sys

RESOURCE_URL = "https://resource:5002"
IDP_URL      = "https://idp:5000"
CA_CERT      = "/certs/ca.crt"

GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW= "\033[93m"
BLUE  = "\033[94m"
BOLD  = "\033[1m"
RESET = "\033[0m"

def banner(text):
    print(f"\n{BOLD}{BLUE}{'═'*60}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'═'*60}{RESET}")

def result(label, status_code, body, expect_denied=True):
    blocked = status_code in (401, 403)
    icon    = f"{GREEN}[BLOCKED ✓]" if blocked == expect_denied else f"{RED}[BYPASSED ✗]"
    print(f"  {icon}{RESET}  HTTP {status_code}")
    if isinstance(body, dict):
        print(f"  Response : {body.get('error') or body.get('content') or body}")
    time.sleep(0.5)

def get_token(username, password):
    r = requests.post(f"{IDP_URL}/login",
                      json={"username": username, "password": password},
                      verify=CA_CERT)
    return r.json().get("token", "")

def access(token, path, expected_block=True):
    r = requests.get(
        f"{RESOURCE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"} if token else {},
        verify=CA_CERT,
    )
    result(path, r.status_code, r.json(), expect_denied=expected_block)
    return r.status_code

# Wait for services to be ready
time.sleep(3)

banner("ATTACK SCENARIO 1 — No token (unauthenticated access)")
print(f"  Target   : /files/report.txt")
print(f"  Strategy : Access protected resource with no Bearer token")
access("", "/files/report.txt", expected_block=True)

banner("ATTACK SCENARIO 2 — Expired token")
print(f"  Target   : /files/report.txt")
print(f"  Strategy : Replay a hardcoded expired JWT")
EXPIRED_TOKEN = (
    "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJhbGljZSIsInJvbGUiOiJ1c2VyIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjE2MDAwMDM2MDB9."
    "invalidsignature"
)
access(EXPIRED_TOKEN, "/files/report.txt", expected_block=True)

banner("ATTACK SCENARIO 3 — Privilege escalation (user accessing admin resource)")
print(f"  Target   : /admin/users  (admin-only)")
print(f"  Strategy : Log in as 'alice' (role=user) and try admin endpoint")
alice_token = get_token("alice", "alice123")
print(f"  Token    : Alice's valid token (role=user)")
access(alice_token, "/admin/users", expected_block=True)

banner("ATTACK SCENARIO 4 — Forged token (tampered signature)")
print(f"  Target   : /files/secret.txt")
print(f"  Strategy : Modify a valid JWT payload to claim role=admin, break signature")
import base64
# Decode alice's token, change role to admin, re-encode with broken signature
parts = alice_token.split(".")
forged_payload = base64.urlsafe_b64encode(
    json.dumps({"sub": "alice", "role": "admin", "iss": "zero-trust-idp",
                "exp": 9999999999}).encode()
).rstrip(b"=").decode()
forged_token = f"{parts[0]}.{forged_payload}.INVALIDSIGNATURE"
print(f"  Token    : Forged with role=admin (invalid signature)")
access(forged_token, "/files/secret.txt", expected_block=True)

banner("ATTACK SCENARIO 5 — Legitimate access (everything correct)")
print(f"  Target   : /files/report.txt  (user-accessible)")
print(f"  Strategy : Log in as 'alice', access a resource her role permits")
access(alice_token, "/files/report.txt", expected_block=False)

print(f"\n{BOLD}{GREEN}Demo complete. Check the dashboard at https://localhost:8443{RESET}\n")
