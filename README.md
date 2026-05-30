# AI Study Planner

A study planning app to organize goals, plans, and tasks. JWT-based auth, progress tracking, and target dates.

## Stack

| Layer      | Technology                                    |
|------------|-----------------------------------------------|
| Backend    | Python 3.12, FastAPI, SQLAlchemy 2, uv        |
| Database   | PostgreSQL 16                                 |
| Migrations | Alembic                                       |
| Frontend   | React 18, TypeScript, Vite, Mantine 7         |
| Container  | Docker Compose                                |

## Quick Start

```bash
docker compose up --build
```

On first boot the backend automatically runs migrations and seeds the database with sample data.

| Service   | URL                         |
|-----------|-----------------------------|
| Frontend  | http://localhost:5173       |
| API       | http://localhost:8000       |
| API Docs  | http://localhost:8000/docs  |

> If port 8000 is already in use, change `"8000:8000"` to `"8001:8000"` in `docker-compose.yml`.

## Seed Data

The seeder runs automatically on every `compose up` (idempotent — skips if the admin user already exists).

| Credential | Value      |
|------------|------------|
| Username   | `admin`    |
| Password   | `admin123` |

Four sample plans are created (AWS cert, TypeScript, Clean Code, System Design) with multiple tasks at various completion states so you can see the progress bars and date badges in action.

To re-seed from scratch, remove the database volume and restart:

```bash
docker compose down -v && docker compose up --build
```

## API Endpoints

| Method | Path                            | Description              |
|--------|---------------------------------|--------------------------|
| POST   | /auth/register                  | Create account           |
| POST   | /auth/login                     | Sign in, get JWT         |
| GET    | /users/{id}/plans               | List user's plans        |
| POST   | /plans                          | Create study plan        |
| GET    | /plans/{id}                     | Get study plan           |
| PATCH  | /plans/{id}                     | Update plan              |
| POST   | /plans/{id}/tasks               | Add task to plan         |
| GET    | /plans/{id}/tasks               | List tasks               |
| PATCH  | /plans/{id}/tasks/{taskId}      | Toggle task completion   |

## Development

### Backend tests

```bash
cd backend
uv sync --all-groups
uv run pytest tests/ -v
```

### Backend only (no Docker)

```bash
cd backend
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/study_planner \
  uv run uvicorn app.main:app --reload
```

### Frontend only (no Docker)

```bash
cd frontend
npm install
npm run dev
```

## Architecture

```
backend/app/
├── api/routers/   → HTTP layer (parse request, return response)
├── services/      → Business logic, raises 404s
├── repositories/  → Database access only
├── models/        → SQLAlchemy ORM models
├── schemas/       → Pydantic request/response models
├── core/          → Config, database session, JWT/bcrypt helpers
└── seed.py        → Idempotent sample data seeder

frontend/src/
├── api/           → API client and token helpers
├── components/
│   ├── layout/    → AppHeader
│   ├── routing/   → PrivateRoute
│   ├── plan/      → PlanCard, CreatePlanModal
│   └── task/      → TaskItem, AddTaskModal
└── pages/
    ├── auth/      → LoginPage
    ├── dashboard/ → Dashboard
    └── plans/     → PlanDetail
```
