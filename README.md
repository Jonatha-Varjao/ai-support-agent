# AI Support Agent — Mission

A web application with an LLM-powered support agent for Mission, with an admin dashboard for managing the knowledge base.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14, FastAPI, SQLAlchemy 2 (async), asyncpg, Alembic |
| Database | PostgreSQL 17 + pgvector (RAG) |
| Frontend | React 19, Vite, TypeScript, TanStack Query, Zustand, Tailwind v4 |
| Auth | httpOnly cookies + JWT (HS256) |
| LLM | Gemini 2.0 Flash (provider-swappable; Google `google-genai` SDK) |
| MCP | `fastmcp` server + Playwright (headless Chromium) for `web_fetch` |
| Observability | MLflow (tracing server, shared Postgres backend) |
| Container | Docker Compose (4 services: db, api, mcp, web) |
| Tooling | `uv` (Python), `bun` (JS), `ruff`, `eslint`, `prettier` |

## Repo structure

```
ai-support-agent/
├── apps/
│   ├── api/                # FastAPI backend
│   └── web/                # React SPA
├── services/
│   └── mcp/                # fastmcp server (web_fetch)
├── infra/                  # Dockerfiles + docker-compose.yml
├── specs/                  # (gitignored) planning docs
└── .env.example            # all env vars
```

## How to run locally

### Prereqs
- Docker + Docker Compose
- A Gemini API key

### Steps

1. `cp .env.example .env` and fill in:
   - `GEMINI_API_KEY` — your Gemini key
   - `JWT_SECRET` — any random 32+ byte string
   - `ADMIN_EMAIL` — the email that gets `admin` role on first login

2. `docker compose -f infra/docker-compose.yml up --build`

3. Wait for the healthchecks to pass (~30s). Services:
   - Web: `http://localhost:5173`
   - API: `http://localhost:8000`
   - MLflow UI: `http://localhost:5000`
   - MCP: internal (not exposed to host)

4. Open `http://localhost:5173`. Enter any email. The admin email becomes an `admin` role automatically.

## Mandatory features

| # | Requirement | Status |
|---|---|---|
| 1 | Email login (no password, no social) | Done |
| 2 | ChatGPT-style chat interface (send, view replies, continue conversation, multi-thread sidebar) | Done |
| 3 | Knowledge base for Mission | Done (backend RAG; frontend renders streamed answers) |
| 4 | Admin dashboard to manage KB content | Done `/admin/kb` (CRUD via drawer) |
| 5 | Log of unanswered questions | Done `/admin/unanswered` |
| 6 | MCP integration (external web fetch) | Done (backend MCP server with Playwright; sync 20s timeout) |
| 7 | Per-user memory (threads tied to email) | Done |

## Bonus features

| # | Bonus | Status |
|---|---|---|
| 1 | Agent observability (KPI page) | Pending backend endpoint |
| 2 | Response cache (semantic) | Done (backend; frontend surfacing planned) |
| 3 | Human handoff | Done `/admin/handoffs` (status transitions) |

## Admin

After logging in with the email set in `ADMIN_EMAIL`, you'll see an "Admin" link in the sidebar. The admin dashboard has 3 tabs:

- **Base de conhecimento** — CRUD on the 5 KB categories (product, service, flow, institutional, faq).
- **Não respondidas** — questions the agent failed to answer (low confidence or no KB match). Mark resolved to clear them.
- **Handoffs** — user requests for human support. Mark contacted or closed.

New KB entries become searchable in the next chat. Unanswered and handoff entries are created by the backend automatically.

## Notes for reviewers

- The frontend reads from the backend over httpOnly cookies. No token handling in the JS bundle.
- The chat streams via SSE — the network panel will show a long-lived `text/event-stream` response when a message is sent.
- MLflow traces every chat turn. The trace UI at `:5000` shows the full span tree (embed → cache → RAG → LLM → MCP).
- The MCP `web_fetch` tool is invoked when the user asks in a "fetch the site" style; the agent auto-detects keywords like "acesse", "visite", "site da mission".
- The backend's semantic cache surfaces via the `done.cached` flag on the SSE event; the LLM call is skipped on cache hit.
