# DocuFlow

**Multi-tenant document management backend with built-in RAG** — upload a PDF, and ask questions about it in natural language. Answers are grounded in your own tenant's documents and streamed back token by token.

![CI](https://github.com/MuhammadHaider1/docuflow-backend/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

Upload a PDF → a Celery worker extracts the text → chunks it → generates 384-dimensional
embeddings → stores them in **pgvector**. Then `POST /rag/query` runs a cosine-similarity
search scoped to your organization, feeds the top chunks to Gemini, and streams the answer back.

> **Solo project** — architecture, backend, RBAC, the RAG pipeline, deployment and
> production debugging were all done by me.

---

## Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [The RAG pipeline](#the-rag-pipeline)
- [Multi-tenancy & RBAC](#multi-tenancy--rbac)
- [Production debugging](#production-debugging)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Setup](#setup)
- [API surface](#api-surface)
- [Testing & CI](#testing--ci)
- [Security](#security)
- [Roadmap](#roadmap)

---

## What it does

| Capability | Detail |
|---|---|
| **Multi-tenant SaaS** | Organizations, memberships, and every resource scoped by `X-Organization-Id` |
| **RAG over your documents** | Semantic search + grounded answers, **tenant-isolated** at the SQL level |
| **Streaming answers** | Server-Sent-Events style `text/plain` stream via `StreamingResponse` |
| **RBAC** | 7 roles, 11 permissions, 51 role→permission links, enforced by a reusable dependency |
| **Async document processing** | Celery + Redis; PDF text extraction never blocks a request |
| **Versioned storage** | `Document` + `DocumentVersion` lineage, objects in MinIO (S3-compatible) |
| **Hierarchical folders** | Nested parent/child tree, cascade-safe deletes |
| **Audit log** | Async trail of actor, action, entity, IP and JSONB detail |
| **Notifications** | Per-user read/unread with bulk operations |
| **Rate limiting** | SlowAPI, e.g. 30 req/min on RAG endpoints |

**Scale:** 4,200+ lines across 71 Python files · 10 routers · 10 model modules · 7 Alembic migrations.

---

## Architecture

Layered, so a request never skips straight to the database:

```
                         ┌──────────────────────────────┐
   HTTP request  ───────►│  API        src/api/v1       │  routing, auth deps,
                         │              PermissionChecker│  rate limiting
                         └───────────────┬──────────────┘
                                         ▼
                         ┌──────────────────────────────┐
                         │  SERVICES    src/services    │  business logic,
                         │              RAGService      │  storage, AI calls
                         └───────┬──────────────┬───────┘
                                 ▼              ▼
              ┌──────────────────────┐   ┌──────────────────────┐
              │ REPOSITORIES         │   │ TASKS    src/tasks   │
              │ src/repositories     │   │ Celery: PDF → chunk  │
              │ per-entity queries   │   │ → embed → pgvector   │
              └──────────┬───────────┘   └──────────┬───────────┘
                         ▼                          ▼
              ┌────────────────────────────────────────────┐
              │  PostgreSQL + pgvector   │   Redis   MinIO  │
              │  asyncpg / SQLAlchemy 2.0 │  broker   S3     │
              └────────────────────────────────────────────┘
```

### Two details worth calling out

**CPU-bound work is pushed off the event loop.** Embedding generation is synchronous and
blocking, but it runs inside an async request path. Rather than stalling every concurrent
request, `RAGService` hands it to a thread pool:

```python
loop = asyncio.get_running_loop()
embeddings = await loop.run_in_executor(
    None, self.embedding_service.get_embeddings_batch, raw_chunks
)
```

**RAG is tenant-isolated in SQL, not in Python.** The organization filter is part of the
`WHERE` clause, so a missing application-level check cannot leak another tenant's chunks:

```python
stmt = (
    select(DocumentChunk)
    .join(Document, DocumentChunk.document_id == Document.id)
    .where(Document.organization_id == org_id)          # ← tenant boundary
    .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
    .limit(limit)
)
```

---

## The RAG pipeline

### Ingestion — `POST /documents` triggers a Celery task

```
PDF uploaded
   └─► process_document_task              (Celery, max_retries=3, 5s backoff)
          ├─ minio.stat_object()          verify the object really exists
          ├─ PdfReader().pages            extract text per page (pypdf)
          ├─ chunk_text(500, overlap 50)   sliding window
          ├─ SentenceTransformer           all-MiniLM-L6-v2 → 384-d vectors
          └─ INSERT documentchunk         embedding column (pgvector)
```

Retries are bounded: on the final attempt the document is marked `failed` instead of
retrying forever, and the error is re-raised so it is not silently swallowed.

### Query — `POST /api/v1/rag/query`

```
question
  ├─ embed the question              → 384-d vector
  ├─ top-3 cosine neighbours         → filtered by organization_id
  ├─ build a grounded prompt         → "answer only from this context"
  └─ Gemini  models/gemini-3.6-flash → answer
```

`POST /api/v1/rag/query-stream` is identical but yields chunks as they arrive.

**Resilience.** Gemini returns 503 under load, which would otherwise surface as a failed
request. `_call_gemini_stream` wraps the call in `tenacity` with exponential backoff
(3 attempts, 2–6s) and retries only on `ServerError`, so a genuine bad request is not
retried three times. The streaming path degrades to an explanatory notice rather than a
broken connection.

**Model caching.** The embedding model is resolved by `EMBEDDING_MODEL_PATH` first and only
falls back to the HuggingFace hub id when that directory is missing. Offline flags are
applied **only** in the local case — see the debugging notes below.

---

## Multi-tenancy & RBAC

7 seeded roles over 11 permissions (51 role→permission links):

| Role | Permissions | Intent |
|---|---|---|
| `Super Admin` | 11 | Platform-wide |
| `Platform Admin` | 11 | Platform-wide |
| `Organization Owner` | 11 | Owns the tenant, manages members and roles |
| `Workspace Admin` | 8 | Manages documents and folders |
| `Contributor` | 5 | Creates and edits content |
| `Reviewer` | 3 | Reads and comments |
| `Viewer` | 2 | Read-only |

Enforcement is a dependency, so it is impossible to forget at a route:

```python
async def create_document(
    _: bool = Depends(PermissionChecker("document:create")),
    ...
)
```

`PermissionChecker` **fails closed** — an unknown permission is a 403, never a pass. Seeding
is idempotent, so it is safe to re-run on every deploy, and it reports loudly on a
permission referenced by a role but missing from the catalogue instead of skipping it.

---

## Production debugging

Four bugs found and fixed while deploying this to Azure. Each is a commit, and each has a
regression test.

**1. `pg_hba.conf` trusted every local connection.** The password was correct and still
irrelevant — Postgres was configured with `trust` for loopback, so *any* password connected
successfully. Found by testing that an old password still worked after rotating it. Fixed by
switching to `scram-sha-256`, and both Postgres and Redis were rebound from `0.0.0.0` to
`127.0.0.1`.

**2. A failed model load poisoned the singleton forever.** `EmbeddingService` cached itself
in `__new__` *before* the model had loaded. The first load failed, but the half-initialised
instance stayed in `_instance`, so every later call reused the broken object instead of
retrying. The visible error was always a HuggingFace connection error, which hid the fact
that the API key was also missing. Fixed by memoising only after a successful load.

**3. Offline mode was forced at import time.** `document_tasks.py` and
`embedding_service.py` both set `HF_HUB_OFFLINE=1` on import, so the model could never be
downloaded in the first place. Offline flags are now applied only when a local model
directory actually exists.

**4. The org creator was given the weakest role.** `register_new_organization` looked up
`"Viewer"`, while the comment above it said "Get Admin role" and the error message said
`'Member' does not exist`. Whoever created an organization ended up unable to manage
members, documents or roles — unable to administer their own tenant. The test suite missed it
because the assertions were `assert response.status_code in [200, 400, 404, 422, 500]`,
which passes for almost any response. Fixed, and the test now asserts the exact role id;
it was verified to fail against the old code.

**5. A live endpoint returned 422 to every caller.** `GET /comments/documents/{document_id}/comments`
declared its path parameter as `doc_id`, so FastAPI treated the id as a *required query
parameter* and the endpoint could never succeed. The test for it had been pointed at
`/api/v1/comments/`, a path that does not exist, and asserted the 404 — a green test that
exercised nothing. Both are fixed: the parameter is named correctly, the tests call real
routes, and a tenant-isolation test now proves another tenant's document returns 404.

---

## Tech stack

| Layer | Choice |
|---|---|
| API framework | FastAPI 0.139, Starlette, Uvicorn (uvloop/httptools) |
| Data | PostgreSQL 15 + **pgvector**, SQLAlchemy 2.0 async, asyncpg |
| Migrations | Alembic (7 revisions) |
| Validation | Pydantic v2, pydantic-settings |
| Auth | JWT (PyJWT), Argon2 via `pwdlib`, FastAPI dependencies |
| Vector search | pgvector cosine distance, `sentence-transformers` MiniLM (384-d) |
| LLM | Google Gemini (`google-genai`) with `tenacity` backoff |
| Background work | Celery + Redis, `pypdf` for extraction |
| Object storage | MinIO (S3-compatible) via `minio` / `aioboto3` |
| Rate limiting | SlowAPI |
| Tests | pytest, pytest-asyncio, httpx |
| Lint | ruff (lint + format) |

---

## Project structure

```
docuflow-backend/
├── .github/workflows/ci.yml      # lint, tests, secret scan
├── docker/                       # FastAPI & Celery Dockerfiles
├── docker-compose.yml            # postgres+pgvector, redis, minio
├── migrations/versions/          # 7 Alembic revisions
├── requirements.txt              # runtime deps
├── requirements-dev.txt          # test + lint tooling
├── requirements-rag.txt          # optional ~2 GB PyTorch stack
├── scripts/                      # manual dev utilities (need a live DB)
├── src/
│   ├── main.py                   # app, lifespan, routers, limiter
│   ├── core/                     # config, database, security, seeding, limiter
│   ├── api/v1/                   # 10 routers incl. rag.py
│   ├── models/                   # SQLAlchemy models (chunks.py holds pgvector)
│   ├── repositories/             # data access, one module per entity
│   ├── schemas/                  # Pydantic request/response models
│   ├── services/                 # business logic, RAG, embedding, storage
│   ├── tasks/                    # Celery app + document pipeline
│   └── utils/chunking.py         # sliding-window splitter
└── tests/                        # pytest suite, 79 tests (statement-aware fake DB)
```

---

## Setup

**Prerequisites:** Python 3.12+, Docker & Docker Compose.

```bash
git clone https://github.com/MuhammadHaider1/docuflow-backend.git
cd docuflow-backend

python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env        # then edit: SECRET_KEY + GOOGLE_API_KEY
```

Generate a real signing key:

```bash
openssl rand -hex 32
```

Start the infrastructure. Host ports match `.env.example`:

```bash
docker compose up -d
```

| Service | Host port | Notes |
|---|---|---|
| PostgreSQL + pgvector | `5432` | needs the `vector` extension — the image ships it |
| Redis | `6380` | Celery broker |
| MinIO API | `9100` | |
| MinIO console | `9101` | <http://localhost:9101> |

Then initialise the database. **Use one of these, not both** — they create the same tables
and running them together will conflict:

```bash
# Option A — create the schema from the models and seed RBAC
python init_db.py

# Option B — or apply the 7 Alembic revisions instead
alembic upgrade head
```

Start the API and the worker:

```bash
uvicorn src.main:app --reload
celery -A src.tasks.celery_app.app worker --loglevel=info
```

API docs: <http://localhost:8000/docs>

### Enabling the RAG features

The core API runs without them. To ingest vectors and answer questions:

```bash
pip install -r requirements-rag.txt
```

Set `GOOGLE_API_KEY` in `.env`. If you want the embedding model served from disk instead of
downloaded on first use, place it at `EMBEDDING_MODEL_PATH` (default
`models/all-MiniLM-L6-v2`) and the app will never contact HuggingFace.

---

## API surface

All routes are prefixed `/api/v1`. Requests need `Authorization: Bearer <token>`, and
tenant-scoped requests need an `X-Organization-Id` header.

| Module | Endpoints |
|---|---|
| **Auth** | `POST /auth/register`, `/auth/login`, `/auth/refresh` |
| **Organizations** | list / create / get / update / delete, add members |
| **Documents & folders** | CRUD, nested folder tree, version history, download |
| **RBAC** | `GET /roles`, `GET /permissions`, assign / revoke / read member role |
| **RAG** | `POST /rag/query`, `POST /rag/query-stream` |
| **Comments** | CRUD |
| **Audit** | `GET /audit` |
| **Notifications** | CRUD, read/unread, bulk mark-read |
| **Admin** | `/admin` |

```bash
# ask a question about your documents
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-Id: $ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{"query": "What database does this project use?"}'
```

---

## Testing & CI

```bash
pytest              # 79 tests
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
```

Tests run against a mocked async DB session, so **no PostgreSQL, Redis or MinIO is needed**
to run the suite — which is what makes it usable in CI.

GitHub Actions runs on every push and PR to `main`:

- **Lint** — `ruff check` and `ruff format --check`
- **Tests** — full suite on a clean environment
- **Secret scan** — fails if a `.env` was ever committed, or if a Google API key /
  HuggingFace token / private key appears in the tree

That last job exists because this project has actually leaked a key once. It has been
rotated, and the check is there to stop it happening again.

---

## Security

- `.env` is git-ignored and has never been committed; CI enforces this.
- Passwords are hashed with Argon2. `SECRET_KEY`, the database password, the MinIO keys and
  the Gemini key have all been rotated off their defaults.
- Postgres and Redis bind to `127.0.0.1` only; only SSH and the API port are exposed.
- RAG queries require `document:read` and are rate limited to 30/min.
- Authorization is deny-by-default.

> **Deployment note:** the Azure instance runs behind a private HTTPS tunnel rather than a
> public port, and the API binds to loopback behind it. Postgres, Redis and MinIO are not
> reachable from the internet.

---

## Roadmap

- [ ] Replace the hard-coded Celery broker URL with a setting
- [ ] Real integration tests against a live Postgres + pgvector instance
- [ ] TLS via a real domain instead of the tunnel
- [ ] OCR for scanned PDFs (`pypdf` only reads text layers)
- [ ] Presigned upload/download URLs that work outside the host
- [ ] Hybrid retrieval (BM25 + vector) and a re-ranker
- [ ] Container images for the API and worker
- [ ] Rate-limit and audit-log dashboards

---

## License

MIT — see [LICENSE](LICENSE).
