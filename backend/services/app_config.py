import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "app_config.json"

DEFAULTS: dict = {
    "date_from": "2026-05-01",
    "billed_hide_hours": 24,
    "routes": [
        {"name": "กรุงเทพ",       "color": "#1f6feb", "icon": "🏙️"},
        {"name": "สายใน",         "color": "#238636", "icon": "🛣️"},
        {"name": "สายนอก",        "color": "#b45309", "icon": "🚛"},
        {"name": "รับหน้าบริษัท", "color": "#7c3aed", "icon": "🏢"},
        {"name": "เซลล์ส่งเอง",   "color": "#dc2626", "icon": "🧑‍💼"},
    ],
}

_cached: dict | None = None


def get_config() -> dict:
    global _cached
    if _cached is not None:
        return _cached
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        _cached = {**DEFAULTS, **data}
    else:
        _cached = dict(DEFAULTS)
    return _cached


def save_config(data: dict) -> dict:
    global _cached
    merged = {**DEFAULTS, **data}
    CONFIG_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _cached = merged
    return merged
