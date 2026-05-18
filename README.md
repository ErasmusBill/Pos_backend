# FastAPI POS Backend

Backend API for a Point-of-Sale (POS) system built with FastAPI, SQLModel, and Alembic.

## What This Project Does

- User account creation, activation, login, and profile management
- Role-aware access controls (`admin`, `cashier`, `staff`)
- Inventory management (categories, products, stock adjustment)
- Sales product configuration (selling price, tax settings, active status)
- Email workflows (account activation and password reset)
- Response caching via `fastapi-cache2` (currently in-memory backend)

## Tech Stack

- FastAPI
- SQLModel + SQLAlchemy
- Alembic (database migrations)
- SQLite (`pos.db`)
- JWT authentication
- fastapi-mail

## Project Structure

```text
.
|-- main.py
|-- src/
|   |-- common/
|   |-- db/
|   |-- users/
|   |-- inventory/
|   `-- sales/
|-- migrations/
|-- static/uploads/products/
|-- pyproject.toml
`-- alembic.ini
```

## Requirements

- Python `3.14+` (as defined in `pyproject.toml`)
- `uv` (recommended) or another Python environment manager

## Local Setup

1. Install dependencies:

```bash
uv sync
```

2. Set environment variables in `.env`:

```env
DATABASE_URL=sqlite:///./pos.db
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your_mail_username
MAIL_PASSWORD=your_mail_password
MAIL_FROM=no-reply@example.com
MAIL_FROM_NAME=POS Backend
SECRET_KEY=replace_with_a_strong_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
ENVIRONMENT=development
SECURITY_PASSWORD_SALT=replace_with_a_random_salt
```

3. Run migrations:

```bash
uv run alembic upgrade head
```

4. Start the API server:

```bash
uv run uvicorn main:app --reload
```

## API Base URL

- Local: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Main Route Groups

- `GET /health`
- Users/Auth (under `/api/v1`):
  - `/create-user`, `/activate-account/{token}`, `/login`
  - `/me`, `/update-my-profile`, `/change-password`
  - `/forgot-password`, `/reset-password-confirm`
- Inventory (under `/api/v1/inventory`):
  - `/categories`, `/products`, `/products/{product_id}/adjust-stock`
- Sales (under `/api/v1/sales`):
  - `/products` and `/products/{sales_product_id}`

## Notes

- Product images are stored in `static/uploads/products/`.
- The local SQLite database file is `pos.db`.
- Do not commit `.env`, local DB files, or uploaded media to GitHub.
