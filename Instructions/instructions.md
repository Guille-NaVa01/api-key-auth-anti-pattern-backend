# Exercise: API Key Authentication Anti-Pattern

## Objective

The objective of this exercise is to understand and reproduce a common security anti-pattern: **implementing API authentication using a custom `x-api-key` HTTP header without a proper authentication/authorization mechanism**.

You will build two independent GitHub repositories:

1. **Backend API** — exposes public and protected endpoints.
2. **Frontend application** — consumes the API and sends the required `x-api-key` header.


---

## Part 1 — Backend API

Create a GitHub repository containing a backend API.

You may use any backend technology covered in class, such as:

* Python + Flask/FastAPI
* Node.js + Express
* Java/Spring
* Go

### Required endpoints

Your API must implement the following endpoints:

| Method | Endpoint    | API Key Required | Expected Result        |
| ------ | ----------- | ---------------- | ---------------------- |
| GET    | `/health`   | ❌ No             | Health/status response |
| GET    | `/api/data` | ✅ Yes            | Static JSON            |
| POST   | `/api/data` | ✅ Yes            | Confirmation message   |

### 1. Health endpoint

Implement:

```text
GET /health
```

This endpoint **must not require an API key**.

Example response:

```json
{
  "status": "ok"
}
```

---

### 2. Protected GET endpoint

Implement:

```text
GET /api/data
```

The endpoint must require the following HTTP header:

```text
x-api-key: <your-api-key>
```

If the correct API key is provided, return a static JSON response.

For example:

```json
{
  "message": "Protected data",
  "course": "Security Exercise",
  "status": "success"
}
```

If the API key is missing or invalid, the API should return an appropriate HTTP error, such as:

```text
401 Unauthorized
```

---

### 3. Protected POST endpoint

Implement:

```text
POST /api/data
```

This endpoint must also require:

```text
x-api-key: <your-api-key>
```

The body can be ignored for this exercise.

A successful request should return something similar to:

```json
{
  "message": "POST received"
}
```

Requests without a valid API key must be rejected.

---

## Security Anti-Pattern

The purpose of the exercise is to reproduce the following pattern:

```text
Client
   |
   | x-api-key: SECRET
   v
+----------------+
|     Backend    |
|                |
| Check header   |
|       |        |
|       v        |
| Compare key    |
+----------------+
```

The backend should perform a simple check similar to:

```text
Does the request contain x-api-key?
        |
        +-- No --> 401
        |
        +-- Yes
              |
              v
       Is the value correct?
              |
         +----+----+
         |         |
        No        Yes
         |         |
        401        API
                  response
```

The purpose is **not** to create a production-grade authentication system. The objective is to understand why relying on a static API key passed directly by the client is considered a security weakness.

---

## Part 2 — Frontend Repository

Create a **second GitHub repository** containing the frontend.

Do not place the frontend inside the backend repository.

The frontend must contain at least these three separate files:

```text
frontend/
├── index.html
├── styles.css
└── app.js
```

### `index.html`

Create a simple but properly structured webpage containing:

* A title
* A button to call the protected GET endpoint
* A button to call the protected POST endpoint
* An area where the API response will be displayed

Example:

```text
Security API Exercise

[ Get Protected Data ]
[ Send POST Request ]

Response:
--------------------------------
|                              |
|       API response           |
|                              |
--------------------------------
```

---

### `styles.css`

Create the styling separately from the HTML.

The page should have a clean and readable interface.

Do not put the CSS directly inside `index.html`.

---

### `app.js`

The JavaScript must use the browser's `fetch()` API to communicate with the backend.

The requests to the protected endpoints must include:

```http
x-api-key: <your-api-key>
```

For example, conceptually:

```javascript
fetch("http://localhost:PORT/api/data", {
    method: "GET",
    headers: {
        "x-api-key": API_KEY
    }
});
```

The frontend must display the response returned by the backend in the browser.

The POST request should similarly send the `x-api-key` header.

---

# Expected Architecture

Your final project should look like this:

```text
GitHub
│
├── Repository 1: security-api
│   │
│   ├── backend source code
│   ├── README.md
│   └── ...
│
└── Repository 2: security-frontend
    │
    ├── index.html
    ├── styles.css
    ├── app.js
    └── README.md
```

The communication should be:

```text
                   Browser
                      |
                      |
               Frontend Repository
                      |
             x-api-key: SECRET
                      |
                      v
              +---------------+
              |   Backend API  |
              +---------------+
                /      |      \
               /       |       \
          /health   GET /api   POST /api
             |          |          |
          Public     Protected  Protected
```

---

# Required Tests

You must demonstrate that the API behaves correctly.

### Test 1 — Health

Call:

```text
GET /health
```

Expected:

```text
200 OK
```

No API key should be required.

### Test 2 — GET without API key

Call:

```text
GET /api/data
```

without the `x-api-key` header.

Expected:

```text
401 Unauthorized
```

### Test 3 — GET with incorrect API key

Send:

```text
x-api-key: wrong-key
```

Expected:

```text
401 Unauthorized
```

### Test 4 — GET with correct API key

Send:

```text
x-api-key: <correct-key>
```

Expected:

```text
200 OK
```

and the static JSON response.

### Test 5 — POST without API key

Expected:

```text
401 Unauthorized
```

### Test 6 — POST with correct API key

Expected:

```text
200 OK
```

and:

```json
{
  "message": "POST received"
}
```

### Test 7 — Frontend

Open the frontend in a browser and demonstrate that:

1. The GET button successfully calls the protected GET endpoint.
2. The POST button successfully calls the protected POST endpoint.
3. The API responses are displayed on the webpage.

---

# Deliverables

Submit **two GitHub repository URLs**.

### Repository 1 — Backend

Must contain:

* Backend source code
* `/health`
* Protected GET endpoint
* Protected POST endpoint
* `x-api-key` validation
* HTTP error handling
* README with installation and execution instructions

### Repository 2 — Frontend

Must contain:

* `index.html`
* `styles.css`
* `app.js`
* README with instructions
* Calls to both protected API endpoints
* `x-api-key` header
* API responses displayed in the browser

---