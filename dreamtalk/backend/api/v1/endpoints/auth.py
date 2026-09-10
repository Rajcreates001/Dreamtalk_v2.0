from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uuid
import hashlib
import os
import jwt
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

from fastapi.responses import RedirectResponse

from dreamtalk.backend.api.v1.models.auth import (
    SignupRequest, LoginRequest, TokenResponse, UserResponse,
    AuthResponse, RefreshRequest, PasswordResetRequest,
    PasswordResetConfirm, ErrorResponse, GoogleAuthRequest,
)
from dreamtalk.backend.db.database import fetchrow, execute, fetch

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)

JWT_SECRET = os.getenv("JWT_SECRET", "dreamtalk-secret-change-in-production")

# Warn if using default secret
if JWT_SECRET == "dreamtalk-secret-change-in-production":
    import logging as _jwt_logging
    _jwt_logging.getLogger("dreamtalk.auth").warning(
        "JWT_SECRET is set to the default value! "
        "Set a strong, unique JWT_SECRET environment variable in production. "
        "This is a security risk — tokens can be forged with the default secret."
    )
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = timedelta(hours=24)
REFRESH_TOKEN_EXPIRE = timedelta(days=30)


def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored: str) -> bool:
    salt_hex, key_hex = stored.split(":")
    salt = bytes.fromhex(salt_hex)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return key.hex() == key_hex


def create_tokens(user_id: str, email: str, role: str) -> dict:
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE,
    }
    refresh_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRE,
    }
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": int(ACCESS_TOKEN_EXPIRE.total_seconds()),
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    existing = await fetchrow("SELECT id FROM users WHERE email = $1", req.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(req.password)

    await execute(
        """INSERT INTO users (id, email, password_hash, full_name, role)
           VALUES ($1, $2, $3, $4, $5)""",
        user_id, req.email, pw_hash, req.full_name, req.role.value,
    )

    # Create free subscription
    sub_id = str(uuid.uuid4())
    await execute(
        """INSERT INTO subscriptions (id, user_id, tier, status, current_period_start, current_period_end)
           VALUES ($1, $2, 'free', 'active', NOW(), NOW() + INTERVAL '100 years')""",
        sub_id, user_id,
    )

    # Create default settings
    await execute(
        """INSERT INTO user_settings (id, user_id) VALUES ($1, $2)""",
        str(uuid.uuid4()), user_id,
    )

    tokens = create_tokens(user_id, req.email, req.role.value)

    # Store session
    await execute(
        """INSERT INTO user_sessions (id, user_id, access_token, refresh_token, expires_at, refresh_expires_at)
           VALUES ($1, $2, $3, $4, NOW() + $5::interval, NOW() + $6::interval)""",
        str(uuid.uuid4()), user_id,
        tokens["access_token"], tokens["refresh_token"],
        timedelta(hours=24), timedelta(days=30),
    )

    user = await fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    return AuthResponse(
        user=UserResponse(
            id=str(user["id"]),
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            avatar_url=user["avatar_url"],
            is_verified=user["is_verified"],
            created_at=user["created_at"].isoformat(),
        ),
        tokens=TokenResponse(**tokens),
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    user = await fetchrow("SELECT * FROM users WHERE email = $1", req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is disabled")

    user_id = str(user["id"])
    tokens = create_tokens(user_id, user["email"], user["role"])

    await execute(
        """INSERT INTO user_sessions (id, user_id, access_token, refresh_token, expires_at, refresh_expires_at)
           VALUES ($1, $2, $3, $4, NOW() + $5::interval, NOW() + $6::interval)""",
        str(uuid.uuid4()), user_id,
        tokens["access_token"], tokens["refresh_token"],
        timedelta(hours=24), timedelta(days=30),
    )

    await execute(
        "UPDATE users SET last_login_at = NOW() WHERE id = $1",
        user_id,
    )

    return AuthResponse(
        user=UserResponse(
            id=user_id,
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            avatar_url=user["avatar_url"],
            is_verified=user["is_verified"],
            created_at=user["created_at"].isoformat(),
        ),
        tokens=TokenResponse(**tokens),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest):
    try:
        payload = jwt.decode(req.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await fetchrow("SELECT * FROM users WHERE id = $1", payload["sub"])
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    tokens = create_tokens(str(user["id"]), user["email"], user["role"])
    return TokenResponse(**tokens)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    user = await fetchrow("SELECT * FROM users WHERE id = $1", current_user["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=str(user["id"]),
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        avatar_url=user["avatar_url"],
        is_verified=user["is_verified"],
        created_at=user["created_at"].isoformat(),
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    await execute(
        "UPDATE user_sessions SET is_revoked = TRUE WHERE user_id = $1 AND is_revoked = FALSE",
        current_user["sub"],
    )
    return {"detail": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(req: PasswordResetRequest):
    user = await fetchrow("SELECT id FROM users WHERE email = $1", req.email)
    if not user:
        return {"detail": "If the email exists, a reset link has been sent"}
    token = str(uuid.uuid4()) + os.urandom(16).hex()
    await execute(
        """INSERT INTO password_resets (id, user_id, token, expires_at)
           VALUES ($1, $2, $3, NOW() + INTERVAL '1 hour')""",
        str(uuid.uuid4()), user["id"], token,
    )
    # In production: send email with reset link
    return {"detail": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(req: PasswordResetConfirm):
    reset = await fetchrow(
        "SELECT * FROM password_resets WHERE token = $1 AND used_at IS NULL AND expires_at > NOW()",
        req.token,
    )
    if not reset:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    pw_hash = hash_password(req.new_password)
    await execute("UPDATE users SET password_hash = $1 WHERE id = $2", pw_hash, reset["user_id"])
    await execute("UPDATE password_resets SET used_at = NOW() WHERE id = $1", reset["id"])
    await execute(
        "UPDATE user_sessions SET is_revoked = TRUE WHERE user_id = $1",
        reset["user_id"],
    )
    return {"detail": "Password reset successfully"}


# ─── OAuth / Social Login Endpoints ──────────────────────────────────


@router.get("/google/login")
async def google_login_redirect():
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    if not GOOGLE_CLIENT_ID:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_not_configured")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", f"{FRONTEND_URL}/api/v1/auth/google/callback")
    scope = "openid email profile"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
    )
    return RedirectResponse(url=auth_url)


@router.post("/google")
async def google_auth(req: GoogleAuthRequest):
    """Exchange a Google access token for Dreamtalk tokens."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {req.access_token}"},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid Google token")
            google_user = resp.json()
    except ImportError:
        raise HTTPException(status_code=500, detail="httpx is required for Google auth")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Failed to verify Google token")

    email = google_user.get("email")
    name = google_user.get("name", email.split("@")[0])
    google_id = google_user.get("sub")

    if not email or not google_id:
        raise HTTPException(status_code=400, detail="Incomplete Google profile data")

    existing = await fetchrow("SELECT * FROM users WHERE email = $1", email)
    now = datetime.now(timezone.utc)
    if existing:
        user_id = existing["id"]
        role = existing["role"]
    else:
        user_id = str(uuid.uuid4())
        role = "personal"
        await execute(
            """INSERT INTO users (id, email, full_name, role, password_hash, is_verified, is_active, created_at, updated_at)
               VALUES ($1, $2, $3, $4, '', TRUE, TRUE, NOW(), NOW())""",
            user_id, email, name, role,
        )

    tokens = create_tokens(user_id, email, role)
    session_id = str(uuid.uuid4())
    await execute(
        """INSERT INTO user_sessions (id, user_id, access_token, refresh_token, expires_at, refresh_expires_at)
           VALUES ($1, $2, $3, $4, $5, NOW() + $6::interval)""",
        session_id, user_id, tokens["access_token"], tokens["refresh_token"],
        datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE,
        timedelta(days=30),
    )

    user_resp = UserResponse(
        id=str(user_id),
        email=email,
        full_name=name,
        role=role,
        avatar_url=None,
        is_verified=True,
        created_at=now.isoformat(),
    )
    return {"user": user_resp, "tokens": tokens}


@router.get("/github/login")
async def github_login_redirect():
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
    if not GITHUB_CLIENT_ID:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=github_not_configured")
    redirect_uri = os.getenv("GITHUB_REDIRECT_URI", f"{FRONTEND_URL}/api/v1/auth/github/callback")
    auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read:user user:email"
    )
    return RedirectResponse(url=auth_url)


@router.post("/github")
async def github_auth(req: GoogleAuthRequest):
    """Exchange a GitHub access token for Dreamtalk tokens."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {req.access_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Dreamtalk/1.0",
                },
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid GitHub token")
            github_user = resp.json()

            email_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {req.access_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Dreamtalk/1.0",
                },
            )
            emails = email_resp.json() if email_resp.status_code == 200 else []
            primary_email = next(
                (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                github_user.get("email"),
            )
    except ImportError:
        raise HTTPException(status_code=500, detail="httpx is required for GitHub auth")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Failed to verify GitHub token")

    email = primary_email or f"{github_user['login']}@github.user"
    name = github_user.get("name") or github_user["login"]
    github_id = str(github_user["id"])

    existing = await fetchrow("SELECT * FROM users WHERE email = $1", email)
    now = datetime.now(timezone.utc)
    if existing:
        user_id = existing["id"]
        role = existing["role"]
    else:
        user_id = str(uuid.uuid4())
        role = "personal"
        await execute(
            """INSERT INTO users (id, email, full_name, role, password_hash, is_verified, is_active, created_at, updated_at)
               VALUES ($1, $2, $3, $4, '', TRUE, TRUE, NOW(), NOW())""",
            user_id, email, name, role,
        )

    tokens = create_tokens(user_id, email, role)
    session_id = str(uuid.uuid4())
    await execute(
        """INSERT INTO user_sessions (id, user_id, access_token, refresh_token, expires_at, refresh_expires_at)
           VALUES ($1, $2, $3, $4, $5, NOW() + $6::interval)""",
        session_id, user_id, tokens["access_token"], tokens["refresh_token"],
        datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE,
        timedelta(days=30),
    )

    user_resp = UserResponse(
        id=str(user_id),
        email=email,
        full_name=name,
        role=role,
        avatar_url=github_user.get("avatar_url"),
        is_verified=True,
        created_at=now.isoformat(),
    )
    return {"user": user_resp, "tokens": tokens}


@router.get("/microsoft/login")
async def microsoft_login_redirect():
    MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
    if not MICROSOFT_CLIENT_ID:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=microsoft_not_configured")
    redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI", f"{FRONTEND_URL}/api/v1/auth/microsoft/callback")
    auth_url = (
        f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        f"?client_id={MICROSOFT_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid email profile User.Read"
    )
    return RedirectResponse(url=auth_url)


@router.post("/microsoft")
async def microsoft_auth(req: GoogleAuthRequest):
    """Exchange a Microsoft access token for Dreamtalk tokens."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {req.access_token}"},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid Microsoft token")
            ms_user = resp.json()
    except ImportError:
        raise HTTPException(status_code=500, detail="httpx is required for Microsoft auth")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Failed to verify Microsoft token")

    email = ms_user.get("userPrincipalName") or ms_user.get("mail")
    name = ms_user.get("displayName") or email.split("@")[0] if email else "Microsoft User"
    ms_id = ms_user.get("id")

    if not email or not ms_id:
        raise HTTPException(status_code=400, detail="Incomplete Microsoft profile data")

    existing = await fetchrow("SELECT * FROM users WHERE email = $1", email)
    now = datetime.now(timezone.utc)
    if existing:
        user_id = existing["id"]
        role = existing["role"]
    else:
        user_id = str(uuid.uuid4())
        role = "personal"
        await execute(
            """INSERT INTO users (id, email, full_name, role, password_hash, is_verified, is_active, created_at, updated_at)
               VALUES ($1, $2, $3, $4, '', TRUE, TRUE, NOW(), NOW())""",
            user_id, email, name, role,
        )

    tokens = create_tokens(user_id, email, role)
    session_id = str(uuid.uuid4())
    await execute(
        """INSERT INTO user_sessions (id, user_id, access_token, refresh_token, expires_at, refresh_expires_at)
           VALUES ($1, $2, $3, $4, $5, NOW() + $6::interval)""",
        session_id, user_id, tokens["access_token"], tokens["refresh_token"],
        datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE,
        timedelta(days=30),
    )

    user_resp = UserResponse(
        id=str(user_id),
        email=email,
        full_name=name,
        role=role,
        avatar_url=None,
        is_verified=True,
        created_at=now.isoformat(),
    )
    return {"user": user_resp, "tokens": tokens}
