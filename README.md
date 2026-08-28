# DocuFlow Backend API

> Enterprise-grade asynchronous **document management** and **notification processing** backend, purpose-built for **multi-tenant** SaaS workflows and designed to evolve into an **AI-powered document intelligence platform**.

Built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0 (Async)**, **Alembic**, **Redis/Celery**, and **MinIO (S3-compatible object storage)**.

---

## ✨ Highlights

- **Multi-Tenant SaaS Architecture** — Organizations, memberships, and organization-scoped resources with `UUID` primary keys and `X-Organization-Id`-aware isolation.
- **JWT Authentication & Authorization** — Access + refresh token flow with Argon2/bcrypt password hashing via `pwdlib`.
- **Role-Based Access Control (RBAC)** — `Role`, `Permission` and `RolePermission` (many-to-many) models with organization-scoped roles and member role assignment/revocation.
- **Hierarchical Document Management** — Folders (nested parent/child trees) and `Document` + `DocumentVersion` models supporting multi-version document lineage.
- **Background Intelligence** — Celery + Redis workers offload heavy document processing (e.g., PDF text extraction via `pypdf`) without blocking API threads.
- **Compliance-Grade Audit Logging** — Asynchronous event-driven audit trail capturing action, entity, user, IP, and JSONB details.
- **Notification System** — Read/unread + bulk notification operations per user.
- **Object Storage** — MinIO (S3-compatible) integration with automatic bucket initialization.
- **API Rate Limiting** — SlowAPI middleware protecting endpoints.
- **Versioned DB Migrations** — Alembic for reproducible PostgreSQL schema evolution.

---

## 🧠 AI & Vector Search (Planned / Roadmap)

Docuflow is architected to grow into an intelligent document platform. The following **AI-driven capabilities are designed into the architecture and are on the roadmap**:

- **Vector Search RAG Integration** — An enterprise Retrieval-Augmented Generation (RAG) pipeline using **pgvector** and **LangChain**, enabling semantic search, dynamic text chunking, and context-aware question-answering over multi-tenant document stores.
- **Async Background Intelligence** — Extending Celery+Redis workers to run background **OCR**, automated text extraction, and **vector embedding generation** without blocking core API threads.
- **Smart Document Insights** — LLM-powered summarization, entity extraction, and intelligent document classification built on the existing `extracted_content` pipeline.
- **Context-Aware QA** — Chat-style question answering grounded in an organization's own document corpus (retrieval over tenant-isolated vector indexes).

> The existing `processing_status` lifecycle, `extracted_content` column, Celery task orchestration, and MinIO object pipeline lay the foundation for these AI features.

---

## 🏗️ Architecture

The codebase follows a clean **layered architecture** separating concerns across the request path:

```
HTTP Request
   │
   ▼
┌──────────────┐   FastAPI Routers (src/api/v1) — routing + auth deps
│     API      │
└──────┬───────┘
       ▼
┌──────────────┐   Business logic (src/services)
│  SERVICES    │   orchestrates repositories, storage & tasks
└──────┬───────┘
       ▼
┌──────────────┐   Data access (src/repositories)
│ REPOSITORIES │   isolated DB queries per entity
└──────┬───────┘
       ▼
┌──────────────┐   SQLAlchemy 2.0 async models (src/models)
│   MODELS     │   PostgreSQL + asyncpg
└──────────────┘
```

**Async Background Layer:** `src/tasks` — Celery worker executes heavy document workloads (e.g., `process_document_task`) decoupled from the request cycle.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) |
| **Database** | PostgreSQL + [SQLAlchemy 2.0 (Async)](https://www.sqlalchemy.org/) + [asyncpg](https://github.com/MagicStack/asyncpg) |
| **Migrations** | [Alembic](https://alembic.sqlalchemy.org/) |
| **Validation** | Pydantic v2 / Pydantic-Settings |
| **Auth** | JWT (python-jose), `pwdlib` (Argon2/bcrypt) |
| **Caching / Broker** | Redis |
| **Task Queue** | Celery |
| **Object Storage** | MinIO (S3-compatible) via `aioboto3` + `minio` |
| **Rate Limiting** | SlowAPI |
| **Containerization** | Docker & Docker Compose |
| **Server** | Uvicorn (+ uvloop/httptools) |
| **Testing** | pytest |
| **Linting** | ruff |

---

## 📁 Project Structure

```
docuflow-backend/
├── docker/
│   ├── fastapi.Dockerfile
│   └── celery.Dockerfile
├── docker-compose.yml          # postgres + redis + minio
├── alembic.ini
├── migrations/                 # Alembic versioned schema
├── src/
│   ├── main.py                 # App factory, lifespan, routers, rate limiter
│   ├── core/
│   │   ├── config.py           # Pydantic-settings (env-driven)
│   │   ├── database.py         # Async engine + session factory
│   │   ├── security.py         # JWT creation/decode + auth dependency
│   │   ├── minio.py            # MinIO client singleton
│   │   ├── limiter.py          # SlowAPI rate limiter
│   │   ├── seeding.py          # Default role/permission seeding
│   │   └── exceptions.py
│   ├── api/v1/
│   │   ├── auth.py             # /auth (register, login, refresh)
│   │   ├── organizations.py    # /organizations
│   │   ├── documents.py        # /documents, /folders
│   │   ├── rbac.py             # /roles, /permissions, member roles
│   │   ├── comment.py          # /comments
│   │   ├── audit.py            # /audit
│   │   ├── notification.py     # /notifications
│   │   └── admin.py
│   ├── models/                 # SQLAlchemy async models
│   │   ├── auth.py             # User, RefreshToken
│   │   ├── organization.py     # Organization, Membership
│   │   ├── document.py         # Folder, Document, DocumentVersion
│   │   ├── rbac.py             # Role, Permission, RolePermission
│   │   ├── audit.py            # AuditLog (JSONB)
│   │   ├── comment.py
│   │   └── notification.py
│   ├── repositories/           # Data-access layer
│   ├── schemas/                # Pydantic request/response models
│   ├── services/               # Business-logic layer (incl. storage.py)
│   └── tasks/
│       ├── celery_app.py       # Celery app (Redis broker/backend)
│       ├── document_tasks.py   # process_document_task (PDF text extraction)
│       ├── processing.py       # AI/OCR/embedding pipeline (planned)
│       └── emails.py
└── tests/                      # pytest (auth, comments, documents)
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (recommended for full stack) **or** a local PostgreSQL, Redis, and MinIO instance

### 1. Clone the repository

```bash
git clone https://github.com/MuhammadHaider1/docuflow-backend.git
cd docuflow-backend
```

### 2. Create a virtual environment & install dependencies

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
# Security
SECRET_KEY=your-secret-key
ALGORITHIM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database (PostgreSQL)
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=docuflow

# MinIO (S3-compatible object storage)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=docuflow-documents
MINIO_SECURE=false
```

### 4. Start infrastructure with Docker Compose (PostgreSQL + Redis + MinIO)

```bash
docker-compose up -d
```

> Exposed ports: PostgreSQL `5433`, Redis `6380`, MinIO `9000` (API) / `9001` (Console). Adjust `DB_HOST`, `DB_PORT`, etc. in `.env` accordingly.

### 5. Run Alembic migrations

```bash
alembic upgrade head
```

### 6. Run the API server

```bash
uvicorn src.main:app --reload
```

The interactive API docs will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 7. Run Celery worker (background document processing)

```bash
celery -A src.tasks.celery_app.app worker --loglevel=info
```

---

## 📡 API Endpoints (prefix `/api/v1`)

| Module | Endpoints |
|--------|-----------|
| **Authentication** | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh` |
| **Organizations** | `GET/POST /organizations`, `GET/POST/PATCH /organizations/{id}` |
| **Documents & Folders** | CRUD + download `/documents`, `/folders` (nested tree) |
| **RBAC** | `GET /roles`, `GET /permissions`, member role assign/revoke/get |
| **Comments** | CRUD `/comments` |
| **Audit Logs** | `GET /audit` (queryable audit trail) |
| **Notifications** | CRUD + read/unread + bulk operations `/notifications` |
| **Admin** | `/admin` |

---

## 🧪 Running Tests

```bash
pytest
```

---

## ⚠️ Notes & Current State

- The `.env` file is **never committed** — it is git-ignored for security.
- **Dockerfiles** (`docker/*.Dockerfile`) are stubs and part of the containerization roadmap.
- **AI / RAG / OCR / vector embedding** features are designed into the architecture (see Roadmap) and are actively being implemented on top of the existing Celery + `extracted_content` pipeline.

---

## 🗺️ Roadmap

- [ ] **Vector Search RAG** — pgvector + LangChain semantic search & context-aware QA
- [ ] **Background OCR** — automatic text extraction from scanned documents
- [ ] **Vector Embedding Generation** — background async embedding via Celery
- [ ] **LLM Summarization & Classification** — AI insights over extracted content
- [ ] **Presigned URL download / uploads** on MinIO
- [ ] **Full Dockerfile implementations** for FastAPI & Celery
- [ ] **Multi-version document lineage UI**

---

## 📄 License

This project is open source. See the [LICENSE](LICENSE) file for details.
