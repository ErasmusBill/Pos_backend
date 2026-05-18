from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi import status
from typing import Any, Optional


class CustomResponse(JSONResponse):
    def __init__(
            self,
            message: str,
            status_code: int = status.HTTP_200_OK,
            data: Optional[Any] = None
    ):
        content = {
            "success": status_code < 400,
            "message": message,
            "status": status_code,
            "data": jsonable_encoder(data) if data is not None else {}
        }

        super().__init__(status_code=status_code, content=content)