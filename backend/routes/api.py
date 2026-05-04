from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
from services.sales_service import get_ready_to_invoice
from services.store_service import get_store_pickings

router = APIRouter()
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"


@router.get("/api/sales/ready-to-invoice")
def sales_ready_to_invoice():
    try:
        return {"data": get_ready_to_invoice(), "ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/store/pickings")
def store_pickings():
    try:
        return {"data": get_store_pickings()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sales", response_class=HTMLResponse)
def sales_tv():
    return (FRONTEND_DIR / "sales-tv" / "index.html").read_text()


@router.get("/store", response_class=HTMLResponse)
def store_tv():
    return (FRONTEND_DIR / "store-tv" / "index.html").read_text()
