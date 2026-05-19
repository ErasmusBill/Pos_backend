import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

audit_logger = logging.getLogger("pos_audit")


class BusinessAuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()

        response = await call_next(request)

        process_time = round((time.perf_counter() - start_time) * 1000, 2)
        user_agent = request.headers.get("user-agent", "Unknown Client")

        audit_logger.info(
            f"METHOD={request.method} PATH={request.url.path} "
            f"STATUS={response.status_code} LATENCY={process_time}ms AGENT=\"{user_agent}\""
        )

        response.headers["X-Process-Latency-Ms"] = str(process_time)
        return response