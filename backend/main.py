# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
import os

load_dotenv()

# This tells Swagger UI that our API uses Bearer token auth
# This is what makes the Authorize button appear
security = HTTPBearer()

app = FastAPI(
    title="Finance GenAI Agent API",
    description="Budget-aware personal finance reasoning agent powered by Gemini",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://habitwealth-ai.vercel.app",
        "https://habitwealth-hh1djd82f-shreya-debug.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
from routers import (
    auth,
    budget,
    transactions,
    calculator_routes,
    agent,
    csv_upload,
    purchase_advisor,
    # rag,
)

app.include_router(auth.router)
app.include_router(budget.router)
app.include_router(transactions.router)
app.include_router(calculator_routes.router)
app.include_router(agent.router)
app.include_router(csv_upload.router)
app.include_router(purchase_advisor.router)
# app.include_router(rag.router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "Finance Agent API is running",
        "model": "gemini-3-flash-preview",
    }
