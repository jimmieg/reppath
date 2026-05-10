import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.chat import router
from backend.services.rag import ingest_corpus

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ingest corpus on startup — skips already-embedded docs
    ingest_corpus()
    yield


app = FastAPI(title="RepPath API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}