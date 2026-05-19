import time
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi_cache import FastAPICache


class RateLimitingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.rstrip("/").endswith("/orders/checkout"):
            client_ip = request.client.host if request.client else "unknown"
            current_time = int(time.time())
            window_bucket = current_time // 12

            try:
                cache_key = f"{FastAPICache.get_prefix()}:rate_limit:{client_ip}:{window_bucket}"
                backend = FastAPICache.get_backend()
                hits_raw = await backend.get(cache_key)
                current_hits = int(hits_raw.decode("utf-8")) if hits_raw else 0
            except Exception:
                return await call_next(request)

            if current_hits >= 2:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "status_code": 429,
                        "message": "Duplicate checkout sequence detected. Please wait a moment for the receipt to print.",
                        "data": None
                    }
                )

            await backend.set(cache_key, str(current_hits + 1).encode("utf-8"), expire=12)

        return await call_next(request)
