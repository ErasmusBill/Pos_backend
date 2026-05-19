import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from src.common.responses import CustomResponse

logger = logging.getLogger("pos_api")


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # 1. Catch dangling DB sessions and force rollbacks to protect financial integrity
            if hasattr(request.state, "db"):
                try:
                    request.state.db.rollback()
                    logger.warning("Database transaction rolled back automatically by global safety middleware.")
                except Exception:
                    pass

            # 2. Log full trace details to backoffice monitoring system
            logger.error(f"Critical System Failure on path {request.url.path}: {str(exc)}", exc_info=True)

            # 3. Suppress raw python trace leaks and spit out clean, standard JSON structure
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status_code": 500,
                    "message": "A critical server error occurred. The technical log has been preserved.",
                    "data": None
                }
            )