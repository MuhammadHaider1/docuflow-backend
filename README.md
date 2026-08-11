# DocuFlow Backend API

An asynchronous document management and notification processing backend built with **FastAPI**, **PostgreSQL**, **SQLAlchemy (Async)**, and **Alembic**.

## 🚀 Features

* **Authentication & Authorization**: Secure JWT-based authentication.
* **Notification System**: Full notification pipeline supporting read/unread statuses and bulk operations.
* **Audit Logging**: Asynchronous audit logs for system events and document actions.
* **Database Migrations**: Version-controlled PostgreSQL schema management with Alembic.
* **Docker Support**: Containerized environment for local development and database orchestration.

## 🛠️ Tech Stack

* **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
* **Database**: PostgreSQL with [SQLAlchemy 2.0 (Async)](https://www.sqlalchemy.org/) & [asyncpg](https://github.com/MagicStack/asyncpg)
* **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
* **Containerization**: Docker & Docker Compose
* **Server**: Uvicorn

## 📦 Getting Started

### Prerequisites

* Python 3.12+
* PostgreSQL or Docker Compose

### Local Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/MuhammadHaider1/docuflow-backend.git](https://github.com/MuhammadHaider1/docuflow-backend.git)
   cd docuflow-backend
