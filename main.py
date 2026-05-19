from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from src.db.engine import create_db_and_tables
from src.users.urls import user_router
from src.inventory.urls import inventory_router
from src.sales.urls import sales_router
from src.cart.urls import order_router
from src.middlewares.audit_logging import BusinessAuditLoggingMiddleware
from src.middlewares.error_handling import GlobalExceptionMiddleware
from src.middlewares.rate_limiting import RateLimitingMiddleware

from dotenv import load_dotenv
load_dotenv()

from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    FastAPICache.init(InMemoryBackend(), prefix="pos-cache")

    # Initialize DB
    create_db_and_tables()

    yield



app = FastAPI(
    title="My POS Backend API",
    version="1.0.0",
    description="A professional backend for tablet and desktop POS views",
    lifespan=lifespan
)

app.include_router(user_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(sales_router, prefix="/api/v1")

app.include_router(order_router, prefix="/api/v1")

app.add_middleware(RateLimitingMiddleware)
app.add_middleware(BusinessAuditLoggingMiddleware)
app.add_middleware(GlobalExceptionMiddleware)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "testserver",
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "online", "message": "POS System is running"}
