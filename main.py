from contextlib import asynccontextmanager
from fastapi import FastAPI
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
# from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.backends.inmemory import InMemoryBackend
from src.db.engine import create_db_and_tables
from src.users.urls import user_router
from src.inventory.urls import inventory_router
from src.sales.urls import sales_router

from dotenv import load_dotenv
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # redis = aioredis.from_url(
    #     "redis://localhost:6379",
    #     encoding="utf8",
    #     decode_responses=True
    # )
    # FastAPICache.init(RedisBackend(redis), prefix="pos-cache")
    FastAPICache.init(InMemoryBackend(),prefix="pos-cache")

    # Initialize DB
    create_db_and_tables()

    yield
    # await redis.close()



app = FastAPI(
    title="My POS Backend API",
    version="1.0.0",
    description="A professional backend for tablet and desktop POS views",
    lifespan=lifespan
)

app.include_router(user_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(sales_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "online", "message": "POS System is running"}