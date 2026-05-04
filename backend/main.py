from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / "config" / ".env")

from routes.api import router

app = FastAPI(title="Odoo TV Dashboard")
app.include_router(router)
app.mount("/static", StaticFiles(directory=Path(__file__).parent.parent / "frontend" / "shared"), name="static")
