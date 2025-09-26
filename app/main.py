import os
import json
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_tables
from .routers import auth_router, convert_router, history_router, favorites_router, profile_router
from .logger_config import setup_logging

# Setup logging
setup_logging()

app = FastAPI(title="Katakanizer API", version="1.0.0")

# CORS設定 - 環境変数からJSON配列またはカンマ区切り文字列を読み込み
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000")
try:
    # JSON配列として解析を試みる
    cors_origins = json.loads(cors_origins_env)
except (json.JSONDecodeError, TypeError):
    # 失敗したらカンマ区切りとして処理
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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