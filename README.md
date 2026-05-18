#⬡ GeoAnalytica
### Global data, decoded.

A full-stack geospatial analysis platform that lets you query global data in plain English, visualize it on an interactive world map, and export AI-powered reports — with zero API keys required on the free tier.

---

## Features

| Feature | Free Tier | Pro Tier |
|---|---|---|
| Natural language queries | ✓ | ✓ |
| Interactive choropleth map | ✓ | ✓ |
| World Bank & IMF data | ✓ | ✓ |
| AI-powered summaries (Claude) | ✓ | ✓ |
| Statistical analysis & outliers | ✓ | ✓ |
| Timeline animation | ✓ | ✓ |
| Threshold alerts | ✓ | ✓ |
| CSV / Excel / PDF / JSON export | ✓ | ✓ |
| Queries per day | 20 | Unlimited |
| Fields per query | 5 | Unlimited |
| Direct API connections | — | ✓ |
| Real-time data | — | ✓ |

---

## Project Structure

```
geoanalytica/
├── docker-compose.yml          # All services orchestrated
├── .env.example                # Environment template
├── nginx.conf                  # Reverse proxy config
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                # Database migrations
│   └── app/
│       ├── main.py             # FastAPI entrypoint
│       ├── config.py           # Pydantic settings
│       ├── database.py         # Async SQLAlchemy
│       ├── models/             # SQLAlchemy ORM models
│       ├── schemas/            # Pydantic v2 schemas
│       ├── routers/            # FastAPI route handlers
│       ├── services/           # Business logic
│       │   ├── web_intelligence_engine.py  # 8-step scraping pipeline
│       │   ├── query_parser.py             # Claude-powered NL parsing
│       │   ├── analysis_engine.py          # Stats, outliers, clustering
│       │   ├── ai_narrative.py             # Claude summary generation
│       │   └── export_service.py           # CSV/Excel/PDF/JSON export
│       ├── workers/            # Celery tasks
│       └── utils/              # Geo data, field catalog, helpers
└── frontend/
    ├── index.html              # Landing page
    ├── login.html / register.html
    ├── dashboard.html          # Project management
    ├── analysis.html           # 3-column analysis workspace
    ├── results.html            # Full results dashboard
    ├── settings.html           # API keys & preferences
    ├── alerts.html             # Alert management
    ├── css/                    # Component-based CSS (no framework)
    └── js/                     # Vanilla ES6 modules
```

---

## Quick Start (Docker)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 4.0+
- [Git](https://git-scm.com/)
- An [Anthropic API key](https://console.anthropic.com/)

### Step 1 — Clone and configure

```bash
git clone https://github.com/your-org/geoanalytica.git
cd geoanalytica
cp .env.example .env
```

### Step 2 — Generate security keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Generate ENCRYPTION_KEY (Fernet)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste both into your `.env` file.

### Step 3 — Add your Anthropic API key

Edit `.env` and set:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

The platform works without this key but AI summaries and NL query parsing will be disabled.

### Step 4 — Build and start

```bash
docker-compose up --build
```

This starts:
- **PostgreSQL 15** with PostGIS on port 5432
- **Redis 7** on port 6379
- **FastAPI** backend (proxied via Nginx)
- **Celery worker** (4 concurrent workers)
- **Celery beat** (scheduled alerts & exports)
- **Nginx** serving frontend on port 80

### Step 5 — Run database migrations

```bash
docker-compose exec backend alembic upgrade head
```

### Step 6 — Access the app

Open **http://localhost** in your browser.

Register a new account and start analyzing!

---

## Running Without Docker

### Prerequisites
- Python 3.11+
- PostgreSQL 15 with PostGIS extension
- Redis 7
- Node.js (not needed — no build step)

### Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium --with-deps

# Create .env (edit with your values)
cp ../.env.example .env

# Set DATABASE_URL to your local Postgres
# e.g. postgresql+asyncpg://postgres:password@localhost:5432/geoanalytica

# Create database
createdb geoanalytica

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Workers setup (new terminal)

```bash
cd backend
source venv/bin/activate

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

# Start Celery beat (separate terminal)
celery -A app.workers.celery_app beat --loglevel=info
```

### Frontend setup

The frontend is pure static HTML/CSS/JS with no build step.

**Option A — Serve via Python:**
```bash
cd frontend
python -m http.server 3000
```
Open http://localhost:3000 — but API calls will fail (CORS). Use the Nginx approach below for development.

**Option B — Nginx (recommended):**
Install Nginx locally and point it at your `frontend/` directory with the proxy config from `nginx.conf`.

**Option C — Update API base URL:**
In `frontend/js/core/api.js`, change:
```js
base: '/api',
```
to:
```js
base: 'http://localhost:8000/api',
```
Then open `frontend/index.html` directly in your browser.

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✓ | PostgreSQL connection string (asyncpg) |
| `REDIS_URL` | ✓ | Redis connection URL |
| `SECRET_KEY` | ✓ | JWT signing key (32+ char hex) |
| `ENCRYPTION_KEY` | ✓ | Fernet key for API key encryption |
| `ANTHROPIC_API_KEY` | Recommended | Enables AI parsing & summaries |
| `ALLOWED_ORIGINS` | ✓ | CORS origins (JSON array) |
| `SMTP_*` | Optional | Email alert notifications |
| `BRAVE_API_KEY` | Optional | Improves web scraping quality |
| `SERP_API_KEY` | Optional | Google Trends data |

---

## Data Sources (Free Tier)

No API keys required:

| Source | Data |
|---|---|
| World Bank API | GDP, inflation, unemployment, demographics |
| IMF DataMapper | Macroeconomic indicators |
| OECD Stats | Advanced economy data |
| Open-Meteo | Climate and weather |
| REST Countries | Country metadata |
| Wikipedia | Country infoboxes |
| UN Data | Population statistics |

---

## Optional API Key Integrations (Pro Tier)

| Service | Unlocks | Free Key? |
|---|---|---|
| Alpha Vantage | Stock prices, forex, US economic data | ✓ |
| NewsAPI | 70,000+ news sources | ✓ |
| OpenWeatherMap | Current weather & forecasts | ✓ |
| Brave Search | Better web scraping coverage | ✓ |
| SerpAPI | Google Trends data | Paid |
| Mapbox | Premium map tiles | ✓ (free tier) |

---

## System Architecture & Subscription Flow

GeoAnalytica features a decoupled, production-grade asynchronous architecture with built-in subscription tier management, robust query gating, and secure field-level encryption.

### High-Fidelity Architecture Diagram

```
+-----------------------------------------------------------------------------------------+
|                                     FRONTEND PORTAL                                     |
|               HTML5 / Component-based CSS / Vanilla ES6 Javascript UI                   |
|       (Leaflet.js Choropleth Maps · Chart.js Time-Series · Tabulator Data Tables)       |
+-----------------------------------------------------------------------------------------+
       |                                                                           ^
       | [HTTP/REST API Requests]                                                  | [WebSockets]
       v                                                                           |
+-----------------------------------------------------------------------------------------+
|                                  NGINX REVERSE PROXY                                    |
|              - Proxies standard REST endpoints to uvicorn ASGI server                   |
|              - Orchestrates real-time bi-directional WebSocket pipelines               |
+-----------------------------------------------------------------------------------------+
       |
       v
+-----------------------------------------------------------------------------------------+
|                                    FASTAPI BACKEND                                      |
+-----------------------------------------------------------------------------------------+
|  [Security & Authentication Middleware]                                                 |
|    - OAuth2 Bearer Tokens (JWT verification via dependencies.py)                       |
|    - AES-256 Symmetric Field Encryption (Fernet-backed encryption_service.py)           |
|                                                                                         |
|  [Subscription & Gating Controller]                                                     |
|    - Tier limits mapping (TIER_LIMITS config policy: Free vs Pro)                       |
|    - Active rate limiter: check_query_limit (daily quota, fields/query, active user check)|
|    - User operations & self-service upgrades (/api/users/me/upgrade)                    |
|    - Admin user/tier control suite (/api/admin/users)                                   |
|                                                                                         |
|  [Async Pipeline Dispatcher]                                                            |
|    - Non-blocking project & query orchestration logic                                    |
|    - WebSocket connection manager for live state and query progress updates             |
+-----------------------------------------------------------------------------------------+
       |                                           |                               ^
       | [Read/Write State]                        | [Queue Tasks]                 | [Push Updates]
       v                                           v                               |
+------------------+                       +---------------+                       |
|    POSTGRESQL    |                       |  REDIS CACHE  |                       |
|    (PostGIS)     |                       |  & MQ BROKER  |                       |
+------------------+                       +---------------+                       |
       ^                                           |                               |
       |                                           v                               |
       |                                   +---------------+                       |
       | [Fetch State & Persist Result]    | CELERY WORKER |                       |
       +-----------------------------------| (run_async)   |-----------------------+
                                           +---------------+
                                                   |
                                                   v
                                           +---------------------------------------+
                                           |        WEB INTELLIGENCE ENGINE        |
                                           |  - Natural Language Parser (Claude)   |
                                           |  - Asynchronous Parallel Fetchers     |
                                           |  - Stats & Outliers Analytics Engine  |
                                           |  - AI Narrative summarization (Claude)|
                                           +---------------------------------------+
```

### Query & Subscription Gating Pipeline

1. **User Request**: The user submits a Natural Language geospatial request in the frontend workspace.
2. **Identity Verification**: FastAPI validates the incoming JSON Web Token (JWT) signature.
3. **Tier Limits Check**: The `check_query_limit` guard intercepts the query:
   - Fetches the user's active tier (`free` or `pro`).
   - Counts total queries processed for the current day.
   - Compares total fields parsed against the tier's configuration (e.g. max 5 fields for Free, 20 for Pro).
   - If limits are reached, immediately returns `429 Too Many Requests` with dynamic tier upgrade pathways.
4. **Asynchronous Execution**: Celery worker schedules the parsing, fetching, merging, statistical outlier checks, and Claude AI summary generations.
5. **Real-time Streaming**: Results are saved and broadcasted to the browser via dedicated WebSockets.

---

## System Verification Proof (Screenshots)

Below is the step-by-step visual proof demonstrating the robustness, visual premium aesthetics, project opening, and self-service subscription flows.

### 1. Unified Dashboard
![Login & Dashboard Overview](images/01_login_dashboard.png)
*Figure 1: Premium Dark Theme Dashboard showing total project statistics, daily query metrics with progress bars, connected API keys, active alerts, and recent query history.*

### 2. Project Opening & Geospatial Workspace
![Analysis Workspace](images/02_analysis_workspace_pro.png)
*Figure 2: Fully interactive geospatial workspace displaying dynamic Choropleth maps, timeline animators, customizable field selections, and active user query results.*

### 3. Smart Query Builder & Natural Language Input
![Query Builder Workspace](images/03_query_builder.png)
*Figure 3: Natural language geospatial instruction box where plain English queries are converted to production analytical queries.*

### 4. Pro Plan Account settings
![Pro Settings Overview](images/04_pro_settings_overview.png)
*Figure 4: Account settings view displaying dynamic API connections, security keys manager, and subscription statistics indicating active Pro plan.*

### 5. Plan Downgrade Flows (Dynamic Confirmation)
![Downgrade Modal Confirm](images/05_downgrade_modal_confirm.png)
*Figure 5: Integrated self-service downgrade mechanism featuring custom confirmation dialogs prompting the user about the transition down to standard Free limits.*

### 6. Free Tier Comparison Card
![Free Tier Comparison](images/06_free_tier_comparison.png)
*Figure 6: Rebuilt dynamic tier card displaying exact limit statistics, feature comparisons, and a prominent 'Upgrade to Pro' self-service button.*

### 7. Upgrading to Premium Tier (Dynamic Action)
![Upgrade Action Trigger](images/07_upgrade_trigger_flow.png)
*Figure 7: Clicking upgrade securely calls `/api/users/me/upgrade` in real-time, displaying crisp notifications and refreshing the state.*

### 8. Upgraded Pro Plan Status
![Upgraded Back to Pro](images/08_upgraded_back_pro.png)
*Figure 8: Account dashboard reflecting the successful transition back to Pro plan, displaying updated limit cards (500 queries/day, 20 fields/query, 500K rows).*

### 9. Alert Management Suite
![Alerts Management Suite](images/09_alerts_gating_interface.png)
*Figure 9: Fully structured alert console showing automated system triggers, checks, thresholds, and slack/email integration status.*

### 10. Robust Workspace Operations
![Workspace Loading Successful](images/10_project_opening_successful.png)
*Figure 10: Smooth transition and project load flow. Dynamic page-detection prevents erroneous page routing, ensuring project loads correctly.*

### 11. Premium Data Enrichment
![Premium AI Summaries Unlocked](images/11_premium_features_unlocked.png)
*Figure 11: Decoded data points, charts, outlier matrices, and premium Claude AI narratives unlocked on the Pro plan.*

---

## Troubleshooting

**`alembic upgrade head` fails with "extension postgis does not exist"**
```bash
docker-compose exec postgres psql -U postgres -d geoanalytica -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

**Playwright chromium fails to install in Docker**
The Dockerfile runs `playwright install chromium --with-deps`. If it fails, try:
```bash
docker-compose exec backend playwright install chromium
```

**WebSocket connection fails**
Check that `nginx.conf` has the WebSocket upgrade headers. Also ensure your browser supports WebSockets (all modern browsers do).

**`ENCRYPTION_KEY` error on startup**
Generate a proper Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Paste the output into `.env` as `ENCRYPTION_KEY=`.

**Celery tasks not running**
Check the worker logs:
```bash
docker-compose logs worker
```
Ensure Redis is healthy:
```bash
docker-compose exec redis redis-cli ping
```

**Frontend shows "Network error"**
The frontend expects the API at `/api/`. If you're opening HTML files directly (not via Nginx), update `js/core/api.js` to use the full backend URL.

**Free tier limit hit (429 error)**
Your account hit 20 queries/day. Wait until midnight UTC or upgrade to Pro.

---

## API Documentation

Once running, visit:
- **Swagger UI:** http://localhost/api/docs
- **ReDoc:** http://localhost/api/redoc

---

## Technology Credits

- **FastAPI** — Modern Python web framework
- **Leaflet.js** — Interactive maps
- **Chart.js** — Data visualizations
- **Tabulator.js** — Data tables
- **Claude (Anthropic)** — AI query parsing & narrative generation
- **World Bank Open Data** — Economic indicators
- **CartoDB** — Map tile layers
- **PostGIS** — Geospatial database extension

---

## License

MIT License — see LICENSE file for details.

---

*Built with love and chai — GeoAnalytica, 2026*
