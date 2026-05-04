import xmlrpc.client
import os
from functools import cached_property
from urllib.parse import urlparse


class OdooClient:
    def __init__(self):
        raw = os.getenv("ODOO_URL", "")
        parsed = urlparse(raw)
        # ใช้แค่ scheme + host (ตัด path เช่น /odoo ออก)
        self.url = f"{parsed.scheme}://{parsed.netloc}"
        self.db = os.getenv("ODOO_DB")
        self.username = os.getenv("ODOO_USERNAME")
        self.password = os.getenv("ODOO_PASSWORD")
        self._uid = None

    @cached_property
    def common(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")

    @cached_property
    def models(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def authenticate(self) -> int:
        if not self._uid:
            self._uid = self.common.authenticate(self.db, self.username, self.password, {})
        return self._uid

    def search_read(self, model: str, domain: list, fields: list, limit: int = 100) -> list:
        uid = self.authenticate()
        return self.models.execute_kw(
            self.db, uid, self.password,
            model, "search_read",
            [domain],
            {"fields": fields, "limit": limit, "order": "write_date desc"},
        )


odoo = OdooClient()
