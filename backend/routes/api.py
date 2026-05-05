from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
from services.sales_service import get_ready_to_invoice
from services.store_service import get_store_pickings
from services.transport_service import get_transport_pickings
from services.bill_receipt_service import get_pending_receipts, confirm_receipt

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


@router.get("/api/transport/pickings")
def transport_pickings():
    try:
        return {"data": get_transport_pickings()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transport", response_class=HTMLResponse)
def transport_tv():
    return (FRONTEND_DIR / "transport-tv" / "index.html").read_text()


# ── Mobile: Bill Receipt ──────────────────────────────────────────────────────

class ConfirmReceiptRequest(BaseModel):
    so_ids:        list[int]
    signature_b64: str
    signer_name:   str


@router.get("/mobile/receive-bill", response_class=HTMLResponse)
def mobile_receive_bill():
    return (FRONTEND_DIR / "mobile-receive-bill" / "index.html").read_text()


@router.get("/api/mobile/pending-receipts")
def api_pending_receipts():
    try:
        return {"data": get_pending_receipts(), "ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/mobile/confirm-receipt")
def api_confirm_receipt(body: ConfirmReceiptRequest):
    try:
        result = confirm_receipt(body.so_ids, body.signature_b64, body.signer_name)
        if not result["ok"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
