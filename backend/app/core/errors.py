from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class IllegalTransitionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ForbiddenActionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(IllegalTransitionError)
    async def illegal(_: Request, exc: IllegalTransitionError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message, "code": "illegal_transition"})

    @app.exception_handler(ForbiddenActionError)
    async def forbidden(_: Request, exc: ForbiddenActionError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.message, "code": "forbidden"})

    @app.exception_handler(NotFoundError)
    async def missing(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.message, "code": "not_found"})
