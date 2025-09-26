from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import create_tables
from .routers import auth_router, convert_router, history_router, favorites_router, profile_router
from .logger_config import setup_logging
from .exceptions import BaseKatakanizerException, to_http_exception

# Setup logging
setup_logging()

# Get settings
settings = get_settings()

app = FastAPI(
    title="Katakanizer API",
    version="1.0.0",
    debug=settings.debug
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# グローバル例外ハンドラー
@app.exception_handler(BaseKatakanizerException)
async def katakanizer_exception_handler(request: Request, exc: BaseKatakanizerException):
    """カスタム例外ハンドラー"""
    http_exc = to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP例外ハンドラー（統一フォーマット）"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.detail,
            "error_code": "HTTP_ERROR",
            "details": {}
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """一般例外ハンドラー"""
    return JSONResponse(
        status_code=500,
        content={
            "message": "内部サーバーエラーが発生しました",
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": {"error": str(exc)} if settings.debug else {}
        }
    )


@app.on_event("startup")
def startup_event():
    create_tables()


# Include routers
app.include_router(auth_router)
app.include_router(convert_router)
app.include_router(history_router)
app.include_router(favorites_router)
app.include_router(profile_router)


@app.get("/")
def read_root():
    return {"message": "Katakanizer API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "katakanizer-backend"
    }