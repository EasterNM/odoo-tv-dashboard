import socket
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / "config" / ".env")

socket.setdefaulttimeout(30)

from routes.api import router

app = FastAPI(title="Odoo TV Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)
app.mount("/static", StaticFiles(directory=Path(__file__).parent.parent / "frontend" / "shared"), name="static")
