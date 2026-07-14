from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, ensure_database_exists
from app import models  # noqa: F401 - registers models on Base metadata
from app.routers import interactions, chat
from app.config import settings

app = FastAPI(title="AI-First CRM — HCP Module", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interactions.router)
app.include_router(chat.router)


@app.on_event("startup")
def on_startup():
    ensure_database_exists()
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}
