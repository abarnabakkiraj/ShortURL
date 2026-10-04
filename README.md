# URL Shortener & Analytics System

A full-stack web app that turns long URLs into short links, redirects visitors, and records every click so the owner can see how a link performs.

## Features

- Register, log in and log out (JWT authentication, bcrypt-hashed passwords)
- Create short links with an auto-generated 7-character code, or choose your own alias
- Optional expiry date per link
- Redirect `http://localhost:8000/<code>` to the original URL (HTTP 307)
- Every click is stored: time, IP address, user agent, referrer, device, browser, operating system and (optionally) country
- Analytics per link: total / today / last 7 days / last 30 days, clicks-over-time line chart, device, browser, OS and referrer breakdowns, plus a "top links" list
- Copy, open and delete links; users can only ever see their own links and analytics
- Responsive dashboard for desktop, tablet and mobile

## Technology Stack

| Layer | Tools |
| --- | --- |
| Frontend | React 19, Vite, JavaScript, Tailwind CSS 4, React Router, Axios, Recharts |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic 2, PyJWT, bcrypt, Uvicorn |
| Database | PostgreSQL (SQLite in memory is used **only** by the tests) |
| Testing | Pytest, FastAPI TestClient |
| Dev tools | VS Code, Windows PowerShell, Git, Docker (optional) |

## Architecture

```
 Browser (React SPA, :5173)
        │  Axios + "Authorization: Bearer <JWT>"
        ▼
 FastAPI (:8000)
   routers/   → HTTP only: validate input, call a service, shape the response
   services/  → business logic: short codes, ownership checks, analytics queries
   models.py  → SQLAlchemy tables      schemas.py → Pydantic request/response models
        │
        ▼
 PostgreSQL:   users 1──* urls 1──* clicks
```

**How a redirect works** (`GET /{short_code}`):

1. Look the code up in `urls` (unique index → one fast query).
2. 404 if it doesn't exist, 410 if the link is disabled or expired.
3. Insert a row into `clicks` and increment `urls.click_count`. If this fails, the error is logged but the visitor is still redirected.
4. Reply `307 Temporary Redirect` with `Location: <original_url>`. A temporary redirect is used on purpose: browsers don't cache it, so every visit reaches the server and gets counted.

**Short codes** are 7 random characters from `A-Z a-z 0-9`, produced by Python's `secrets` module (62⁷ ≈ 3.5 trillion combinations). The code is checked against the database, and if it already exists (or two requests race and the unique index rejects one) a new one is generated. Codes are random, so database IDs are never exposed in a short URL.

**Authorization:** every URL query is filtered by the logged-in user's ID. Asking for somebody else's link or analytics returns `404`, so the existence of other users' links isn't revealed.

## Project Structure

```
url-shortener-analytics/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, error handlers, startup table creation
│   │   ├── config.py          # Settings read from environment / .env
│   │   ├── database.py        # Engine, session factory, Base
│   │   ├── models.py          # User, Url, Click tables
│   │   ├── schemas.py         # Pydantic models + URL/alias validation
│   │   ├── auth.py            # Password hashing, JWT create/decode
│   │   ├── dependencies.py    # get_db, get_current_user
│   │   ├── routers/           # auth.py, urls.py (+ redirect), analytics.py
│   │   └── services/          # url_service.py, analytics_service.py, geo.py
│   ├── tests/                 # conftest.py, test_auth.py, test_urls.py, test_analytics.py
│   ├── requirements.txt, pytest.ini, .env.example, Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/        # Navbar, UrlForm, UrlTable, AnalyticsCard, ProtectedRoute, CopyButton, BreakdownChart
│   │   ├── pages/             # Login, Register, Dashboard, Analytics, NotFound
│   │   ├── context/           # AuthContext (login state)
│   │   ├── services/api.js    # Axios instance, token handling, API functions
│   │   └── utils/format.js
│   ├── package.json, vite.config.js, .env.example, Dockerfile
├── docker-compose.yml
├── .env.example               # secrets for docker-compose only
├── .gitignore
└── README.md
```

## Prerequisites

Install these once (Windows):

1. **Python 3.11 or newer** – <https://www.python.org/downloads/>. Tick **"Add python.exe to PATH"** in the installer. Check with `python --version`.
2. **Node.js 20.19+ or 22 LTS** – <https://nodejs.org/>. Check with `node --version` and `npm --version`.
3. **PostgreSQL 14+** – <https://www.postgresql.org/download/windows/>. Run the installer, keep the default port `5432`, and **remember the password you set for the `postgres` user**. The installer also includes `psql` and pgAdmin.
4. **Git** (optional) – <https://git-scm.com/download/win>.
5. **Docker Desktop** (optional, only for the Docker route).

## Backend Setup

Open the project folder in VS Code, open a terminal (**Terminal → New Terminal**, PowerShell), then:

```powershell
cd backend

python -m venv venv

.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

If PowerShell refuses to run `Activate.ps1` ("running scripts is disabled on this system"), allow it for this terminal only and try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

In VS Code, press `Ctrl+Shift+P` → **Python: Select Interpreter** → choose `backend\venv\Scripts\python.exe`.

## Environment Variables

Still inside `backend`, create your `.env` from the template:

```powershell
Copy-Item .env.example .env
```

Generate a JWT secret and copy the printed value:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Open `backend\.env` and fill in the values:

| Variable | Meaning |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/urlshortener` (URL-encode special characters in the password, e.g. `@` → `%40`) |
| `JWT_SECRET_KEY` | The random secret generated above (at least 32 characters) |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime, default `60` |
| `FRONTEND_URL` | Origin allowed by CORS, `http://localhost:5173` (comma-separate several) |
| `BASE_URL` | Public address of the API, used to build short links: `http://localhost:8000` |
| `TRUST_PROXY_HEADERS` | `false` locally. Set `true` only behind a trusted reverse proxy/CDN so the real client IP and country are read from headers |
| `BCRYPT_ROUNDS` | Password hashing cost, default `12` |

`.env` is listed in `.gitignore`, so your secrets are never committed.

## Database Setup

Create an empty database named `urlshortener`. **You do not create tables by hand**: the backend creates them automatically on startup.

Using `psql` (adjust the version number `16` to the one you installed):

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE DATABASE urlshortener;"
```

Enter your `postgres` password when asked. Or, with pgAdmin: right-click **Databases → Create → Database…**, name it `urlshortener`, click Save.

## Run Backend

With the virtual environment active and inside `backend`:

```powershell
uvicorn app.main:app --reload
```

Check <http://localhost:8000/api/health> – it should return `{"status":"ok","database":"connected"}`. If you see a database connection error, PostgreSQL isn't running or `DATABASE_URL` is wrong.

## Frontend Setup

Open a **second** terminal:

```powershell
cd frontend

Copy-Item .env.example .env

npm install

npm run dev
```

`frontend\.env` contains `VITE_API_URL=http://localhost:8000` (the backend address).

To create a production build: `npm run build` (output in `frontend\dist`).

## URLs

| What | Address |
| --- | --- |
| Frontend | <http://localhost:5173> |
| Backend API | <http://localhost:8000> |
| Swagger UI (interactive API docs) | <http://localhost:8000/docs> |
| Health check | <http://localhost:8000/api/health> |
| A short link | `http://localhost:8000/<short_code>` |

Try it: open the frontend, **Create an account**, paste a long URL, click **Shorten**, then open the short link a few times and press **Analytics**.

## Testing

The tests use an **in-memory SQLite database** (forced in `tests/conftest.py`), so they never touch your PostgreSQL data. From `backend` with the venv active:

```powershell
pytest -v
```

The suite (64 tests) covers registration, login, invalid login, JWT errors (invalid/expired), URL creation/listing/deletion, alias and URL validation, short-code uniqueness and collision handling, redirects (unknown, deleted, expired, inactive), click tracking, analytics (summary, timeline, breakdowns), and authorization (users can't read or delete each other's links or analytics).

## Docker

Docker is optional; local development works without it.

```powershell
Copy-Item .env.example .env
```

Edit the root `.env`: set `POSTGRES_PASSWORD` (letters and digits only) and `JWT_SECRET_KEY` (see the generator command above). Then:

```powershell
docker compose up --build
```

This starts PostgreSQL (`db`), the API (`backend`, http://localhost:8000) and the React dev server (`frontend`, http://localhost:5173). Data is kept in the `pgdata` volume. Stop with `Ctrl+C`; remove everything including data with `docker compose down -v`.

Run the tests inside the container: `docker compose exec backend pytest`

> Docker and local setups both use port 8000/5173, so stop one before starting the other.

## API Documentation

All `/api/urls` and `/api/analytics` endpoints require the header `Authorization: Bearer <access_token>`. Errors use the shape `{"detail": "message"}`.

### Authentication

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/auth/register` | Body `{name, email, password}` (password 8–72 chars) → `201` user. `409` if the email exists. |
| POST | `/api/auth/login` | Body `{email, password}` → `{access_token, token_type, user}`. `401` on bad credentials. |
| GET | `/api/auth/me` | The logged-in user. `401` for missing, invalid or expired tokens. |

### URLs

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/urls` | Body `{original_url, custom_alias?, expires_at?}` → `201`. `422` invalid URL/alias, `409` alias taken. |
| GET | `/api/urls` | Your links, newest first (`limit`, `offset` query params). |
| GET | `/api/urls/{id}` | One of your links. `404` if missing or not yours. |
| DELETE | `/api/urls/{id}` | Deletes the link and its clicks → `204`. |
| GET | `/{short_code}` | Public. `307` redirect and click recorded. `404` unknown/deleted, `410` expired or disabled. |

Aliases: 3–32 characters, letters, digits, `-` and `_`; case-sensitive; names used by the app (`api`, `docs`, `login`, …) are reserved. Only `http://` and `https://` URLs are accepted.

### Analytics

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/analytics/{url_id}` | Everything for one link: summary, timeline, devices, browsers, operating systems, referrers, countries (`days` = 1–365, default 30). |
| GET | `/api/analytics/{url_id}/summary` | `total_clicks`, `clicks_today`, `clicks_this_week`, `clicks_this_month`. |
| GET | `/api/analytics/{url_id}/timeline?days=30` | Clicks per day (days without clicks are included as `0`). |
| GET | `/api/analytics/top-urls?limit=5` | Your most-clicked links. |

Definitions: *today* = since 00:00 UTC; *this week* = the last 7 days; *this month* = the last 30 days. Timeline days are UTC days.

### Notes on the data model

- Short codes and custom aliases share the single `urls.short_code` column (unique index), so a redirect is one lookup; there is no separate `custom_alias` column.
- Indexes: `users.email` (unique), `urls.short_code` (unique), `urls.user_id`, `clicks.url_id`, `clicks.clicked_at`, and `(url_id, clicked_at)` for analytics queries.
- Tables are created by `Base.metadata.create_all()` on startup. This is fine for development; a production system with evolving schemas would add Alembic migrations.
- **Country detection** is behind a small interface (`services/geo.py`). The default implementation reads the `CF-IPCountry` header that Cloudflare adds, only when `TRUST_PROXY_HEADERS=true`. It makes no network calls, so geolocation can never slow down or break a redirect. Locally the country stays empty and the Countries chart is hidden.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `password authentication failed for user "postgres"` | Wrong password in `DATABASE_URL`. |
| `database "urlshortener" does not exist` | Create it (see Database Setup). |
| `connection refused` on port 5432 | Start the PostgreSQL service (Windows **Services** → `postgresql-x64-16`). |
| Backend: `Field required` for `database_url`/`jwt_secret_key` | `backend\.env` is missing or not filled in. |
| Browser shows a CORS error | `FRONTEND_URL` must equal the address in the browser, `http://localhost:5173`. Restart the backend after editing `.env`. |
| `npm run dev` says port 5173 is in use | Close the other process; the port is fixed because CORS expects it. |
| Vite fails with a Node version error | Install Node 20.19+ or 22 LTS. |

## Future Enhancements

- QR code generation for every short link
- Custom domains per user
- Richer link expiration (editing the date, "disable" toggle in the UI) and scheduled cleanup of expired links and old clicks
- Advanced geolocation (GeoIP database such as MaxMind) with city-level analytics
- Rate limiting on login, link creation and redirects
- Redis caching of short code → URL lookups, and background click recording for very high traffic
- Alembic migrations, refresh tokens / httpOnly cookies, email verification and password reset
- Bulk import/export and CSV download of analytics
