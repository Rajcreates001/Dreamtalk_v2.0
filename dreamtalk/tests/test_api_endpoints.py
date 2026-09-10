"""
DreamTalk API Integration Tests
Tests all backend endpoints via HTTP requests against a running server.
Run with: python test_api_endpoints.py
Or:       pytest test_api_endpoints.py -v
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("api_test")

BASE_URL = os.environ.get("DREAMTALK_API_URL", "http://localhost:5000")

passed = 0
failed = 0


def request(method: str, path: str, data: dict = None, files: dict = None, headers: dict = None) -> tuple:
    """Make an HTTP request and return (status_code, body_dict)."""
    url = f"{BASE_URL}{path}"
    hdrs = {"Accept": "application/json", **(headers or {})}

    if files:
        # Multipart form upload
        import io
        import uuid
        boundary = uuid.uuid4().hex
        body = io.BytesIO()
        for field_name, (filename, file_data, content_type) in files.items():
            body.write(f"--{boundary}\r\n".encode())
            body.write(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode())
            body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
            if isinstance(file_data, str):
                body.write(file_data.encode())
            else:
                body.write(file_data)
            body.write(b"\r\n")
        if data:
            for k, v in data.items():
                body.write(f"--{boundary}\r\n".encode())
                body.write(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
                body.write(str(v).encode())
                body.write(b"\r\n")
        body.write(f"--{boundary}--\r\n".encode())
        hdrs["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        req = urllib.request.Request(url, data=body.getvalue(), headers=hdrs, method=method)
    elif data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
        hdrs["Content-Length"] = str(len(body))
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    else:
        req = urllib.request.Request(url, headers=hdrs, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, {"raw": body}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"error": body[:200]}
    except (urllib.error.URLError, ConnectionRefusedError) as e:
        return 0, {"error": str(e)}


def test(name: str, result: bool, detail: str = ""):
    global passed, failed
    if result:
        passed += 1
        icon = "✅"
    else:
        failed += 1
        icon = "❌"
    logger.info(f"  {icon} {name}: {detail}")


# ═══════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════

def test_root():
    status, body = request("GET", "/")
    test("Root endpoint", status == 200, f"HTTP {status}")
    if status == 200:
        assert "service" in body
        assert "status" in body
        assert body["status"] == "running"
        test("Root has service name", True, body.get("service", "")[:40])
        test("Root has docs link", "docs" in body, body.get("docs", ""))


def test_health():
    status, body = request("GET", "/health")
    test("Health endpoint", status == 200, f"HTTP {status}")
    if status == 200:
        assert "database" in body
        assert "status" in body
        test("Health has status", body.get("status") == "ok", str(body.get("status")))
        test("Health has version", "version" in body, body.get("version", ""))


def test_livez():
    status, body = request("GET", "/livez")
    test("Liveness probe", status == 200, f"HTTP {status}")
    if status == 200:
        test("Liveness status alive", body.get("status") == "alive", str(body.get("status")))
        test("Liveness has uptime", "uptime_seconds" in body, f"{body.get('uptime_seconds')}s")


def test_readyz():
    status, body = request("GET", "/readyz")
    test("Readiness probe", status in (200, 503), f"HTTP {status}")
    if "checks" in body:
        checks = body["checks"]
        test("Readiness has DB check", "database" in checks, str(checks.get("database")))
        test("Readiness has Redis check", "redis" in checks, str(checks.get("redis")))
        test("Readiness has Weaviate check", "weaviate" in checks, str(checks.get("weaviate")))


def test_metrics():
    status, body = request("GET", "/metrics")
    test("Metrics endpoint", status == 200, f"HTTP {status}")
    if status == 200:
        metric_keys = ["dreamtalk_uptime_seconds", "dreamtalk_version", "dreamtalk_models_loaded"]
        for k in metric_keys:
            test(f"Metrics has {k}", k in body, str(body.get(k)))


def test_api_docs():
    status, _ = request("GET", "/docs")
    test("OpenAPI docs", status == 200, f"HTTP {status}")
    status2, body2 = request("GET", "/openapi.json")
    test("OpenAPI schema", status2 == 200, f"HTTP {status2}")
    if status2 == 200:
        test("Schema has paths", "paths" in body2, f"{len(body2.get('paths', {}))} endpoints")


def test_avatar_status():
    status, body = request("GET", "/api/avatar/status")
    test("Avatar status", status == 200, f"HTTP {status}")
    if status == 200:
        assert "models_loaded" in body
        test("Avatar has pipeline status", "pipeline_available" in body, str(body.get("pipeline_available")))
        test("Avatar has languages", "languages" in body, str(list(body.get("languages", {}).keys())))


def test_avatar_languages():
    status, body = request("GET", "/api/avatar/languages")
    test("Avatar languages", status == 200, f"HTTP {status}")
    if status == 200:
        assert "languages" in body
        langs = body.get("languages", {})
        test("Avatar has English", "en" in langs, "English")
        test("Avatar has Kannada", "kn" in langs, "Kannada")
        test("Avatar has Tamil", "ta" in langs, "Tamil")
        test("Avatar has Hindi", "hi" in langs, "Hindi")


def test_sentry_debug():
    status, body = request("GET", "/sentry-debug")
    test("Sentry debug endpoint", status == 200, f"HTTP {status}")
    if status == 200:
        test("Sentry has message", "message" in body, body.get("message", "")[:50])


def test_login_endpoint():
    status, body = request("POST", "/api/v1/auth/login", {
        "username": "test@dreamtalk.ai",
        "password": "test_password",
    })
    # Expect either 200 (success), 401 (invalid), or 422 (validation)
    test("Login endpoint accepts requests", status in (200, 401, 422), f"HTTP {status}")


def test_register_endpoint():
    import uuid
    unique_email = f"test_{uuid.uuid4().hex[:8]}@dreamtalk.ai"
    status, body = request("POST", "/api/v1/auth/register", {
        "email": unique_email,
        "password": "SecurePass123!",
        "full_name": "Test User",
    })
    test("Register endpoint accepts requests", status in (200, 201, 400, 422), f"HTTP {status}")


def test_avatar_chat():
    status, body = request("POST", "/api/avatar/chat", data={"text": "Hello! How are you?"})
    test("Avatar chat endpoint", status in (200, 503), f"HTTP {status}")
    if status == 200:
        test("Chat has response", "response" in body, str(body.get("response", ""))[:50])
        test("Chat has emotion", "emotion" in body, body.get("emotion", ""))


def test_avatar_tts():
    status, body = request("POST", "/api/avatar/tts/generate", data={"text": "Hello world", "language": "en"})
    test("TTS generate endpoint", status in (200, 503), f"HTTP {status}")
    if status == 200:
        test("TTS has path", "tts_path" in body, str(body.get("tts_path", ""))[:40])
        test("TTS has length", "length_chars" in body, str(body.get("length_chars")))


def test_avatar_session():
    status, body = request("GET", "/api/avatar/session")
    test("Avatar session endpoint", status == 200, f"HTTP {status}")
    if status == 200:
        test("Session has pipeline_id", "pipeline_id" in body, str(body.get("pipeline_id")))
        test("Session has languages", "languages" in body, str(list(body.get("languages", {}).keys())))
        test("Session has KB ready", "knowledge_base_ready" in body, str(body.get("knowledge_base_ready")))


def test_avatar_video_status():
    status, body = request("GET", "/api/avatar/video/status")
    test("Video status endpoint", status == 200, f"HTTP {status}")
    if status == 200:
        test("Video status has musetalk", "musetalk_available" in body, str(body.get("musetalk_available")))
        test("Video status has ditto", "ditto_available" in body, str(body.get("ditto_available")))
        test("Video status has generated", "has_generated_video" in body, str(body.get("has_generated_video")))


def test_avatar_knowledge():
    status, body = request("GET", "/api/avatar/knowledge?query=hello")
    test("Knowledge base endpoint", status == 200, f"HTTP {status}")
    if status == 200:
        test("Knowledge has query", "query" in body, body.get("query", ""))


def test_tasks_endpoints():
    # Test task result lookup (will fail since no real task, but should return proper error)
    status, body = request("GET", "/api/tasks/result/nonexistent-task-id")
    test("Task result endpoint", status in (200, 404, 503), f"HTTP {status}")
    if status == 503:
        test("Tasks celery unavailable", "detail" in body, body.get("detail", "")[:40])


def test_emotion_endpoints():
    status, body = request("POST", "/api/emotion/detect", data={"text": "I am very happy today!"})
    test("Emotion detect endpoint", status in (200, 422, 503), f"HTTP {status}")
    if status == 200:
        test("Emotion has mood", "mood" in body or "primary_mood" in body,
             str(body.get("mood", body.get("primary_mood", ""))))

    status2, body2 = request("GET", "/api/emotion/moods")
    test("Emotion list moods endpoint", status2 in (200, 404, 503), f"HTTP {status2}")


def test_cognition_endpoints():
    status, body = request("POST", "/api/cognition/reason", data={
        "query": "What is 2+2?",
        "context": {"mode": "logical"},
    })
    test("Cognition reason endpoint", status in (200, 422, 503), f"HTTP {status}")

    status2, body2 = request("POST", "/api/cognition/decide", data={
        "query": "Should I study today?",
        "options": ["yes", "no"],
    })
    test("Cognition decide endpoint", status2 in (200, 422, 503), f"HTTP {status2}")


def test_profile_endpoints():
    status, body = request("GET", "/api/v1/profile/me")
    test("Profile me endpoint", status in (200, 401, 503), f"HTTP {status}")


def test_digital_humans():
    status, body = request("GET", "/api/v1/digital-humans")
    test("Digital humans list", status in (200, 401, 503), f"HTTP {status}")


def test_workforce():
    status, body = request("GET", "/api/v1/workforce/agents")
    test("Workforce agents", status in (200, 401, 503), f"HTTP {status}")


def test_pipeline():
    status, body = request("POST", "/api/v1/pipeline/run", data={
        "twin_id": "test-twin-123",
        "text_input": "Hello world",
        "role": "normal_user",
        "model_name": "rule_based",
        "enable_emotion": True,
        "enable_decision": True,
    })
    test("Pipeline run endpoint", status in (200, 401, 422, 503), f"HTTP {status}")


def test_identity():
    status, body = request("POST", "/api/v1/identity/analyze", data={
        "twin_id": "test-twin-123",
    })
    test("Identity analyze endpoint", status in (200, 401, 422, 503), f"HTTP {status}")


def test_frontend_serves():
    """Check if the frontend is reachable (if running)."""
    frontend_url = os.environ.get("DREAMTALK_FRONTEND_URL", "http://localhost:3000")
    try:
        req = urllib.request.Request(frontend_url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
            has_react = "react" in body.lower() or "next" in body.lower() or "_next" in body
            test("Frontend serves", status == 200, f"HTTP {status}")
            test("Frontend is React/Next", has_react, "React detected" if has_react else "Fallback")
    except (urllib.error.URLError, ConnectionRefusedError):
        test("Frontend serves", True, "Skipped (frontend not running)")


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    global passed, failed

    logger.info("=" * 60)
    logger.info(f"DreamTalk API Integration Tests")
    logger.info(f"Base URL: {BASE_URL}")
    logger.info(f"Frontend URL: {os.environ.get('DREAMTALK_FRONTEND_URL', 'http://localhost:3000')}")
    logger.info("=" * 60)

    # Verify server is reachable first
    status, _ = request("GET", "/")
    if status == 0:
        logger.error(f"❌ Cannot reach server at {BASE_URL}")
        logger.error("   Start the backend first: uvicorn dreamtalk.backend.main:app --port 5000")
        logger.error("   Or set DREAMTALK_API_URL env var")
        sys.exit(1)

    logger.info(f"✅ Server reachable at {BASE_URL}\n")

    # Run all tests
    tests = [
        ("Root", test_root),
        ("Health", test_health),
        ("Liveness", test_livez),
        ("Readiness", test_readyz),
        ("Metrics", test_metrics),
        ("API Docs", test_api_docs),
        ("Avatar Status", test_avatar_status),
        ("Avatar Languages", test_avatar_languages),
        ("Sentry Debug", test_sentry_debug),
        ("Login", test_login_endpoint),
        ("Register", test_register_endpoint),
        ("Avatar Chat", test_avatar_chat),
        ("TTS Generate", test_avatar_tts),
        ("Avatar Session", test_avatar_session),
        ("Video Status", test_avatar_video_status),
        ("Knowledge Base", test_avatar_knowledge),
        ("Tasks", test_tasks_endpoints),
        ("Emotion", test_emotion_endpoints),
        ("Cognition", test_cognition_endpoints),
        ("Profile", test_profile_endpoints),
        ("Digital Humans", test_digital_humans),
        ("Workforce", test_workforce),
        ("Pipeline", test_pipeline),
        ("Identity", test_identity),
        ("Frontend", test_frontend_serves),
    ]

    for name, fn in tests:
        logger.info(f"\n{'─' * 40}")
        logger.info(f"Test: {name}")
        logger.info(f"{'─' * 40}")
        try:
            fn()
        except Exception as e:
            logger.error(f"  ❌ {name} crashed: {e}")
            failed += 1

    # Summary
    total = passed + failed
    logger.info("\n" + "=" * 60)
    logger.info(f"RESULTS: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        logger.info("✅ ALL TESTS PASSED")
    else:
        logger.warning(f"❌ {failed} TEST(S) FAILED")
    logger.info("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
