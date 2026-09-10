import os
import sys
import re
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

_import_trace = []
def _log_import(msg):
    _import_trace.append(f"{len(_import_trace)}: {msg}")

_log_import("start main.py import")

from dotenv import load_dotenv
from pathlib import Path
# .env loading order (override=False = first-loaded wins):
# 1. dreamtalk/.env (local defaults: DB_HOST=127.0.0.1, etc.)
# 2. dreamtalk/backend/.env (Docker overrides: DB_HOST=postgres, etc.)
# because override=False, the FIRST file loaded (dreamtalk/.env) has highest priority.
# This ensures local dev always works regardless of what backend/.env contains.
_base = Path(__file__).resolve().parent.parent  # dreamtalk/
load_dotenv(_base / '.env', override=False)                     # Loaded first -> highest priority (local)
load_dotenv(_base / 'backend' / '.env', override=False)          # Loaded second -> can't override local
_log_import("load_dotenv done")

# ── sys.path setup ──────────────────────────────────────────────────────
# Only add the parent (Dreamtalk-Integrated/) to sys.path, NOT the project root (dreamtalk/).
# Adding the project root creates namespace conflicts (e.g., media/ gets found as a top-level
# module instead of dreamtalk.media). Also remove the CWD if it's dreamtalk/ to avoid conflicts
# when running `uvicorn dreamtalk.backend.main:app` directly from the dreamtalk/ directory.
_here = str(Path(__file__).resolve().parent.parent)  # dreamtalk/
_sys_parent = str(Path(__file__).resolve().parent.parent.parent)  # Dreamtalk-Integrated/

# Remove project root from sys.path if present
sys.path = [p for p in sys.path if os.path.abspath(p) != os.path.abspath(_here)]

if _sys_parent not in sys.path:
    sys.path.insert(0, _sys_parent)
_log_import("sys.path done")

# ── Platform-specific torch fixes ────────────────────────────────────
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
if sys.platform == "win32":
    try:
        _torch_lib = None
        try:
            import torch as _torch
            _torch_lib = str(Path(_torch.__file__).resolve().parent / "lib")
            del _torch
        except (ImportError, OSError):
            _site_pkg = Path(sys.prefix) / "Lib" / "site-packages" / "torch" / "lib"
            if _site_pkg.exists():
                _torch_lib = str(_site_pkg)
        if _torch_lib:
            if _torch_lib not in os.environ.get("PATH", ""):
                os.environ["PATH"] = _torch_lib + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(_torch_lib)
                except Exception:
                    pass
    except Exception:
        pass  # Non-fatal
_log_import("torch fix done")

from fastapi import FastAPI, Request
_log_import("fastapi done")
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
_log_import("fastapi submodules done")

from dreamtalk.backend.db.database import close_pool, get_pool, execute
_log_import("database done")
from dreamtalk.backend.db.auto_seed import auto_seed, auto_seed_identities, auto_seed_digital_twins, auto_seed_organizations
_log_import("auto_seed done")
from dreamtalk.backend.api.v1.endpoints.voice import router as voice_router
_log_import("voice done")
from dreamtalk.backend.api.v1.endpoints.chat import router as chat_router
_log_import("chat done")
from dreamtalk.backend.api.v1.endpoints.auth import router as auth_router
_log_import("auth done")
from dreamtalk.backend.api.v1.endpoints.profile import router as profile_router
_log_import("profile done")
from dreamtalk.backend.api.v1.endpoints.digital_humans import router as dh_router
_log_import("dh done")
from dreamtalk.backend.api.v1.endpoints.identity import router as identity_router
_log_import("identity done")
from dreamtalk.backend.api.v1.endpoints.digital_twins import router as digital_twins_router
_log_import("digital_twins done")
from dreamtalk.backend.api.v1.endpoints.workforce import router as workforce_router
_log_import("workforce done")
from dreamtalk.backend.api.v1.endpoints.pipeline import router as pipeline_router
_log_import("pipeline done")
from dreamtalk.backend.api.v1.endpoints.avatar import router as avatar_router
_log_import("avatar done")
from dreamtalk.backend.api.v1.endpoints.tasks import router as tasks_router
_log_import("tasks done")
from dreamtalk.emotion.api.emotion_router import router as emotion_router
_log_import("emotion done")
from dreamtalk.cognition.api.cognition_router import router as cognition_router
_log_import("cognition done")
from dreamtalk.digital_twin.personality import PersonalityEngine
_log_import("personality done")
from dreamtalk.digital_twin.learning_orchestrator import LearningOrchestrator
_log_import("learning_orch done")
from dreamtalk.workforce.org_memory import OrgMemory
_log_import("org_memory done")
logger = logging.getLogger("dreamtalk.main")

# ── Sentry Error Tracking ─────────────────────────────────────────────
_sentry_initialized = False
def init_sentry():
    global _sentry_initialized
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        logger.info("Sentry not configured (no SENTRY_DSN env var)")
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
            ],
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            profiles_sample_rate=float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.05")),
            environment=os.environ.get("DREAMTALK_ENV", "development"),
            release="dreamtalk@v0.5.0",
            send_default_pii=False,
        )
        _sentry_initialized = True
        logger.info("Sentry error tracking initialized")
    except ImportError:
        logger.info("Sentry SDK not installed — skipping")
    except Exception as e:
        logger.warning(f"Sentry init failed: {e}")


# ── Celery Integration ────────────────────────────────────────────────
_celery_app = None
try:
    from dreamtalk.backend.celery_app import celery_app as _celery_app
    logger.info("Celery integration loaded")
except Exception as e:
    logger.debug(f"Celery not available: {e}")
_log_import("celery done")

# ── Redis Cache ───────────────────────────────────────────────────────
_redis_available = False
try:
    from dreamtalk.backend.services import redis_cache
    _redis_available = True
except Exception:
    _redis_available = False
_log_import("redis done")

# ── Weaviate ──────────────────────────────────────────────────────────
_weaviate_available = False
try:
    from dreamtalk.backend.services import weaviate_client
    _weaviate_available = True
except Exception:
    _weaviate_available = False
_log_import("weaviate done")

_schema_applied = False


async def apply_schema():
    global _schema_applied
    if _schema_applied:
        return
    _schema_applied = True

    base = Path(__file__).resolve().parent / "db"

    def _make_idempotent(sql: str) -> str:
        sql = re.sub(r'\bCREATE TABLE (?!IF NOT EXISTS\b)', 'CREATE TABLE IF NOT EXISTS ', sql)
        sql = re.sub(r'\bCREATE INDEX (?!IF NOT EXISTS\b)', 'CREATE INDEX IF NOT EXISTS ', sql)
        def _wrap_enum(m):
            name = m.group(1)
            vals = m.group(2)
            return f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({vals}); EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        sql = re.sub(r'CREATE TYPE (\w+) AS ENUM \(([^)]+)\);', _wrap_enum, sql)
        sql = re.sub(r'CREATE TRIGGER IF NOT EXISTS ', 'CREATE TRIGGER ', sql)
        sql = re.sub(
            r'CREATE TRIGGER \w+.*?EXECUTE FUNCTION update_updated_at\(\);',
            lambda m: f"DO $$ BEGIN {m.group(0)} EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            sql, flags=re.DOTALL,
        )
        return sql

    pool = await get_pool()
    async with pool.acquire() as conn:
        for fname in ("schema.sql", "schema_v2.sql"):
            path = base / fname
            if not path.exists():
                logger.warning("Schema file not found: %s", path)
                continue
            idempotent = _make_idempotent(path.read_text(encoding="utf-8"))
            try:
                await conn.execute(idempotent)
                logger.info("Applied %s", fname)
            except Exception as e:
                logger.warning("Schema apply error for %s: %s", fname, str(e)[:120])
                for block in idempotent.split('\n\n'):
                    block = block.strip()
                    if block and not block.startswith('--'):
                        try:
                            await conn.execute(block)
                        except Exception:
                            pass


async def auto_seed_v2():
    await PersonalityEngine.ensure_table()
    await LearningOrchestrator.ensure_tables()
    await OrgMemory.ensure_table()
    pr_sql = """
    CREATE TABLE IF NOT EXISTS pipeline_results (
        id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        pipeline_id     VARCHAR(64) NOT NULL,
        twin_id         VARCHAR(64),
        step_name       VARCHAR(50),
        result_type     VARCHAR(50),
        result_data     JSONB DEFAULT '{}',
        created_at      TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_pipeline_results_pipeline ON pipeline_results(pipeline_id);
    CREATE INDEX IF NOT EXISTS idx_pipeline_results_twin ON pipeline_results(twin_id);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_pipeline_results_unique ON pipeline_results(pipeline_id, step_name, result_type);
    """
    await execute(pr_sql)

    sql = """
    CREATE TABLE IF NOT EXISTS media_assets (
        id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        twin_id         UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
        user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        category        VARCHAR(50) NOT NULL,
        sub_category    VARCHAR(50) NOT NULL,
        filename        VARCHAR(512) NOT NULL,
        file_path       VARCHAR(1024) NOT NULL,
        file_size       BIGINT DEFAULT 0,
        mime_type       VARCHAR(127),
        checksum        VARCHAR(64),
        is_original     BOOLEAN DEFAULT TRUE,
        version         INTEGER DEFAULT 1,
        processing_status VARCHAR(30) DEFAULT 'stored',
        metadata        JSONB DEFAULT '{}',
        created_at      TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_media_assets_twin ON media_assets(twin_id);
    CREATE INDEX IF NOT EXISTS idx_media_assets_category ON media_assets(twin_id, category);
    """
    await execute(sql)


async def load_avatar_models():
    try:
        from dreamtalk.backend.api.v1.endpoints.avatar import load_all_models
        await load_all_models()
    except Exception as e:
        logger.warning(f"Could not load avatar models: {e}")


async def safe_db_init():
    pool = None
    try:
        pool = await get_pool()
        await apply_schema()
        await auto_seed(pool)
        await auto_seed_identities(pool)
        await auto_seed_digital_twins(pool)
        await auto_seed_organizations(pool)
        await auto_seed_v2()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.warning(f"Database init skipped (non-fatal): {e}")
        logger.warning("Server will run without persistence -- pipeline results won't save")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_sentry()
    await safe_db_init()

    # Start model loading in background (non-blocking)
    task = asyncio.ensure_future(load_avatar_models())
    task.add_done_callback(lambda t: logger.info(f"Model loading {'succeeded' if not t.exception() else f'failed: {t.exception()}'}"))

    logger.info("=" * 60)
    logger.info("DreamTalk Backend Ready!")
    logger.info(f"Avatar Viewer: http://localhost:5001/api/avatar/viewer")
    logger.info(f"API Docs:      http://localhost:5001/docs")
    if _redis_available:
        logger.info("Redis cache:     connected")
    if _weaviate_available:
        logger.info("Weaviate:        connected")
    if _celery_app:
        logger.info("Celery:          loaded")
    if _sentry_initialized:
        logger.info("Sentry:          enabled")
    logger.info("=" * 60)
    logger.info("Entering serving phase - yielding control to uvicorn")
    try:
        yield
    except asyncio.CancelledError:
        logger.info("Server received shutdown signal (CancelledError) - shutting down gracefully")
    except Exception as e:
        logger.warning(f"Unexpected error during server lifespan: {e}")
    finally:
        logger.info("Shutdown signal received - closing resources")
        try:
            await close_pool()
        except Exception:
            pass


app = FastAPI(
    title="Dreamtalk API Gateway",
    description="Backend API for Dreamtalk AI Digital Workforce Platform with 3D Avatar",
    version="0.5.0",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────
try:
    from dreamtalk.backend.services.api_logger import APILoggingMiddleware
    app.add_middleware(APILoggingMiddleware)
    logger.info("API logging middleware enabled")
except Exception as e:
    logger.warning(f"API logging middleware not available: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:4000,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# ── Rate Limiter ──────────────────────────────────────────────────────
try:
    from dreamtalk.backend.middleware.rate_limiter import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limiter enabled")
except Exception as e:
    logger.warning(f"Rate limiter not available: {e}")

# ── Input Validation ──────────────────────────────────────────────────
try:
    from dreamtalk.backend.middleware.input_validator import InputValidationMiddleware
    app.add_middleware(InputValidationMiddleware)
    logger.info("Input validation enabled")
except Exception as e:
    logger.warning(f"Input validation not available: {e}")


# ── Static file mounts ─────────────────────────────────────────────────
os.makedirs("voice_module/assets/outputs", exist_ok=True)
os.makedirs("voice_module/assets/voices", exist_ok=True)
# Serve pipeline TTS outputs (where chat API saves audio)
# Chat API writes to CWD-relative "pipeline_outputs/tts" (i.e. /app/pipeline_outputs/tts)
# Also check the parent-relative path for backward compatibility
_pipeline_tts_cwd = Path.cwd() / "pipeline_outputs" / "tts"
_pipeline_tts_parent = Path(__file__).resolve().parent.parent / "pipeline_outputs" / "tts"
os.makedirs(str(_pipeline_tts_cwd), exist_ok=True)
os.makedirs(str(_pipeline_tts_parent), exist_ok=True)
# Mount from CWD path (where files are actually written)
app.mount("/outputs", StaticFiles(directory=str(_pipeline_tts_cwd)), name="outputs")

os.makedirs("dreamtalk/media", exist_ok=True)
app.mount("/media", StaticFiles(directory="dreamtalk/media"), name="media")

_avatar_static = Path(__file__).resolve().parent.parent / "avatar" / "static"
os.makedirs(str(_avatar_static), exist_ok=True)
app.mount("/api/static", StaticFiles(directory=str(_avatar_static)), name="avatar_static")

# ── Routers ────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(dh_router)
app.include_router(voice_router)
app.include_router(chat_router)
app.include_router(identity_router)
app.include_router(digital_twins_router)
app.include_router(workforce_router)
app.include_router(pipeline_router)
app.include_router(avatar_router)
app.include_router(tasks_router)
app.include_router(emotion_router)
app.include_router(cognition_router)


# ── WebSocket Endpoint ─────────────────────────────────────────────────
from fastapi import WebSocket as _WS
from dreamtalk.backend.websocket.chat_handler import WebSocketChatHandler as _ChatHandler
_chat_ws_handler = _ChatHandler()

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: _WS, session_id: str):
    """WebSocket endpoint for real-time digital twin chat."""
    await websocket.accept()
    await _chat_ws_handler.handle_connection(websocket, session_id)

@app.websocket("/ws/chat")
async def websocket_chat_default(websocket: _WS):
    """WebSocket endpoint with auto-generated session ID."""
    await websocket.accept()
    await _chat_ws_handler.handle_connection(websocket)

@app.websocket("/api/v1/avatar/ws/chat")
async def websocket_chat_avatar(websocket: _WS):
    """WebSocket endpoint matching frontend constant WS_URL."""
    await websocket.accept()
    await _chat_ws_handler.handle_connection(websocket)

@app.websocket("/api/v1/avatar/ws/chat/{session_id}")
async def websocket_chat_avatar_session(websocket: _WS, session_id: str):
    """WebSocket endpoint matching frontend constant WS_URL with session."""
    await websocket.accept()
    await _chat_ws_handler.handle_connection(websocket, session_id)

@app.get("/ws/status")
async def websocket_status():
    """Check WebSocket server status."""
    return {
        "status": "available",
        "active_sessions": _chat_ws_handler.get_active_sessions(),
        "endpoints": ["/ws/chat", "/ws/chat/{session_id}"],
    }

# ── Pipeline Health Monitor ────────────────────────────────────────────
@app.get("/pipeline/health")
async def pipeline_health():
    """Comprehensive health check of all pipeline components."""
    from dreamtalk.pipeline.health import get_health_monitor
    monitor = get_health_monitor()
    return await monitor.check_all()


@app.get("/analytics/emotions")
async def emotion_analytics(window_minutes: int = 30):
    """Get emotion analytics data for dashboard visualization."""
    from dreamtalk.pipeline.analytics import get_analytics
    return get_analytics().get_emotion_analytics(window_minutes)


@app.get("/analytics/brain")
async def brain_analytics(window_minutes: int = 30):
    """Get brain activity analytics for visualization."""
    from dreamtalk.pipeline.analytics import get_analytics
    return get_analytics().get_brain_analytics(window_minutes)


@app.get("/analytics/stats")
async def session_stats():
    """Get overall session statistics."""
    from dreamtalk.pipeline.analytics import get_analytics
    return get_analytics().get_session_stats()


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus-format metrics endpoint."""
    from dreamtalk.pipeline.metrics import get_metrics
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(get_metrics().to_prometheus())


@app.get("/metrics/json")
async def json_metrics():
    """JSON metrics endpoint."""
    from dreamtalk.pipeline.metrics import get_metrics
    return get_metrics().to_json()


# ── Sentry Exception Handler ───────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if _sentry_initialized:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)[:200]},
    )


# ── Health / Monitoring Endpoints ─────────────────────────────────────
import time as _time_mod
_start_time = _time_mod.time()


@app.get("/livez")
async def liveness():
    """Kubernetes liveness probe — always OK if server is running."""
    return {"status": "alive", "uptime_seconds": int(_time_mod.time() - _start_time)}


@app.get("/readyz")
async def readiness():
    """Kubernetes readiness probe — checks if DB and critical deps are ready."""
    db_ok = False
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_ok = True
    except Exception:
        pass
    checks = {
        "database": db_ok,
        "redis": _redis_available,
        "weaviate": _weaviate_available,
    }
    all_ready = db_ok and _redis_available and _weaviate_available
    status_code = 200 if all_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_ready else "degraded", "checks": checks},
    )


@app.get("/metrics")
async def metrics():
    """Expose Prometheus-style metrics for monitoring."""
    uptime = int(_time_mod.time() - _start_time)
    return {
        "dreamtalk_uptime_seconds": uptime,
        "dreamtalk_db_connected": 1,
        "dreamtalk_redis_connected": 1 if _redis_available else 0,
        "dreamtalk_weaviate_connected": 1 if _weaviate_available else 0,
        "dreamtalk_celery_loaded": 1 if _celery_app else 0,
        "dreamtalk_sentry_enabled": 1 if _sentry_initialized else 0,
        "dreamtalk_models_loaded": 1,
        "dreamtalk_version": "0.5.0",
    }


@app.get("/sentry-debug")
async def sentry_debug():
    """Test endpoint to verify Sentry is capturing errors."""
    if not _sentry_initialized:
        return {"message": "Sentry not configured. Set SENTRY_DSN env var and restart."}
    try:
        raise ValueError("This is a test error for Sentry debugging")
    except ValueError as e:
        import sentry_sdk
        sentry_sdk.capture_exception(e)
        return {"message": "Test error sent to Sentry. Check your Sentry dashboard."}


@app.get("/")
async def root():
    return {
        "service": "Dreamtalk API Gateway",
        "status": "running",
        "version": "0.5.0",
        "avatar": "/api/avatar/viewer",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    db_status = "not_connected"
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"unavailable: {e}"

    weaviate_status = "unavailable"
    if _weaviate_available:
        try:
            from dreamtalk.backend.services.weaviate_client import health_check as _wc
            w = await _wc()
            weaviate_status = "connected" if w.get("available") else "unavailable"
        except Exception:
            weaviate_status = "unavailable"

    redis_status = "unavailable"
    if _redis_available:
        try:
            from dreamtalk.backend.services.redis_cache import _get_client as _rc
            if _rc():
                redis_status = "connected"
        except Exception:
            redis_status = "unavailable"

    return {
        "service": "Dreamtalk AI Digital Workforce Platform (Avatar Integrated)",
        "version": "0.5.0",
        "database": db_status,
        "redis": redis_status,
        "weaviate": weaviate_status,
        "celery": "loaded" if _celery_app else "unavailable",
        "status": "ok",
        "models_loaded": True,
        "avatar_viewer": "/api/avatar/viewer",
    }


if __name__ == "__main__":
    import uvicorn
    _project_root_path = Path(__file__).resolve().parent.parent
    os.chdir(str(_project_root_path))
    sys.path.insert(0, str(_project_root_path))
    uvicorn.run(
        "dreamtalk.backend.main:app",
        host="0.0.0.0",
        port=5001,
    )
