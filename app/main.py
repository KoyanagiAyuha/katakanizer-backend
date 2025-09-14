import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_tables
from .routers import auth_router, convert_router, history_router
from .logger_config import setup_logging

# Setup logging
setup_logging()

app = FastAPI(title="Katakanizer API", version="1.0.0")

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

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


@app.get("/")
def read_root():
    return {"message": "Katakanizer API is running"}