from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import create_tables
from .exceptions import BaseKatakanizerException, to_http_exception
from .routers import (
    auth_router,
    convert_router,
    favorites_router,
    history_router,
    profile_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="Katakanizer API",
    version="2.0.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BaseKatakanizerException)
async def katakanizer_exception_handler(request: Request, exc: BaseKatakanizerException):
    http_exc = to_http_exception(exc)
    return JSONResponse(status_code=http_exc.status_code, content=http_exc.detail)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "message": "内部サーバーエラーが発生しました",
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": {"error": str(exc)} if settings.debug else {},
        },
    )


app.include_router(auth_router)
app.include_router(convert_router)
app.include_router(history_router)
app.include_router(favorites_router)
app.include_router(profile_router)


@app.get("/")
async def read_root():
    return {"message": "Katakanizer API is running"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "katakanizer-backend",
    }
