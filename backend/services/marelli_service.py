from collections import defaultdict
from services.odoo_client import odoo

_MARELLI_DOMAIN = [["name", "ilike", "marelli"]]


def get_marelli_report() -> dict:
    uid = odoo.authenticate()

    # 1. Products
    products = odoo.models.execute_kw(
        odoo.db, uid, odoo.password,
        "product.product", "search_read",
        [_MARELLI_DOMAIN],
        {"fields": ["id", "name", "default_code", "categ_id",
                    "list_price", "standard_price",
                    "qty_available", "virtual_available"], "limit": 500},
    )
    prod_ids = [p["id"] for p in products]
    prod_map = {p["id"]: p for p in products}

    # 2. Sale Order Lines
    sol = odoo.models.execute_kw(
        odoo.db, uid, odoo.password,
        "sale.order.line", "search_read",
        [[["product_id", "in", prod_ids]]],
        {"fields": ["order_id", "product_id", "product_uom_qty",
                    "qty_delivered", "price_unit", "price_subtotal",
                    "state", "create_date"], "limit": 2000, "order": "create_date asc"},
    )

    # 3. Purchase Order Lines
    pol = odoo.models.execute_kw(
        odoo.db, uid, odoo.password,
        "purchase.order.line", "search_read",
        [[["product_id", "in", prod_ids]]],
        {"fields": ["order_id", "product_id", "product_qty",
                    "qty_received", "price_unit", "price_subtotal",
                    "state", "date_order"], "limit": 1000},
    )

    # 4. Sale Orders (for customer info)
    so_ids = list({l["order_id"][0] for l in sol})
    orders = odoo.models.execute_kw(
        odoo.db, uid, odoo.password,
        "sale.order", "search_read",
        [[["id", "in", so_ids]]],
        {"fields": ["id", "partner_id", "date_order"], "limit": 1000},
    ) if so_ids else []
    order_map = {o["id"]: o for o in orders}

    # 5. Purchase Orders (for supplier info)
    po_ids = list({l["order_id"][0] for l in pol})
    purchases = odoo.models.execute_kw(
        odoo.db, uid, odoo.password,
        "purchase.order", "search_read",
        [[["id", "in", po_ids]]],
        {"fields": ["id", "partner_id", "amount_total", "date_order"], "limit": 200},
    ) if po_ids else []

    # ── Aggregations ──────────────────────────────────────────────────────

    # Sales by product
    sales_by_prod = defaultdict(lambda: {
        "so_count": 0, "qty_ordered": 0.0, "qty_delivered": 0.0,
        "revenue": 0.0, "pending_qty": 0.0, "pending_value": 0.0,
    })
    for l in sol:
        pid = l["product_id"][0]
        s = sales_by_prod[pid]
        s["so_count"] += 1
        s["qty_ordered"] += l["product_uom_qty"]
        s["qty_delivered"] += l["qty_delivered"]
        s["revenue"] += l["price_subtotal"]
        pending = l["product_uom_qty"] - l["qty_delivered"]
        if pending > 0 and l["state"] in ("sale", "done"):
            s["pending_qty"] += pending
            s["pending_value"] += pending * l["price_unit"]

    # Purchase by product
    po_by_prod = defaultdict(lambda: {"po_count": 0, "qty_ordered": 0.0, "qty_received": 0.0, "cost": 0.0})
    for l in pol:
        pid = l["product_id"][0]
        p = po_by_prod[pid]
        p["po_count"] += 1
        p["qty_ordered"] += l["product_qty"]
        p["qty_received"] += l["qty_received"]
        p["cost"] += l["price_subtotal"]

    # Top customers
    cust_agg = defaultdict(lambda: {"so_count": 0, "qty": 0.0, "revenue": 0.0, "orders": set()})
    for l in sol:
        o = order_map.get(l["order_id"][0])
        if o:
            cust = o["partner_id"][1] if o["partner_id"] else "ไม่ระบุ"
            cust_agg[cust]["so_count"] += 1
            cust_agg[cust]["qty"] += l["product_uom_qty"]
            cust_agg[cust]["revenue"] += l["price_subtotal"]
            cust_agg[cust]["orders"].add(l["order_id"][0])

    # Monthly trend
    monthly = defaultdict(lambda: {"qty": 0.0, "revenue": 0.0})
    for l in sol:
        ym = l["create_date"][:7]
        monthly[ym]["qty"] += l["product_uom_qty"]
        monthly[ym]["revenue"] += l["price_subtotal"]

    # Supplier summary
    sup_agg = defaultdict(lambda: {"po_count": 0, "amount": 0.0})
    for po in purchases:
        sup = po["partner_id"][1] if po["partner_id"] else "ไม่ระบุ"
        sup_agg[sup]["po_count"] += 1
        sup_agg[sup]["amount"] += po["amount_total"]

    # ── Build output lists ────────────────────────────────────────────────

    products_out = []
    total_revenue = 0.0
    total_cogs = 0.0
    total_stock_value = 0.0

    for p in products:
        pid = p["id"]
        sp = sales_by_prod[pid]
        pp = po_by_prod[pid]
        cost = p["standard_price"]
        price = p["list_price"]
        margin_pct = (price - cost) / price * 100 if price else 0
        stock = p["qty_available"]
        stock_val = stock * cost if stock > 0 else 0

        total_revenue += sp["revenue"]
        total_cogs += sp["qty_delivered"] * cost
        total_stock_value += stock_val

        status = "negative" if stock < 0 else ("low" if stock < 5 else "ok")

        products_out.append({
            "id": pid,
            "sku": p["default_code"] or "",
            "name": p["name"],
            "categ": p["categ_id"][1] if p["categ_id"] else "",
            "price": price,
            "cost": cost,
            "margin_pct": round(margin_pct, 1),
            "stock": stock,
            "virtual": p["virtual_available"],
            "stock_value": round(stock_val, 2),
            "stock_status": status,
            # sales
            "so_count": sp["so_count"],
            "qty_ordered": sp["qty_ordered"],
            "qty_delivered": sp["qty_delivered"],
            "revenue": round(sp["revenue"], 2),
            "pending_qty": sp["pending_qty"],
            "pending_value": round(sp["pending_value"], 2),
            # purchase
            "po_count": pp["po_count"],
            "po_qty": pp["qty_ordered"],
            "po_cost": round(pp["cost"], 2),
        })

    gross_profit = total_revenue - total_cogs
    gross_margin = gross_profit / total_revenue * 100 if total_revenue else 0

    sales_by_product_sorted = sorted(
        products_out, key=lambda x: -x["revenue"]
    )

    top_customers = sorted(
        [
            {
                "name": k,
                "so_count": len(v["orders"]),
                "qty": round(v["qty"], 0),
                "revenue": round(v["revenue"], 2),
            }
            for k, v in cust_agg.items()
        ],
        key=lambda x: -x["revenue"],
    )[:20]

    monthly_trend = [
        {"month": ym, "qty": round(v["qty"], 0), "revenue": round(v["revenue"], 2)}
        for ym, v in sorted(monthly.items())
    ]

    suppliers = [
        {"name": k, "po_count": v["po_count"], "amount": round(v["amount"], 2)}
        for k, v in sorted(sup_agg.items(), key=lambda x: -x[1]["amount"])
    ]

    total_pending_qty = sum(p["pending_qty"] for p in products_out)
    total_pending_value = sum(p["pending_value"] for p in products_out)

    return {
        "totals": {
            "product_count": len(products),
            "revenue": round(total_revenue, 2),
            "cogs": round(total_cogs, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin_pct": round(gross_margin, 1),
            "stock_value": round(total_stock_value, 2),
            "pending_qty": total_pending_qty,
            "pending_value": round(total_pending_value, 2),
            "so_lines": len(sol),
            "po_lines": len(pol),
        },
        "products": sales_by_product_sorted,
        "top_customers": top_customers,
        "monthly_trend": monthly_trend,
        "suppliers": suppliers,
    }
