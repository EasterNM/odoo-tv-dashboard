import xmlrpc.client
import os
import threading
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
        self._local = threading.local()

    @cached_property
    def common(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")

    @property
    def models(self):
        # ServerProxy ไม่ thread-safe — แต่ละเธรดต้องมี instance ของตัวเอง
        if not hasattr(self._local, "proxy"):
            self._local.proxy = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        return self._local.proxy

    def authenticate(self) -> int:
        if not self._uid:
            self._uid = self.common.authenticate(self.db, self.username, self.password, {})
        return self._uid

    def search_read(self, model: str, domain: list, fields: list, limit: int = 100, order: str = "write_date desc") -> list:
        uid = self.authenticate()
        return self.models.execute_kw(
            self.db, uid, self.password,
            model, "search_read",
            [domain],
            {"fields": fields, "limit": limit, "order": order},
        )

    def write(self, model: str, ids: list, vals: dict) -> bool:
        uid = self.authenticate()
        return self.models.execute_kw(
            self.db, uid, self.password,
            model, "write",
            [ids, vals],
        )

    def execute_method(self, model: str, method: str, record_ids: list, kwargs: dict = None) -> any:
        uid = self.authenticate()
        return self.models.execute_kw(
            self.db, uid, self.password,
            model, method,
            [record_ids],
            kwargs or {},
        )

    def create(self, model: str, vals: dict) -> int:
        uid = self.authenticate()
        return self.models.execute_kw(
            self.db, uid, self.password,
            model, "create",
            [vals],
        )


odoo = OdooClient()
