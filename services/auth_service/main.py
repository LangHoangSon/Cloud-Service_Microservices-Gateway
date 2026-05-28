import os
import uuid
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import hashlib
import hmac

app = FastAPI(title="Auth Service", version="1.0.0")

JWT_SECRET   = os.getenv("JWT_SECRET", "super-secret-key-change-in-prod")
JWT_ALGO     = "HS256"
JWT_EXPIRE_H = 24

# ── Simple file-based user store (no DB needed for demo) ─────────────────────
USERS_FILE = Path("users.json")

def _load_users() -> dict:
    if not USERS_FILE.exists():
        USERS_FILE.write_text("{}")
    return json.loads(USERS_FILE.read_text())

def _save_users(users: dict):
    USERS_FILE.write_text(json.dumps(users, indent=2))

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _verify_password(password: str, hashed: str) -> bool:
    return hmac.compare_digest(_hash_password(password), hashed)


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_EXPIRE_H * 3600


# ── JWT helpers ───────────────────────────────────────────────────────────────
def _create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_H),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Bearer dependency ─────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    return _decode_token(credentials.credentials)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"service": "auth", "status": "ok"}


@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest):
    users = _load_users()

    # Check email uniqueness
    if any(u["email"] == body.email for u in users.values()):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    users[user_id] = {
        "user_id":    user_id,
        "username":   body.username,
        "email":      body.email,
        "password":   _hash_password(body.password),
        "created_at": now,
    }
    _save_users(users)

    return UserResponse(
        user_id=user_id,
        username=body.username,
        email=body.email,
        created_at=now,
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    users = _load_users()

    user = next((u for u in users.values() if u["email"] == body.email), None)
    if not user or not _verify_password(body.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _create_token(user["user_id"], user["email"])
    return TokenResponse(access_token=token)


@app.get("/auth/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    users = _load_users()
    user_id = current_user["sub"]

    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        user_id=user["user_id"],
        username=user["username"],
        email=user["email"],
        created_at=user["created_at"],
    )


@app.get("/auth/users", response_model=list[UserResponse])
def list_users():
    """Admin endpoint — list all users (no sensitive data)."""
    users = _load_users()
    return [
        UserResponse(
            user_id=u["user_id"],
            username=u["username"],
            email=u["email"],
            created_at=u["created_at"],
        )
        for u in users.values()
    ]
