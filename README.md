# Backend API — `x-api-key` Anti-Pattern Exercise

A small FastAPI service used to demonstrate why authenticating clients with a
single static value in a custom `x-api-key` header is a weak security
pattern.

## Endpoints

| Method | Path        | Key required | Description             |
|--------|-------------|--------------|--------------------------|
| GET    | `/health`   | No           | Health check             |
| GET    | `/api/data` | Yes          | Returns static JSON      |
| POST   | `/api/data` | Yes          | Returns a confirmation   |

## Running locally

```bash
deactivate

rm -rf venv

python -m venv venv

source venv/Scripts/activate

pip install -r requirements.txt

python -m uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.
Interactive docs: `http://127.0.0.1:8000/docs`.

## Trying it with curl

```bash
# Public
curl http://127.0.0.1:8000/health

# Protected, no key -> 401
curl -i http://127.0.0.1:8000/api/data

# Protected, correct key -> 200
curl -i http://127.0.0.1:8000/api/data -H "x-api-key: supersecret-demo-key-123"

# POST
curl -i -X POST http://127.0.0.1:8000/api/data -H "x-api-key: supersecret-demo-key-123"
```

## Tests

```bash
pip install pytest httpx
pytest test_api.py
```

## Why this is an anti-pattern

This service intentionally implements the *weak* pattern so it can be
inspected and discussed:

- **One shared secret for everyone.** Every legitimate client uses the exact
  same key, so there's no way to tell clients apart, revoke one client
  without breaking all of them, or audit who did what.
- **Plaintext comparison, no hashing.** The key is compared as a raw string
  in memory and (typically) stored in plaintext in `.env` files, CI secrets,
  or source control by accident.
- **No expiration or rotation.** The key is valid forever unless a human
  manually changes it and redeploys — and every client must be updated at
  the same time.
- **Trivial to steal.** Because it's just an HTTP header, the key is visible
  in browser dev tools, proxy logs, and any client-side JavaScript bundle.
  A key embedded in a frontend app is, for practical purposes, public.
- **No scoping.** The key grants full access to every protected endpoint —
  there's no concept of least privilege.
- **Vulnerable over plain HTTP.** Without TLS, the header is sent in the
  clear and can be sniffed on the network.

### What a stronger design looks like

- Short-lived, signed tokens (e.g. JWT) issued after real authentication
  (OAuth2 / OpenID Connect, username+password, etc.), not a static secret.
- Per-client credentials, so keys can be individually revoked and audited.
- Hashing/salting any stored secret server-side, comparing with a
  constant-time comparison.
- Key rotation policies and expiration.
- Rate limiting and anomaly detection on top of authentication.
- HTTPS enforced everywhere so headers/tokens are never sent in the clear.

This exercise is deliberately simplified for teaching purposes and should
never be used as-is in a real system.
