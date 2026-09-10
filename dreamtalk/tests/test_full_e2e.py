#!/usr/bin/env python3
"""DreamTalk Full E2E API Test Suite - Corrected Routes"""
import json, sys, time, urllib.request, urllib.error, ssl

BASE = "http://127.0.0.1:5001"
PASS = 0; FAIL = 0
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def req(method, url, data=None, headers=None, timeout=30):
    hdrs = {"Content-Type": "application/json"}
    if headers: hdrs.update(headers)
    body = json.dumps(data).encode() if data else None
    try:
        r = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        with urllib.request.urlopen(r, timeout=timeout, context=ctx) as resp:
            ct = resp.read().decode()
            return resp.status, json.loads(ct) if ct else {}
    except urllib.error.HTTPError as e:
        ct = e.read().decode()
        try: return e.code, json.loads(ct)
        except: return e.code, {"raw": ct[:200]}
    except Exception as e:
        return 0, {"error": str(e)}

def test(name, method, path, data=None, headers=None, expect_status=None, timeout=30):
    global PASS, FAIL
    url = path if path.startswith("http") else BASE + path
    status, body = req(method, url, data, headers, timeout)
    if expect_status and status != expect_status:
        print(f"  FAIL {name} -- Expected {expect_status}, got {status}")
        FAIL += 1; return body
    else:
        print(f"  OK   {name} -- {status}")
        PASS += 1; return body

print("=" * 60)
print("DREAMTALK FULL E2E API TEST SUITE")
print("=" * 60)

# 1. HEALTH
print("\n[1] INFRASTRUCTURE HEALTH")
test("Backend health", "GET", "/health", expect_status=200)
test("Pipeline health", "GET", "/pipeline/health", expect_status=200)
test("Metrics endpoint", "GET", "/metrics", expect_status=200)

# 2. AUTH
print("\n[2] AUTHENTICATION")
r = test("Signup", "POST", "/api/v1/auth/signup", {
    "email": f"e2e_{int(time.time())}@dreamtalk.ai",
    "password": "SecureP@ssw0rd!",
    "full_name": "E2E Test", "role": "personal"
}, expect_status=200)
token = r.get("tokens", {}).get("access_token", "")
uid = r.get("user", {}).get("id", "")
H = {"Authorization": f"Bearer {token}"} if token else {}
print(f"     Token len={len(token)}, User={uid}")

test("Login", "POST", "/api/v1/auth/login",
     {"email": f"e2e_{int(time.time())}@dreamtalk.ai", "password": "wrong"},
     expect_status=401)

# Re-login with correct creds (we need to know the email we just created)
# The signup response has the email
email = r.get("user", {}).get("email", "")
lr = test("Login correct", "POST", "/api/v1/auth/login",
     {"email": email, "password": "SecureP@ssw0rd!"}, expect_status=200)
ltoken = lr.get("tokens", {}).get("access_token", "")
if ltoken: H = {"Authorization": f"Bearer {ltoken}"}

test("Get profile", "GET", "/api/v1/auth/me", headers=H, expect_status=200)
rt = lr.get("tokens", {}).get("refresh_token", "")
test("Refresh token", "POST", "/api/v1/auth/refresh", {"refresh_token": rt}, expect_status=200)

# 3. DIGITAL TWINS
print("\n[3] DIGITAL TWINS")
tw = test("Create twin", "POST", "/api/v1/digital-twins", {
    "name": "E2E Twin", "description": "Test", "category": "personal", "role": "personal"
}, headers=H, expect_status=201)
tid = tw.get("id", "")
print(f"     Twin ID: {tid}")

test("List twins", "GET", "/api/v1/digital-twins/", headers=H, expect_status=200)
if tid:
    test("Get twin", "GET", f"/api/v1/digital-twins/{tid}", headers=H, expect_status=200)
    test("Twin status", "GET", f"/api/v1/digital-twins/{tid}/status", headers=H, expect_status=200)
    test("Twin full status", "GET", f"/api/v1/digital-twins/{tid}/full-status", headers=H, expect_status=200)
    test("Twin personality", "GET", f"/api/v1/digital-twins/{tid}/personality", headers=H, expect_status=200)
    test("Twin pipeline status", "GET", f"/api/v1/digital-twins/{tid}/pipeline/status", headers=H, expect_status=200)

# 4. CHAT
print("\n[4] BRAIN / CHAT")
r = test("Chat happy", "POST", "/api/chat/public",
    {"message": "I'm so happy today!", "twin_id": tid or "test"}, expect_status=200, timeout=120)
print(f"     Emotion: {r.get('emotion','?')}, Model: {r.get('brain_model','?')}")

test("Chat sad", "POST", "/api/chat/public",
    {"message": "I feel sad", "twin_id": tid or "test"}, expect_status=200, timeout=120)

test("Chat neutral", "POST", "/api/chat/public",
    {"message": "What is 2+2?", "twin_id": tid or "test"}, expect_status=200, timeout=120)

# 5. TTS
print("\n[5] TTS")
# TTS uses form data
import urllib.parse
tts_url = BASE + "/api/avatar/tts/generate"
tts_data = urllib.parse.urlencode({"text": "Hello from DreamTalk!", "voice": "af_heart"}).encode()
try:
    r = urllib.request.Request(tts_url, data=tts_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(r, timeout=60, context=ctx) as resp:
        ct = resp.read().decode()
        result = json.loads(ct) if ct else {}
        print(f"  OK   TTS generate -- {resp.status}")
        PASS += 1
except urllib.error.HTTPError as e:
    print(f"  FAIL TTS generate -- {e.code}: {e.read().decode()[:100]}")
    FAIL += 1
except Exception as e:
    print(f"  FAIL TTS generate -- {e}")
    FAIL += 1

test("IndicF5 status", "GET", "/api/avatar/tts/indicf5/status", expect_status=200)
test("IndicF5 languages", "GET", "/api/avatar/tts/indicf5/languages", expect_status=200)

# 6. VOICE
print("\n[6] VOICE")
test("Voice engines", "GET", "/api/v1/voice/engines", expect_status=200)
test("Voice status", "GET", "/api/v1/voice/status", expect_status=200)
test("Voice voices", "GET", "/api/v1/voice/voices", expect_status=200)

# 7. AVATAR
print("\n[7] AVATAR")
test("Avatar status", "GET", "/api/avatar/status", expect_status=200)
test("Avatar languages", "GET", "/api/avatar/languages", expect_status=200)
test("Avatar knowledge", "GET", "/api/avatar/knowledge", expect_status=200)

# 8. EMOTION
print("\n[8] EMOTION")
test("Emotion health", "GET", "/emotion/health", expect_status=200)
test("Emotion state", "GET", "/emotion/state", expect_status=200)
test("Emotion RL state", "GET", "/emotion/rl_state", expect_status=200)
test("Emotion memory", "GET", "/emotion/memory", expect_status=200)

# 9. COGNITION
print("\n[9] COGNITION")
test("Cognition health", "GET", "/cognition/health", expect_status=200)
test("Cognition reasoners", "GET", "/cognition/reasoners", expect_status=200)

# 10. ANALYTICS
print("\n[10] ANALYTICS")
test("Analytics emotions", "GET", "/analytics/emotions", expect_status=200)
test("Analytics brain", "GET", "/analytics/brain", expect_status=200)
test("Analytics stats", "GET", "/analytics/stats", expect_status=200)

# 11. DIGITAL HUMANS
print("\n[11] DIGITAL HUMANS")
test("List digital humans", "GET", "/api/v1/digital-humans", headers=H, expect_status=200)

# 12. WORKFORCE
print("\n[12] WORKFORCE")
test("Workforce orgs", "GET", "/api/v1/workforce/organizations", headers=H, expect_status=200)

# 13. IDENTITY
print("\n[13] IDENTITY")
test("Identity by user", "GET", "/api/v1/identity/by-user", headers=H, expect_status=200)

# 14. PIPELINE
print("\n[14] PIPELINE")
test("Pipeline run", "POST", "/api/v1/pipeline/run", {"twin_id": tid or "test", "input_text": "hello"}, headers=H, expect_status=200)

# 15. FRONTEND (direct curl, not through test framework)
print("\n[15] FRONTEND")
import subprocess
for page in ["/", "/conversations", "/voice-cloning", "/avatar-studio", "/digital-brain", "/analytics"]:
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--connect-timeout", "5",
             f"http://127.0.0.1:4000{page}"],
            capture_output=True, text=True, timeout=10
        )
        code = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        if code == 200:
            print(f"  OK   Frontend {page} -- {code}")
            PASS += 1
        else:
            print(f"  FAIL Frontend {page} -- {code}")
            FAIL += 1
    except Exception as e:
        print(f"  FAIL Frontend {page} -- {e}")
        FAIL += 1

# RESULTS
print("\n" + "=" * 60)
total = PASS + FAIL
pct = PASS * 100 // total if total else 0
print(f"RESULTS: {PASS}/{total} passed ({pct}%)")
if FAIL:
    print(f"FAILED: {FAIL} tests")
else:
    print("ALL TESTS PASSED!")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
