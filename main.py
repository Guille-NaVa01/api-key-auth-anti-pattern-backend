"""
Backend API — Security Anti-Pattern Exercise
=============================================

Demonstrates a common (and weak) authentication pattern:
checking a static, shared secret sent by the client in a custom
`x-api-key` HTTP header.

This is intentionally NOT a production-grade auth system. See
README.md for a discussion of why this pattern is insecure and
what to use instead (OAuth2 / JWT, hashed + rotated keys stored
server-side, per-client keys, rate limiting, HTTPS-only, etc.)

Step 2 addition: Fernet encrypt/decrypt for data stored in SQLite.
Step 3 addition: DATABASE_ENCRYPTION_KEY read from env var (never hardcoded).
"""

import os
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from cryptography.fernet import Fernet, InvalidToken

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(
    title="Security Exercise API",
    description=(
        "Demonstrates the x-api-key anti-pattern for educational purposes. "
        "Also integrates Fernet encryption for database-stored messages."
    ),
    version="2.0.0",
)

# Allow the frontend (running on a different origin) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# THE ANTI-PATTERN LIVES HERE
#
# A single static secret, read from an environment variable, is compared
# against whatever the client sends in the `x-api-key` header.
# --------------------------------------------------------------------------
# Store the API_KEY in a mutable dict so the /internal/rotate-key endpoint
# can update it at runtime when Nginx rotates without restarting the server.
_api_key_store: dict[str, str] = {"current": os.environ.get("API_KEY", "")}
if not _api_key_store["current"]:
    raise RuntimeError(
        "API_KEY environment variable is not set. "
        "Copy .env.example to .env and set a value."
    )


def verify_api_key(x_api_key: str | None) -> None:
    """Naive header check: presence + exact string match. No hashing,
    no per-client identity, no expiration, no scopes."""
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing x-api-key header",
        )
    if x_api_key != _api_key_store["current"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


# --------------------------------------------------------------------------
# STEP 3 — DATABASE_ENCRYPTION_KEY (separate from API_KEY, never rotated)
#
# This key encrypts/decrypts data at rest in the database.
# It must NEVER change once data has been stored, otherwise existing
# ciphertext becomes unreadable.
# --------------------------------------------------------------------------
DATABASE_ENCRYPTION_KEY = os.environ.get("DATABASE_ENCRYPTION_KEY")
if not DATABASE_ENCRYPTION_KEY:
    raise RuntimeError(
        "DATABASE_ENCRYPTION_KEY environment variable is not set. "
        "Add it to your .env file."
    )

_cipher = Fernet(DATABASE_ENCRYPTION_KEY.encode())


# --------------------------------------------------------------------------
# DATABASE SETUP (SQLite — no extra infrastructure required)
# --------------------------------------------------------------------------
DATABASE_URL = "sqlite:///./messages.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Message(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, index=True)
    sender     = Column(String(50), nullable=False)
    receiver   = Column(String(50), nullable=False)
    ciphertext = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


Base.metadata.create_all(bind=engine)


# --------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# --------------------------------------------------------------------------
class DataPayload(BaseModel):
    # The body is accepted but ignored for the legacy endpoints.
    model_config = ConfigDict(extra="allow")


class RotateKeyRequest(BaseModel):
    new_key:         str
    rotation_secret: str  # Must equal DATABASE_ENCRYPTION_KEY to authenticate


class SendMessageRequest(BaseModel):
    sender:   str
    receiver: str
    message:  str


class MessageOut(BaseModel):
    id:        int
    sender:    str
    receiver:  str
    message:   str          # decrypted plaintext returned to caller
    created_at: datetime


# --------------------------------------------------------------------------
# INTERNAL ROTATION ENDPOINT
# --------------------------------------------------------------------------
@app.post("/internal/rotate-key", include_in_schema=False)
def internal_rotate_key(payload: RotateKeyRequest):
    """Called by the Nginx container's rotation cronjob every 2 minutes.

    Updates the in-memory API_KEY so the backend stays in sync with Nginx
    without a restart. Protected by DATABASE_ENCRYPTION_KEY as a shared
    auth secret — this key never rotates, so it's always stable.

    This endpoint is intentionally excluded from the OpenAPI docs.
    """
    if payload.rotation_secret != DATABASE_ENCRYPTION_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid rotation secret.",
        )
    old_key = _api_key_store["current"]
    _api_key_store["current"] = payload.new_key
    print(f"[rotate] API_KEY updated: {old_key[:8]}... -> {payload.new_key[:8]}...")
    return {"rotated": True, "hint": f"new key starts with {payload.new_key[:4]}..."}


# --------------------------------------------------------------------------
# ORIGINAL ENDPOINTS (unchanged)
# --------------------------------------------------------------------------
@app.get("/health")
def health():
    """Public endpoint — no API key required."""
    return {"status": "ok"}


@app.get("/api/data")
def get_data(x_api_key: str | None = Header(default=None)):
    """Protected endpoint — requires a valid x-api-key header."""
    verify_api_key(x_api_key)
    return {
        "message": "Protected data",
        "course":  "Security Exercise",
        "status":  "success",
    }


@app.post("/api/data")
def post_data(
    payload: DataPayload | None = None,
    x_api_key: str | None = Header(default=None),
):
    """Protected endpoint — requires a valid x-api-key header.
    The request body is accepted but not used."""
    verify_api_key(x_api_key)
    return {"message": "POST received"}


# --------------------------------------------------------------------------
# STEP 2 — ENCRYPT → DATABASE → DECRYPT endpoints
# --------------------------------------------------------------------------
@app.post("/api/messages", status_code=status.HTTP_201_CREATED)
def send_message(
    payload: SendMessageRequest,
    x_api_key: str | None = Header(default=None),
):
    """Encrypts `message` with Fernet and stores the ciphertext in SQLite.

    The plaintext is never persisted — only the encrypted blob lives in the DB.
    """
    verify_api_key(x_api_key)

    ciphertext = _cipher.encrypt(payload.message.encode()).decode()

    db: Session = SessionLocal()
    try:
        record = Message(
            sender=payload.sender,
            receiver=payload.receiver,
            ciphertext=ciphertext,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {"id": record.id, "message": "Message encrypted and stored."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")
    finally:
        db.close()


@app.get("/api/messages", response_model=list[MessageOut])
def get_messages(
    x_api_key: str | None = Header(default=None),
):
    """Reads all stored messages, decrypts each one, and returns plaintext."""
    verify_api_key(x_api_key)

    db: Session = SessionLocal()
    try:
        records = db.query(Message).order_by(Message.created_at.asc()).all()
        result = []
        for r in records:
            try:
                plaintext = _cipher.decrypt(r.ciphertext.encode()).decode()
            except InvalidToken:
                plaintext = "[ERROR: could not decrypt — key mismatch?]"
            result.append(MessageOut(
                id=r.id,
                sender=r.sender,
                receiver=r.receiver,
                message=plaintext,
                created_at=r.created_at,
            ))
        return result
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
