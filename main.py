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
"""

import os
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv is optional; env vars can also be set directly.
    pass

app = FastAPI(
    title="Security Exercise API",
    description="Demonstrates the x-api-key anti-pattern for educational purposes.",
    version="1.0.0",
)

# Allow the frontend (running on a different origin) to call this API.
# In a real system you would restrict this to known origins.
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
# against whatever the client sends in the `x-api-key` header. Anyone who
# obtains this value (browser dev tools, a proxy, a leaked .env file,
# decompiled mobile app, etc.) can authenticate as any other client,
# forever, until the key is manually rotated.
# --------------------------------------------------------------------------
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY environment variable is not set. Copy .env.example to .env and set a value.")

def verify_api_key(x_api_key: str | None) -> None:
    """Naive header check: presence + exact string match. No hashing,
    no per-client identity, no expiration, no scopes."""
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing x-api-key header",
        )
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


class DataPayload(BaseModel):
    # The body is accepted but ignored for this exercise.
    model_config = ConfigDict(extra="allow")


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
        "course": "Security Exercise",
        "status": "success",
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
