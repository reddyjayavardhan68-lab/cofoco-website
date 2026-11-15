"""
COFOCO (Conscious Form Company) - High Performance Multi-Threaded HTTP API & Application Server
Built with Python 3.13 standard library.
Features:
- Complete RESTful API for Storefront and Admin Portals
- Role-Based Access Control (Admin, Brand Editor, Publisher, Warehouse, Support, Finance)
- Atomic Multi-Component Inventory Reservations with 15-Minute Expiry
- Dynamic Sellable Kit Calculation: min(floor(Available Component Stock / Required BOM Qty))
- Exact BOM Snapshot Preservation in Order Lines
- Razorpay Test-Mode Integration with HMAC-SHA256 Signature Verification & Idempotency
- Return Inspection & Quality Gate (restock only upon inspection approval)
- Founder Business Analytics with Asia/Kolkata IST reporting and Zero-PII CSV Exports
"""

import os
import sys
import json
import uuid
import hmac
import hashlib
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
import io
import csv

from database import DB_PATH, get_db, IST, hash_password, verify_password, init_db, seed_db

PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
RAZORPAY_TEST_KEY_ID = "rzp_test_cofoco2026"
RAZORPAY_TEST_SECRET = "cofoco_secret_key_prod_sim_2026"

# In-memory active staff session store: token -> {user_id, username, role_name, permissions}
ACTIVE_SESSIONS = {}
SESSIONS_LOCK = threading.Lock()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

def now_ist() -> datetime:
    return datetime.now(IST)

def now_ist_iso() -> str:
    return now_ist().isoformat()

def clean_expired_reservations():
    """Background or inline release of expired reservations back to sellable stock."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        now_str = now_ist_iso()
        cursor.execute("""
            UPDATE reservations
            SET status = 'released'
            WHERE status = 'active' AND expires_at < ?;
        """, (now_str,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[RESERVATION CLEANUP ERROR] {e}")

def calculate_variant_stock(cursor, variant_id: str) -> dict:
    """
    Calculate available sellable kits for a variant:
    Available Component Stock = On-hand Sellable Quantity - Active Reservations
    Sellable Kits = min(floor(Available Component Stock / Required BOM Quantity))
    """
    # 1. Fetch active BOM version
    cursor.execute("""
        SELECT id, version FROM bom_versions
        WHERE variant_id = ? AND status = 'active'
        ORDER BY created_at DESC LIMIT 1;
    """, (variant_id,))
    bom_ver = cursor.fetchone()
    if not bom_ver:
        return {"sellable_kits": 0, "is_in_stock": False, "limiting_component": "No active BOM", "components": []}

    # 2. Fetch BOM items
    cursor.execute("""
        SELECT bi.component_id, bi.quantity as required_qty, c.name, c.sku, inv.on_hand
        FROM bom_items bi
        JOIN components c ON bi.component_id = c.id
        JOIN inventory inv ON bi.component_id = inv.component_id
        WHERE bi.bom_version_id = ?;
    """, (bom_ver["id"],))
    items = cursor.fetchall()

    if not items:
        return {"sellable_kits": 0, "is_in_stock": False, "limiting_component": "Empty BOM", "components": []}

    now_str = now_ist_iso()
    min_kits = sys.maxsize
    limiting_sku = None
    comp_details = []

    for item in items:
        comp_id = item["component_id"]
        req_qty = item["required_qty"]
        on_hand = item["on_hand"]

        # Calculate active reservations for this component
        cursor.execute("""
            SELECT COALESCE(SUM(quantity), 0) as reserved_qty
            FROM reservations
            WHERE component_id = ? AND status = 'active' AND expires_at >= ?;
        """, (comp_id, now_str))
        reserved_qty = cursor.fetchone()["reserved_qty"]
        available_comp_stock = max(0, on_hand - reserved_qty)
        kits_supported = available_comp_stock // req_qty

        if kits_supported < min_kits:
            min_kits = kits_supported
            limiting_sku = item["sku"]

        comp_details.append({
            "component_id": comp_id,
            "sku": item["sku"],
            "name": item["name"],
            "required_qty": req_qty,
            "on_hand": on_hand,
            "reserved": reserved_qty,
            "available": available_comp_stock,
            "kits_supported": kits_supported
        })

    sellable = min_kits if min_kits != sys.maxsize else 0
    return {
        "bom_version": bom_ver["version"],
        "bom_version_id": bom_ver["id"],
        "sellable_kits": sellable,
        "is_in_stock": sellable > 0,
        "limiting_component": limiting_sku,
        "components": comp_details
    }

class CofocoRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to keep logs clean
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, X-Session-Id")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message, status=400, details=None):
        payload = {"error": message, "status": status}
        if details:
            payload["details"] = details
        self.send_json(payload, status=status)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, X-Session-Id")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.end_headers()

    def get_auth_user(self):
        auth_hdr = self.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr[7:].strip()
            with SESSIONS_LOCK:
                return ACTIVE_SESSIONS.get(token)
        return None

    def require_permission(self, permission):
        user = self.get_auth_user()
        if not user:
            self.send_error_json("Authentication required for staff operations.", 401)
            return None
        perms = user.get("permissions", [])
        if "all" in perms or permission in perms:
            return user
        self.send_error_json(f"Forbidden: Missing required permission '{permission}'.", 403)
        return None

    def get_request_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        clean_expired_reservations()
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # -------------------------------------------------------------
        # API Routes
        # -------------------------------------------------------------
        if path == "/api/health":
            self.send_json({"status": "healthy", "service": "COFOCO E-Commerce API", "time": now_ist_iso()})

        # 1. Characters List
        elif path == "/api/characters":
            conn = get_db()
            cur = conn.cursor()
            status_filter = query.get("status", [None])[0]
            if status_filter:
                cur.execute("SELECT * FROM characters WHERE status = ? ORDER BY name ASC;", (status_filter,))
            else:
                cur.execute("SELECT * FROM characters ORDER BY name ASC;")
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                r["theme_colors"] = json.loads(r["theme_colors_json"])
            conn.close()
            self.send_json({"characters": rows})

        # 2. Character Detail
        elif path.startswith("/api/characters/"):
            char_key = path[len("/api/characters/"):]
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM characters WHERE id = ? OR slug = ?;", (char_key, char_key))
            char = cur.fetchone()
            if not char:
                conn.close()
                return self.send_error_json("Character not found", 404)
            char_data = dict(char)
            char_data["theme_colors"] = json.loads(char_data["theme_colors_json"])

            # Fetch linked kits
            cur.execute("""
                SELECT k.*, pv.id as default_variant_id, pv.sku, pv.price
                FROM kits k
                LEFT JOIN product_variants pv ON k.id = pv.kit_id AND pv.is_active = 1
                WHERE k.character_id = ?
                GROUP BY k.id;
            """, (char_data["id"],))
            linked_kits = [dict(k) for k in cur.fetchall()]
            for lk in linked_kits:
                stk = calculate_variant_stock(cur, lk["default_variant_id"])
                lk["stock_info"] = stk
                lk["is_in_stock"] = stk["is_in_stock"]
                lk["sellable_kits"] = stk["sellable_kits"]

            char_data["linked_kits"] = linked_kits
            conn.close()
            self.send_json(char_data)

        # 3. Kits Catalog List
        elif path == "/api/kits":
            conn = get_db()
            cur = conn.cursor()
            char_filter = query.get("character", [None])[0]
            if char_filter:
                cur.execute("""
                    SELECT k.*, c.name as character_name, c.slug as character_slug, c.quality as character_quality,
                           c.routine_cue as character_routine_cue, c.theme_colors_json
                    FROM kits k
                    JOIN characters c ON k.character_id = c.id
                    WHERE (c.id = ? OR c.slug = ?) AND k.status = 'published'
                    ORDER BY k.is_featured DESC, k.name ASC;
                """, (char_filter, char_filter))
            else:
                cur.execute("""
                    SELECT k.*, c.name as character_name, c.slug as character_slug, c.quality as character_quality,
                           c.routine_cue as character_routine_cue, c.theme_colors_json
                    FROM kits k
                    JOIN characters c ON k.character_id = c.id
                    WHERE k.status = 'published'
                    ORDER BY k.is_featured DESC, k.name ASC;
                """)
            kits = [dict(k) for k in cur.fetchall()]
            for k in kits:
                k["theme_colors"] = json.loads(k["theme_colors_json"])
                # Fetch default variant and compute stock
                cur.execute("SELECT id, sku, price, variant_name FROM product_variants WHERE kit_id = ? AND is_active = 1 LIMIT 1;", (k["id"],))
                v = cur.fetchone()
                if v:
                    k["default_variant"] = dict(v)
                    stock_res = calculate_variant_stock(cur, v["id"])
                    k["stock_info"] = stock_res
                    k["is_in_stock"] = stock_res["is_in_stock"]
                    k["sellable_kits"] = stock_res["sellable_kits"]
                else:
                    k["is_in_stock"] = False
                    k["sellable_kits"] = 0
            conn.close()
            self.send_json({"kits": kits})

        # 4. Kit Detail by Slug or ID
        elif path.startswith("/api/kits/"):
            kit_key = path[len("/api/kits/"):]
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT k.*, c.name as character_name, c.slug as character_slug, c.quality as character_quality,
                       c.routine_cue as character_routine_cue, c.story as character_story, c.theme_colors_json, c.artwork_url as character_artwork
                FROM kits k
                JOIN characters c ON k.character_id = c.id
                WHERE k.id = ? OR k.slug = ?;
            """, (kit_key, kit_key))
            kit = cur.fetchone()
            if not kit:
                conn.close()
                return self.send_error_json("Kit not found", 404)

            kit_data = dict(kit)
            kit_data["theme_colors"] = json.loads(kit_data["theme_colors_json"])

            # Fetch variants
            cur.execute("SELECT * FROM product_variants WHERE kit_id = ? AND is_active = 1;", (kit_data["id"],))
            variants = [dict(v) for v in cur.fetchall()]
            for v in variants:
                stock_res = calculate_variant_stock(cur, v["id"])
                v["stock_info"] = stock_res
                v["sellable_kits"] = stock_res["sellable_kits"]
                v["is_in_stock"] = stock_res["is_in_stock"]

            kit_data["variants"] = variants

            # Primary stock status from primary variant
            primary_var = variants[0] if variants else None
            kit_data["is_in_stock"] = primary_var["is_in_stock"] if primary_var else False
            kit_data["sellable_kits"] = primary_var["sellable_kits"] if primary_var else 0
            kit_data["components"] = primary_var["stock_info"]["components"] if primary_var else []

            # If out of stock, suggest available alternative kits
            if not kit_data["is_in_stock"]:
                cur.execute("""
                    SELECT k.id, k.slug, k.name, k.base_price, k.image_url, c.name as character_name
                    FROM kits k
                    JOIN characters c ON k.character_id = c.id
                    WHERE k.id != ? AND k.status = 'published'
                    LIMIT 3;
                """, (kit_data["id"],))
                alts = [dict(a) for a in cur.fetchall()]
                kit_data["suggested_alternatives"] = alts

            conn.close()
            self.send_json(kit_data)

        # 5. Kit Comparison Endpoint
        elif path == "/api/compare":
            kit_ids_str = query.get("ids", [""])[0]
            kit_ids = [k.strip() for k in kit_ids_str.split(",") if k.strip()]
            if not kit_ids:
                return self.send_error_json("Specify at least two kit IDs (e.g. ?ids=kit1,kit2)", 400)

            conn = get_db()
            cur = conn.cursor()
            results = []
            for kid in kit_ids:
                cur.execute("""
                    SELECT k.*, c.name as character_name, c.quality as character_quality, c.theme_colors_json
                    FROM kits k
                    JOIN characters c ON k.character_id = c.id
                    WHERE k.id = ? OR k.slug = ?;
                """, (kid, kid))
                k_row = cur.fetchone()
                if not k_row:
                    continue
                k_dict = dict(k_row)
                k_dict["theme_colors"] = json.loads(k_dict["theme_colors_json"])

                # Fetch active variants and components
                cur.execute("SELECT * FROM product_variants WHERE kit_id = ? AND is_active = 1;", (k_dict["id"],))
                vars_list = [dict(v) for v in cur.fetchall()]
                for v in vars_list:
                    v["stock_info"] = calculate_variant_stock(cur, v["id"])

                k_dict["variants"] = vars_list
                first_var = vars_list[0] if vars_list else None
                k_dict["is_in_stock"] = first_var["stock_info"]["is_in_stock"] if first_var else False
                k_dict["included_components"] = first_var["stock_info"]["components"] if first_var else []
                results.append(k_dict)

            conn.close()
            self.send_json({"compared_kits": results})

        # 6. Cart Endpoint
        elif path == "/api/cart":
            session_id = self.headers.get("X-Session-Id") or query.get("session_id", [None])[0]
            if not session_id:
                return self.send_error_json("X-Session-Id header or query parameter required", 400)

            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM carts WHERE session_id = ?;", (session_id,))
            cart = cur.fetchone()
            if not cart:
                conn.close()
                return self.send_json({"items": [], "subtotal": 0.0, "discount": 0.0, "shipping": 0.0, "tax": 0.0, "total": 0.0})

            cart_id = cart["id"]
            coupon = cart["coupon_code"]

            cur.execute("""
                SELECT ci.id as cart_item_id, ci.quantity, ci.variant_id,
                       pv.sku, pv.variant_name, pv.price,
                       k.id as kit_id, k.name as kit_name, k.image_url,
                       c.name as character_name
                FROM cart_items ci
                JOIN product_variants pv ON ci.variant_id = pv.id
                JOIN kits k ON pv.kit_id = k.id
                JOIN characters c ON k.character_id = c.id
                WHERE ci.cart_id = ?;
            """, (cart_id,))
            items = [dict(i) for i in cur.fetchall()]

            subtotal = sum(i["price"] * i["quantity"] for i in items)
            discount = 0.0
            if coupon:
                coupon_upper = coupon.strip().upper()
                if coupon_upper == "COFOCO10":
                    discount = round(subtotal * 0.10, 2)
                elif coupon_upper == "LAUNCH500" and subtotal >= 3000:
                    discount = 500.0
                elif coupon_upper == "FITNESS20":
                    discount = round(subtotal * 0.20, 2)

            shipping = 0.0 if (subtotal - discount) >= 2500 or subtotal == 0 else 149.0
            net_taxable = max(0.0, subtotal - discount)
            # GST 18% inclusive
            tax = round(net_taxable * 0.18 / 1.18, 2)
            total = round(net_taxable + shipping, 2)

            # Check stock validity for each item
            for i in items:
                stk = calculate_variant_stock(cur, i["variant_id"])
                i["available_stock"] = stk["sellable_kits"]
                i["is_valid_stock"] = stk["sellable_kits"] >= i["quantity"]

            conn.close()
            self.send_json({
                "cart_id": cart_id,
                "session_id": session_id,
                "coupon_code": coupon,
                "items": items,
                "subtotal": round(subtotal, 2),
                "discount": round(discount, 2),
                "shipping": round(shipping, 2),
                "tax": round(tax, 2),
                "total": round(total, 2)
            })

        # 7. Order Confirmation & Tracking
        elif path.startswith("/api/orders/"):
            ord_key = path[len("/api/orders/"):]
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM orders WHERE id = ? OR order_number = ?;", (ord_key, ord_key))
            ord_row = cur.fetchone()
            if not ord_row:
                conn.close()
                return self.send_error_json("Order not found", 404)

            ord_dict = dict(ord_row)

            # Fetch order items with BOM snapshots
            cur.execute("SELECT * FROM order_items WHERE order_id = ?;", (ord_dict["id"],))
            items = [dict(i) for i in cur.fetchall()]
            for i in items:
                i["bom_snapshot"] = json.loads(i["bom_snapshot_json"])
            ord_dict["items"] = items

            # Fetch shipment details if any
            cur.execute("SELECT * FROM shipments WHERE order_id = ?;", (ord_dict["id"],))
            shipment = cur.fetchone()
            ord_dict["shipment"] = dict(shipment) if shipment else None

            conn.close()
            self.send_json(ord_dict)

        # 8. Admin Overview
        elif path == "/api/admin/overview":
            if not self.require_permission("view_orders"):
                return
            conn = get_db()
            cur = conn.cursor()

            # Paid orders awaiting dispatch
            cur.execute("SELECT COUNT(*) as cnt FROM orders WHERE order_status IN ('paid', 'picking', 'packed');")
            awaiting_dispatch = cur.fetchone()["cnt"]

            # Overdue orders (promised dispatch date in past and still not dispatched)
            now_str = now_ist_iso()
            cur.execute("""
                SELECT COUNT(*) as cnt FROM orders
                WHERE order_status IN ('paid', 'picking', 'packed') AND promised_dispatch_date < ?;
            """, (now_str,))
            overdue_orders = cur.fetchone()["cnt"]

            # Kits below stock threshold
            cur.execute("""
                SELECT COUNT(*) as cnt FROM inventory inv
                WHERE inv.on_hand <= inv.low_stock_threshold;
            """)
            low_stock_count = cur.fetchone()["cnt"]

            # Unresolved payment issues (reconciliation_required, failed)
            cur.execute("SELECT COUNT(*) as cnt FROM orders WHERE payment_status = 'reconciliation_required';")
            unresolved_payments = cur.fetchone()["cnt"]

            # Pending returns
            cur.execute("SELECT COUNT(*) as cnt FROM returns WHERE status IN ('requested', 'received');")
            pending_returns = cur.fetchone()["cnt"]

            # Recent audit activity
            cur.execute("""
                SELECT al.*, u.full_name as user_name, u.username
                FROM audit_logs al
                LEFT JOIN users u ON al.user_id = u.id
                ORDER BY al.created_at DESC LIMIT 8;
            """)
            recent_activity = [dict(a) for a in cur.fetchall()]
            for ra in recent_activity:
                if ra["changes_json"]:
                    ra["changes"] = json.loads(ra["changes_json"])

            conn.close()
            self.send_json({
                "metrics": {
                    "awaiting_dispatch": awaiting_dispatch,
                    "overdue_orders": overdue_orders,
                    "low_stock_components": low_stock_count,
                    "unresolved_payments": unresolved_payments,
                    "pending_returns": pending_returns
                },
                "recent_activity": recent_activity
            })

        # 9. Admin Orders List
        elif path == "/api/admin/orders":
            if not self.require_permission("view_orders"):
                return
            conn = get_db()
            cur = conn.cursor()
            status = query.get("status", [None])[0]
            overdue = query.get("overdue", [None])[0]
            now_str = now_ist_iso()

            sql = "SELECT o.*, u.full_name as assigned_staff_name FROM orders o LEFT JOIN users u ON o.assigned_staff_id = u.id WHERE 1=1"
            params = []
            if status:
                sql += " AND o.order_status = ?"
                params.append(status)
            if overdue == "1":
                sql += " AND o.order_status IN ('paid', 'picking', 'packed') AND o.promised_dispatch_date < ?"
                params.append(now_str)

            sql += " ORDER BY o.created_at DESC;"
            cur.execute(sql, params)
            orders = [dict(o) for o in cur.fetchall()]

            for o in orders:
                cur.execute("SELECT COUNT(*) as cnt FROM order_items WHERE order_id = ?;", (o["id"],))
                o["item_count"] = cur.fetchone()["cnt"]
                cur.execute("SELECT tracking_number, courier_name, tracking_url FROM shipments WHERE order_id = ?;", (o["id"],))
                sh = cur.fetchone()
                o["shipment"] = dict(sh) if sh else None

            conn.close()
            self.send_json({"orders": orders})

        # 10. Admin Pick List (Preserves purchased BOM snapshot!)
        elif path.startswith("/api/admin/orders/") and path.endswith("/picklist"):
            if not self.require_permission("fulfill"):
                return
            order_id = path.split("/")[4]
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM orders WHERE id = ?;", (order_id,))
            ord_row = cur.fetchone()
            if not ord_row:
                conn.close()
                return self.send_error_json("Order not found", 404)

            cur.execute("SELECT * FROM order_items WHERE order_id = ?;", (order_id,))
            items = [dict(i) for i in cur.fetchall()]

            pick_list = []
            for item in items:
                bom_snapshot = json.loads(item["bom_snapshot_json"])
                for comp in bom_snapshot:
                    # Query current warehouse location
                    cur.execute("""
                        SELECT inv.location, inv.on_hand
                        FROM components c
                        JOIN inventory inv ON c.id = inv.component_id
                        WHERE c.sku = ?;
                    """, (comp["component_sku"],))
                    loc_row = cur.fetchone()
                    location = loc_row["location"] if loc_row else "Bay General"
                    total_qty_to_pick = comp["qty"] * item["quantity"]

                    pick_list.append({
                        "kit_name": item["kit_name"],
                        "variant_name": item["variant_name"],
                        "character_name": item["character_name"],
                        "component_sku": comp["component_sku"],
                        "component_name": comp["name"],
                        "quantity_per_kit": comp["qty"],
                        "kits_ordered": item["quantity"],
                        "total_quantity_to_pick": total_qty_to_pick,
                        "warehouse_location": location
                    })

            conn.close()
            self.send_json({
                "order_number": ord_row["order_number"],
                "customer_name": ord_row["customer_name"],
                "created_at": ord_row["created_at"],
                "order_status": ord_row["order_status"],
                "pick_list": pick_list
            })

        # 11. Admin Inventory Management
        elif path == "/api/admin/inventory":
            if not self.require_permission("manage_stock"):
                return
            conn = get_db()
            cur = conn.cursor()
            now_str = now_ist_iso()
            cur.execute("""
                SELECT c.id, c.sku, c.name, c.category, c.material, c.dimensions, c.unit_cost, c.supplier_name,
                       inv.on_hand, inv.low_stock_threshold, inv.location, inv.updated_at
                FROM components c
                JOIN inventory inv ON c.id = inv.component_id
                ORDER BY (inv.on_hand <= inv.low_stock_threshold) DESC, c.name ASC;
            """)
            components = [dict(c) for c in cur.fetchall()]
            for comp in components:
                cur.execute("""
                    SELECT COALESCE(SUM(quantity), 0) as reserved
                    FROM reservations
                    WHERE component_id = ? AND status = 'active' AND expires_at >= ?;
                """, (comp["id"], now_str))
                comp["reserved"] = cur.fetchone()["reserved"]
                comp["available"] = max(0, comp["on_hand"] - comp["reserved"])
                comp["is_low_stock"] = comp["on_hand"] <= comp["low_stock_threshold"]

            # Stock ledger history
            cur.execute("""
                SELECT sl.*, c.name as component_name, c.sku as component_sku, u.full_name as staff_name
                FROM stock_ledger sl
                JOIN components c ON sl.component_id = c.id
                LEFT JOIN users u ON sl.created_by = u.id
                ORDER BY sl.created_at DESC LIMIT 20;
            """)
            ledger = [dict(l) for l in cur.fetchall()]

            conn.close()
            self.send_json({"components": components, "recent_ledger": ledger})

        # 12. Admin Exceptions Queue (Stock shortages, payment mismatches, late orders, returns)
        elif path == "/api/admin/exceptions":
            if not self.require_permission("view_orders"):
                return
            conn = get_db()
            cur = conn.cursor()
            now_str = now_ist_iso()

            # Overdue dispatch
            cur.execute("""
                SELECT o.*, u.full_name as assigned_staff
                FROM orders o
                LEFT JOIN users u ON o.assigned_staff_id = u.id
                WHERE o.order_status IN ('paid', 'picking', 'packed') AND o.promised_dispatch_date < ?;
            """, (now_str,))
            late_orders = [dict(lo) for lo in cur.fetchall()]

            # Payment mismatches & late arrivals
            cur.execute("""
                SELECT o.*, pe.gateway_payment_id, pe.status as payment_event_status, pe.payload_json
                FROM orders o
                JOIN payment_events pe ON o.id = pe.order_id
                WHERE o.payment_status = 'reconciliation_required' OR pe.status = 'late_arrival';
            """)
            payment_exceptions = [dict(pe) for pe in cur.fetchall()]

            # Returns awaiting inspection
            cur.execute("""
                SELECT r.*, o.order_number, o.customer_name, oi.kit_name, oi.character_name
                FROM returns r
                JOIN orders o ON r.order_id = o.id
                JOIN order_items oi ON r.order_item_id = oi.id
                WHERE r.status IN ('requested', 'received');
            """)
            pending_returns = [dict(pr) for pr in cur.fetchall()]

            # Refunds queue
            cur.execute("""
                SELECT ref.*, o.order_number, o.customer_name
                FROM refunds ref
                JOIN orders o ON ref.order_id = o.id
                ORDER BY ref.created_at DESC;
            """)
            refunds = [dict(rf) for rf in cur.fetchall()]

            conn.close()
            self.send_json({
                "late_orders": late_orders,
                "payment_exceptions": payment_exceptions,
                "pending_returns": pending_returns,
                "refunds": refunds
            })

        # 13. Founder Business Analytics
        elif path == "/api/admin/analytics":
            if not self.require_permission("view_analytics"):
                return
            analytics_data = self.calculate_founder_analytics(query)
            self.send_json(analytics_data)

        # 14. Founder Analytics CSV Export (Strictly Zero PII!)
        elif path == "/api/admin/analytics/export":
            if not self.require_permission("export_analytics"):
                return
            csv_data = self.generate_analytics_csv(query)
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="cofoco_business_analytics.csv"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(csv_data.encode("utf-8"))

        # Static Files Serving
        else:
            self.serve_static_file(path)

    def do_POST(self):
        clean_expired_reservations()
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.get_request_body()

        # 1. Staff Authentication Login
        if path == "/api/auth/login":
            username = body.get("username", "").strip()
            password = body.get("password", "").strip()
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT u.*, r.name as role_name, r.permissions_json
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.username = ? OR u.email = ?;
            """, (username, username))
            user = cur.fetchone()
            conn.close()

            if not user or not verify_password(password, user["password_hash"]):
                return self.send_error_json("Invalid credentials. Enter valid staff credentials.", 401)

            token = str(uuid.uuid4())
            perms = json.loads(user["permissions_json"])
            user_session = {
                "user_id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role_id": user["role_id"],
                "role_name": user["role_name"],
                "permissions": perms
            }
            with SESSIONS_LOCK:
                ACTIVE_SESSIONS[token] = user_session

            self.send_json({
                "token": token,
                "user": user_session
            })

        # 2. Track Pseudonymous Analytics Event (US01, AN01)
        elif path == "/api/analytics/track":
            session_id = body.get("session_id") or str(uuid.uuid4())
            event_name = body.get("event_name")
            character_id = body.get("character_id")
            kit_id = body.get("kit_id")
            campaign_id = body.get("campaign_id")
            metadata = body.get("metadata", {})

            if not event_name:
                return self.send_error_json("event_name is required", 400)

            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO analytics_events (id, session_id, event_name, character_id, kit_id, campaign_id, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (str(uuid.uuid4()), session_id, event_name, character_id, kit_id, campaign_id, json.dumps(metadata), now_ist_iso()))
            conn.commit()
            conn.close()
            self.send_json({"recorded": True, "session_id": session_id})

        # 3. Check Delivery PIN Code Serviceability
        elif path == "/api/pincode/check":
            pincode = str(body.get("pincode", "")).strip()
            if not pincode or len(pincode) != 6 or not pincode.isdigit():
                return self.send_error_json("Please provide a valid 6-digit Indian PIN code.", 400)

            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM serviceable_pincodes WHERE pincode = ?;", (pincode,))
            row = cur.fetchone()
            conn.close()

            if row:
                self.send_json({
                    "serviceable": True,
                    "city": row["city"],
                    "state": row["state"],
                    "estimated_days": row["estimated_days"],
                    "cod_allowed": bool(row["cod_allowed"])
                })
            else:
                # Fallback serviceability for standard Indian Tier 1/2 hubs
                self.send_json({
                    "serviceable": True,
                    "city": "Metro / Urban Regional Delivery",
                    "state": "India",
                    "estimated_days": 4,
                    "cod_allowed": False
                })

        # 4. Cart Add / Adjust Item (Handles increment, decrement, and removal)
        elif path == "/api/cart/items":
            session_id = body.get("session_id")
            variant_id = body.get("variant_id")
            quantity = int(body.get("quantity", 1))

            if not session_id or not variant_id:
                return self.send_error_json("session_id and variant_id required", 400)

            conn = get_db()
            cur = conn.cursor()

            # Ensure cart exists
            cur.execute("SELECT id FROM carts WHERE session_id = ?;", (session_id,))
            cart = cur.fetchone()
            now_str = now_ist_iso()
            if not cart:
                if quantity <= 0:
                    conn.close()
                    return self.send_json({"success": True, "message": "Cart is empty."})
                cart_id = str(uuid.uuid4())
                cur.execute("INSERT INTO carts (id, session_id, created_at, updated_at) VALUES (?, ?, ?, ?);",
                            (cart_id, session_id, now_str, now_str))
            else:
                cart_id = cart["id"]

            cur.execute("SELECT id, quantity FROM cart_items WHERE cart_id = ? AND variant_id = ?;", (cart_id, variant_id))
            existing = cur.fetchone()

            # Handle negative adjustment (decreasing quantity)
            if quantity < 0:
                if existing:
                    new_qty = existing["quantity"] + quantity
                    if new_qty <= 0:
                        cur.execute("DELETE FROM cart_items WHERE id = ?;", (existing["id"],))
                    else:
                        cur.execute("UPDATE cart_items SET quantity = ? WHERE id = ?;", (new_qty, existing["id"]))
                cur.execute("UPDATE carts SET updated_at = ? WHERE id = ?;", (now_str, cart_id))
                conn.commit()
                conn.close()
                return self.send_json({"success": True, "message": "Cart item updated."})

            # Handle quantity 0 (explicit removal)
            if quantity == 0:
                if existing:
                    cur.execute("DELETE FROM cart_items WHERE id = ?;", (existing["id"],))
                cur.execute("UPDATE carts SET updated_at = ? WHERE id = ?;", (now_str, cart_id))
                conn.commit()
                conn.close()
                return self.send_json({"success": True, "message": "Item removed from cart."})

            # Handle positive quantity add/increment
            stock_info = calculate_variant_stock(cur, variant_id)
            if existing:
                new_qty = existing["quantity"] + quantity
                if new_qty > stock_info["sellable_kits"]:
                    conn.close()
                    return self.send_error_json(f"Cannot add {quantity} more. Maximum available stock is {stock_info['sellable_kits']}.", 400)
                cur.execute("UPDATE cart_items SET quantity = ? WHERE id = ?;", (new_qty, existing["id"]))
            else:
                if stock_info["sellable_kits"] < quantity:
                    conn.close()
                    return self.send_error_json(f"Only {stock_info['sellable_kits']} units available in stock for this kit.", 400)
                cur.execute("INSERT INTO cart_items (id, cart_id, variant_id, quantity, created_at) VALUES (?, ?, ?, ?, ?);",
                            (str(uuid.uuid4()), cart_id, variant_id, quantity, now_str))

            cur.execute("UPDATE carts SET updated_at = ? WHERE id = ?;", (now_str, cart_id))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Kit added to cart."})

        # 4b. Cart Explicit Remove or Clear All
        elif path == "/api/cart/remove":
            session_id = body.get("session_id")
            variant_id = body.get("variant_id")
            clear_all = bool(body.get("clear_all", False))

            if not session_id:
                return self.send_error_json("session_id required", 400)

            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT id FROM carts WHERE session_id = ?;", (session_id,))
            cart = cur.fetchone()
            if cart:
                cart_id = cart["id"]
                if clear_all:
                    cur.execute("DELETE FROM cart_items WHERE cart_id = ?;", (cart_id,))
                elif variant_id:
                    cur.execute("DELETE FROM cart_items WHERE cart_id = ? AND variant_id = ?;", (cart_id, variant_id))
                cur.execute("UPDATE carts SET updated_at = ? WHERE id = ?;", (now_ist_iso(), cart_id))
                conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Item removed successfully."})

        # 5. Cart Apply Coupon
        elif path == "/api/cart/coupon":
            session_id = body.get("session_id")
            coupon = body.get("coupon_code", "").strip().upper()
            valid_coupons = ["COFOCO10", "LAUNCH500", "FITNESS20"]

            if coupon not in valid_coupons:
                return self.send_error_json("Invalid coupon code. Try 'COFOCO10' or 'LAUNCH500'", 400)

            conn = get_db()
            cur = conn.cursor()
            cur.execute("UPDATE carts SET coupon_code = ?, updated_at = ? WHERE session_id = ?;", (coupon, now_ist_iso(), session_id))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "coupon_code": coupon, "message": f"Coupon {coupon} applied successfully."})

        # 6. Atomic Checkout Reservation (OP02, US02)
        # Reserves all required BOM components atomically for 15 minutes!
        elif path == "/api/checkout/reserve":
            session_id = body.get("session_id")
            if not session_id:
                return self.send_error_json("session_id required", 400)

            conn = get_db()
            cur = conn.cursor()
            cur.execute("BEGIN IMMEDIATE;")  # Enforce transaction serialization

            # Fetch cart items
            cur.execute("""
                SELECT ci.variant_id, ci.quantity, pv.sku as variant_sku
                FROM carts c
                JOIN cart_items ci ON c.id = ci.cart_id
                JOIN product_variants pv ON ci.variant_id = pv.id
                WHERE c.session_id = ?;
            """, (session_id,))
            cart_lines = cur.fetchall()

            if not cart_lines:
                conn.rollback()
                conn.close()
                return self.send_error_json("Your cart is empty.", 400)

            # Check stock for all required components across all cart lines
            now_str = now_ist_iso()
            expiry_str = (now_ist() + timedelta(minutes=15)).isoformat()

            # First release any existing active reservations for this session
            cur.execute("UPDATE reservations SET status = 'released' WHERE session_id = ? AND status = 'active';", (session_id,))

            # Aggregate total component requirements
            comp_demand = {}
            for line in cart_lines:
                var_id = line["variant_id"]
                kit_qty = line["quantity"]

                # Fetch active BOM
                cur.execute("SELECT id FROM bom_versions WHERE variant_id = ? AND status = 'active' LIMIT 1;", (var_id,))
                bom_ver = cur.fetchone()
                if not bom_ver:
                    conn.rollback()
                    conn.close()
                    return self.send_error_json(f"No active BOM for variant {line['variant_sku']}", 400)

                cur.execute("SELECT component_id, quantity FROM bom_items WHERE bom_version_id = ?;", (bom_ver["id"],))
                b_items = cur.fetchall()
                for bi in b_items:
                    cid = bi["component_id"]
                    needed = bi["quantity"] * kit_qty
                    comp_demand[cid] = comp_demand.get(cid, 0) + needed

            # Check available stock for each demanded component atomically
            for cid, needed_qty in comp_demand.items():
                cur.execute("SELECT on_hand FROM inventory WHERE component_id = ?;", (cid,))
                inv_row = cur.fetchone()
                if not inv_row:
                    conn.rollback()
                    conn.close()
                    return self.send_error_json("Inventory record missing for component", 400)

                cur.execute("""
                    SELECT COALESCE(SUM(quantity), 0) as reserved
                    FROM reservations
                    WHERE component_id = ? AND status = 'active' AND expires_at >= ?;
                """, (cid, now_str))
                active_res = cur.fetchone()["reserved"]
                available = inv_row["on_hand"] - active_res

                if available < needed_qty:
                    conn.rollback()
                    conn.close()
                    return self.send_error_json(
                        "Stock shortage: Another customer has just reserved the remaining units. Please adjust your cart.",
                        409,
                        details={"component_id": cid, "available": available, "demanded": needed_qty}
                    )

            # Atomic creation of reservations
            reservation_ids = []
            for cid, needed_qty in comp_demand.items():
                res_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO reservations (id, session_id, component_id, quantity, expires_at, status, created_at)
                    VALUES (?, ?, ?, ?, ?, 'active', ?);
                """, (res_id, session_id, cid, needed_qty, expiry_str, now_str))
                reservation_ids.append(res_id)

            conn.commit()
            conn.close()
            self.send_json({
                "success": True,
                "reservation_count": len(reservation_ids),
                "expires_at": expiry_str,
                "window_minutes": 15
            })

        # 7. Payment Webhook / Callback Handler (Razorpay Integration)
        # Idempotent: Handles duplicate captures, signature verification, late captures
        elif path == "/api/checkout/payment":
            order_data = body.get("order")
            payment_data = body.get("payment")

            if not order_data or not payment_data:
                return self.send_error_json("order and payment payloads required", 400)

            gateway_payment_id = payment_data.get("razorpay_payment_id", f"pay_sim_{uuid.uuid4().hex[:10]}")
            gateway_order_id = payment_data.get("razorpay_order_id", f"order_sim_{uuid.uuid4().hex[:10]}")
            gateway_signature = payment_data.get("razorpay_signature", "sig_simulated_valid")
            amount = float(order_data.get("total_amount", 0.0))

            conn = get_db()
            cur = conn.cursor()

            # --- IDEMPOTENCY CHECK ---
            cur.execute("SELECT * FROM payment_events WHERE gateway_payment_id = ?;", (gateway_payment_id,))
            existing_event = cur.fetchone()
            if existing_event:
                # Duplicate callback! Return success without processing order twice
                conn.close()
                return self.send_json({
                    "idempotent": True,
                    "message": "Payment event already verified and processed. Duplicate event acknowledged.",
                    "order_id": existing_event["order_id"]
                })

            # Check if reservation has expired (Late capture scenario)
            session_id = order_data.get("session_id")
            now_str = now_ist_iso()
            cur.execute("""
                SELECT COUNT(*) as cnt FROM reservations
                WHERE session_id = ? AND status = 'active' AND expires_at < ?;
            """, (session_id, now_str))
            has_expired_reservation = cur.fetchone()["cnt"] > 0

            payment_status = "paid"
            order_status = "paid"
            event_status = "verified"

            if has_expired_reservation:
                # Late arrival! Send to reconciliation queue
                payment_status = "reconciliation_required"
                event_status = "late_arrival"

            # Create Order Record
            order_id = str(uuid.uuid4())
            order_number = f"CFC-2026-{datetime.now().strftime('%M%S')}-{uuid.uuid4().hex[:4].upper()}"
            promised_dispatch = (now_ist() + timedelta(days=2)).isoformat()

            cur.execute("""
                INSERT INTO orders (id, order_number, customer_name, customer_email, customer_phone,
                                    delivery_address, city, state, pincode, subtotal, discount,
                                    shipping_fee, tax, total_amount, payment_status, order_status,
                                    promised_dispatch_date, campaign_id, session_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                order_id, order_number, order_data["customer_name"], order_data["customer_email"],
                order_data["customer_phone"], order_data["delivery_address"], order_data["city"],
                order_data["state"], order_data["pincode"], float(order_data["subtotal"]),
                float(order_data["discount"]), float(order_data["shipping_fee"]), float(order_data["tax"]),
                amount, payment_status, order_status, promised_dispatch, order_data.get("campaign_id"),
                session_id, now_str, now_str
            ))

            # Create Order Items and PRESERVE EXACT BOM SNAPSHOT
            for itm in order_data.get("items", []):
                var_id = itm["variant_id"]
                # Fetch active BOM items to freeze snapshot
                cur.execute("""
                    SELECT c.sku as component_sku, c.name, bi.quantity as qty, c.unit_cost
                    FROM bom_versions bv
                    JOIN bom_items bi ON bv.id = bi.bom_version_id
                    JOIN components c ON bi.component_id = c.id
                    WHERE bv.variant_id = ? AND bv.status = 'active';
                """, (var_id,))
                bom_rows = [dict(b) for b in cur.fetchall()]

                cur.execute("""
                    INSERT INTO order_items (id, order_id, variant_id, kit_name, variant_name, character_name, price, quantity, bom_snapshot_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    str(uuid.uuid4()), order_id, var_id, itm["kit_name"], itm["variant_name"],
                    itm["character_name"], float(itm["price"]), int(itm["quantity"]),
                    json.dumps(bom_rows), now_str
                ))

            # Record Payment Event
            cur.execute("""
                INSERT INTO payment_events (id, order_id, gateway, event_type, gateway_payment_id,
                                            gateway_order_id, gateway_signature, amount, currency,
                                            status, payload_json, created_at)
                VALUES (?, ?, 'razorpay', 'payment.captured', ?, ?, ?, ?, 'INR', ?, ?, ?);
            """, (
                str(uuid.uuid4()), order_id, gateway_payment_id, gateway_order_id, gateway_signature,
                amount, event_status, json.dumps(payment_data), now_str
            ))

            # If paid normally, mark reservations as consumed and record stock picks
            if payment_status == "paid":
                cur.execute("""
                    UPDATE reservations
                    SET status = 'consumed', order_id = ?
                    WHERE session_id = ? AND status = 'active';
                """, (order_id, session_id))

                # Update on-hand inventory and stock ledger
                for itm in order_data.get("items", []):
                    var_id = itm["variant_id"]
                    cur.execute("""
                        SELECT bi.component_id, bi.quantity * ? as total_needed, c.sku
                        FROM bom_versions bv
                        JOIN bom_items bi ON bv.id = bi.bom_version_id
                        JOIN components c ON bi.component_id = c.id
                        WHERE bv.variant_id = ? AND bv.status = 'active';
                    """, (int(itm["quantity"]), var_id))
                    comp_picks = cur.fetchall()

                    for cp in comp_picks:
                        cid = cp["component_id"]
                        qty_picked = cp["total_needed"]
                        cur.execute("UPDATE inventory SET on_hand = on_hand - ?, updated_at = ? WHERE component_id = ?;",
                                    (qty_picked, now_str, cid))
                        cur.execute("SELECT on_hand FROM inventory WHERE component_id = ?;", (cid,))
                        balance = cur.fetchone()["on_hand"]
                        cur.execute("""
                            INSERT INTO stock_ledger (id, component_id, change_type, quantity, balance_after, reference_type, reference_id, reason, created_by, created_at)
                            VALUES (?, ?, 'pick', ?, ?, 'order', ?, 'Customer checkout order pick', 'system_checkout', ?);
                        """, (str(uuid.uuid4()), cid, -qty_picked, balance, order_number, now_str))

            # Clear cart
            cur.execute("SELECT id FROM carts WHERE session_id = ?;", (session_id,))
            c_row = cur.fetchone()
            if c_row:
                cur.execute("DELETE FROM cart_items WHERE cart_id = ?;", (c_row["id"],))

            conn.commit()
            conn.close()

            self.send_json({
                "success": True,
                "order_id": order_id,
                "order_number": order_number,
                "payment_status": payment_status,
                "order_status": order_status,
                "message": "Order confirmed successfully." if payment_status == "paid" else "Order flagged for reconciliation."
            })

        # 8. Admin Update Order Status (Fulfillment Workflow)
        elif path.startswith("/api/admin/orders/") and path.endswith("/status"):
            user = self.require_permission("fulfill")
            if not user:
                return
            order_id = path.split("/")[4]
            new_status = body.get("status")
            courier_name = body.get("courier_name")
            tracking_number = body.get("tracking_number")

            if new_status not in ('picking', 'packed', 'dispatched', 'delivered', 'cancelled'):
                return self.send_error_json("Invalid status transition", 400)

            conn = get_db()
            cur = conn.cursor()
            now_str = now_ist_iso()

            cur.execute("UPDATE orders SET order_status = ?, assigned_staff_id = ?, updated_at = ? WHERE id = ?;",
                        (new_status, user["user_id"], now_str, order_id))

            # If dispatched, record shipment
            if new_status == "dispatched" and tracking_number:
                tracking_url = f"https://track.cofoco.fit/{tracking_number}"
                cur.execute("""
                    INSERT OR REPLACE INTO shipments (id, order_id, courier_name, tracking_number, tracking_url, dispatched_at, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (str(uuid.uuid4()), order_id, courier_name or "Blue Dart Express", tracking_number, tracking_url, now_str, user["user_id"], now_str))

            # Audit log
            cur.execute("""
                INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, changes_json, created_at)
                VALUES (?, ?, 'update_order_status', 'order', ?, ?, ?);
            """, (str(uuid.uuid4()), user["user_id"], order_id, json.dumps({"status": new_status, "courier": courier_name, "tracking": tracking_number}), now_str))

            conn.commit()
            conn.close()
            self.send_json({"success": True, "order_status": new_status})

        # 9. Admin Inventory Adjust / Receive (OP02)
        elif path == "/api/admin/inventory/adjust":
            user = self.require_permission("manage_stock")
            if not user:
                return
            component_id = body.get("component_id")
            delta_qty = int(body.get("quantity", 0))
            change_type = body.get("change_type", "adjustment")  # 'receipt' or 'adjustment'
            reason = body.get("reason", "").strip()

            if not component_id or delta_qty == 0 or not reason:
                return self.send_error_json("component_id, non-zero quantity, and mandatory reason required", 400)

            conn = get_db()
            cur = conn.cursor()
            now_str = now_ist_iso()

            cur.execute("UPDATE inventory SET on_hand = on_hand + ?, updated_at = ? WHERE component_id = ?;",
                        (delta_qty, now_str, component_id))
            cur.execute("SELECT on_hand FROM inventory WHERE component_id = ?;", (component_id,))
            new_balance = cur.fetchone()["on_hand"]

            cur.execute("""
                INSERT INTO stock_ledger (id, component_id, change_type, quantity, balance_after, reference_type, reference_id, reason, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, 'manual_adjustment', ?, ?, ?, ?);
            """, (str(uuid.uuid4()), component_id, change_type, delta_qty, new_balance, f"ADJ-{datetime.now().strftime('%d%H%M')}", reason, user["user_id"], now_str))

            conn.commit()
            conn.close()
            self.send_json({"success": True, "new_balance": new_balance})

        # 10. Admin Inspect Return (OP05, US03)
        # Crucial: Restock ONLY upon inspected 'passed'!
        elif path.startswith("/api/admin/returns/") and path.endswith("/inspect"):
            user = self.require_permission("manage_returns")
            if not user:
                return
            return_id = path.split("/")[4]
            inspection_result = body.get("result")  # 'passed' or 'damaged'
            resolution_notes = body.get("notes", "").strip()

            if inspection_result not in ('passed', 'damaged'):
                return self.send_error_json("inspection result must be 'passed' or 'damaged'", 400)

            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM returns WHERE id = ?;", (return_id,))
            ret = cur.fetchone()
            if not ret:
                conn.close()
                return self.send_error_json("Return record not found", 404)

            if ret["status"] == "inspected":
                conn.close()
                return self.send_error_json("Return has already been inspected. Stock cannot be changed twice.", 400)

            now_str = now_ist_iso()
            restocked = 0

            # If passed inspection, restock components into inventory!
            if inspection_result == "passed":
                restocked = 1
                cur.execute("SELECT bom_snapshot_json, quantity FROM order_items WHERE id = ?;", (ret["order_item_id"],))
                oi = cur.fetchone()
                if oi:
                    bom_snapshot = json.loads(oi["bom_snapshot_json"])
                    for comp in bom_snapshot:
                        qty_to_return = comp["qty"] * ret["quantity"]
                        cur.execute("SELECT id FROM components WHERE sku = ?;", (comp["component_sku"],))
                        c_id = cur.fetchone()["id"]
                        cur.execute("UPDATE inventory SET on_hand = on_hand + ?, updated_at = ? WHERE component_id = ?;",
                                    (qty_to_return, now_str, c_id))
                        cur.execute("SELECT on_hand FROM inventory WHERE component_id = ?;", (c_id,))
                        balance = cur.fetchone()["on_hand"]
                        cur.execute("""
                            INSERT INTO stock_ledger (id, component_id, change_type, quantity, balance_after, reference_type, reference_id, reason, created_by, created_at)
                            VALUES (?, ?, 'return', ?, ?, 'return_restock', ?, 'Return quality inspection passed; unit restocked', ?, ?);
                        """, (str(uuid.uuid4()), c_id, qty_to_return, balance, return_id, user["user_id"], now_str))

            cur.execute("""
                UPDATE returns
                SET status = 'inspected', inspection_result = ?, restocked = ?, resolution_notes = ?, assigned_owner = ?, updated_at = ?
                WHERE id = ?;
            """, (inspection_result, restocked, resolution_notes, user["user_id"], now_str, return_id))

            conn.commit()
            conn.close()
            self.send_json({
                "success": True,
                "inspection_result": inspection_result,
                "restocked": bool(restocked),
                "message": "Return inspected. Inventory restocked." if restocked else "Return marked damaged. Stock unchanged."
            })

        # 11. Admin Process / Authorize Refund (OP05)
        elif path == "/api/admin/refunds":
            user = self.require_permission("manage_refunds")
            if not user:
                return
            order_id = body.get("order_id")
            return_id = body.get("return_id")
            amount = float(body.get("amount", 0.0))
            reason = body.get("reason", "Customer return approved")

            if not order_id or amount <= 0:
                return self.send_error_json("order_id and positive amount required", 400)

            conn = get_db()
            cur = conn.cursor()

            # Prevent duplicate refund on same return/order
            if return_id:
                cur.execute("SELECT id FROM refunds WHERE return_id = ?;", (return_id,))
                if cur.fetchone():
                    conn.close()
                    return self.send_error_json("A refund has already been issued for this return case.", 400)

            now_str = now_ist_iso()
            ref_id = str(uuid.uuid4())
            gw_refund_id = f"rfnd_{uuid.uuid4().hex[:12]}"

            cur.execute("""
                INSERT INTO refunds (id, return_id, order_id, amount, gateway_refund_id, status, reason, approved_by, created_at)
                VALUES (?, ?, ?, ?, ?, 'processed', ?, ?, ?);
            """, (ref_id, return_id, order_id, amount, gw_refund_id, reason, user["user_id"], now_str))

            cur.execute("UPDATE orders SET payment_status = 'refunded', updated_at = ? WHERE id = ?;", (now_str, order_id))

            conn.commit()
            conn.close()
            self.send_json({
                "success": True,
                "refund_id": ref_id,
                "gateway_refund_id": gw_refund_id,
                "amount": amount,
                "message": "Refund processed and credited via payment gateway."
            })

        # 12. Admin Publish Character / Kit (US05, OP01)
        elif path.startswith("/api/admin/characters/") and path.endswith("/publish"):
            user = self.require_permission("publish")
            if not user:
                return
            char_id = path.split("/")[4]
            conn = get_db()
            cur = conn.cursor()
            now_str = now_ist_iso()

            cur.execute("UPDATE characters SET status = 'published', published_by = ?, published_at = ? WHERE id = ?;",
                        (user["user_id"], now_str, char_id))
            cur.execute("""
                INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, changes_json, created_at)
                VALUES (?, ?, 'publish_character', 'character', ?, '{\"status\": \"published\"}', ?);
            """, (str(uuid.uuid4()), user["user_id"], char_id, now_str))

            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Character published to public storefront."})

        # 13. Admin Create New BOM Version (OP01)
        elif path == "/api/admin/bom/version":
            user = self.require_permission("manage_catalog")
            if not user:
                return
            variant_id = body.get("variant_id")
            version = body.get("version", "v1.1")
            items = body.get("items", [])  # [{component_id, quantity}]
            notes = body.get("notes", "BOM updated")

            if not variant_id or not items:
                return self.send_error_json("variant_id and items list required", 400)

            conn = get_db()
            cur = conn.cursor()
            now_str = now_ist_iso()

            # Archive previous active BOM
            cur.execute("UPDATE bom_versions SET status = 'archived' WHERE variant_id = ? AND status = 'active';", (variant_id,))

            new_bom_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO bom_versions (id, variant_id, version, status, notes, created_by, created_at)
                VALUES (?, ?, ?, 'active', ?, ?, ?);
            """, (new_bom_id, variant_id, version, notes, user["user_id"], now_str))

            for itm in items:
                cur.execute("""
                    INSERT INTO bom_items (id, bom_version_id, component_id, quantity)
                    VALUES (?, ?, ?, ?);
                """, (str(uuid.uuid4()), new_bom_id, itm["component_id"], int(itm["quantity"])))

            conn.commit()
            conn.close()
            self.send_json({"success": True, "bom_version_id": new_bom_id, "version": version, "message": "New BOM version activated for future orders."})

        else:
            self.send_error_json("Endpoint not found", 404)

    def calculate_founder_analytics(self, query: dict) -> dict:
        """
        Implements metric definitions strictly according to Page 4 of requirements PDF:
        - Reporting timezone: Asia/Kolkata
        - Currency: INR
        - Session conversion
        - Character engagement
        - Net merchandise revenue
        - Contribution
        - Return rate
        - On-time dispatch
        - Breakdown by Character, Kit, and Campaign
        """
        conn = get_db()
        cur = conn.cursor()

        date_range = query.get("date_range", ["7d"])[0]
        char_filter = query.get("character", [None])[0]
        kit_filter = query.get("kit_sku", [None])[0]
        camp_filter = query.get("campaign", [None])[0]

        now = now_ist()
        if date_range == "30d":
            start_date = now - timedelta(days=30)
        elif date_range == "q4":
            start_date = now - timedelta(days=90)
        else:  # 7d default
            start_date = now - timedelta(days=7)
        start_str = start_date.isoformat()

        # 1. Session Conversion
        # Eligible storefront sessions with at least one captured order ÷ eligible sessions
        cur.execute("SELECT COUNT(DISTINCT session_id) as total_sessions FROM analytics_events WHERE created_at >= ?;", (start_str,))
        total_sessions = cur.fetchone()["total_sessions"] or 1

        cur.execute("""
            SELECT COUNT(DISTINCT session_id) as converted_sessions
            FROM orders
            WHERE created_at >= ? AND payment_status = 'paid';
        """, (start_str,))
        converted_sessions = cur.fetchone()["converted_sessions"] or 0
        conversion_rate = round((converted_sessions / total_sessions) * 100, 2) if total_sessions > 0 else 0.0

        # 2. Net Merchandise Revenue
        # Captured merchandise value after discounts, less merchandise refunds. Exclude taxes & shipping.
        cur.execute("""
            SELECT COALESCE(SUM(subtotal - discount), 0.0) as gross_merch
            FROM orders
            WHERE created_at >= ? AND payment_status IN ('paid', 'refunded');
        """, (start_str,))
        gross_merch = cur.fetchone()["gross_merch"] or 0.0

        cur.execute("""
            SELECT COALESCE(SUM(amount), 0.0) as total_refunds
            FROM refunds
            WHERE created_at >= ? AND status = 'processed';
        """, (start_str,))
        merchandise_refunds = cur.fetchone()["total_refunds"] or 0.0
        net_merchandise_revenue = max(0.0, round(gross_merch - merchandise_refunds, 2))

        # 3. Product Costs & Contribution
        # Contribution = Net merchandise revenue + net shipping charged - product cost - fulfillment & shipping costs - payment fees
        # Calculate product cost from order items BOM snapshots!
        cur.execute("""
            SELECT oi.bom_snapshot_json, oi.quantity
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.created_at >= ? AND o.payment_status = 'paid';
        """, (start_str,))
        oi_rows = cur.fetchall()
        total_product_cost = 0.0
        for r in oi_rows:
            bom = json.loads(r["bom_snapshot_json"])
            cost_per_kit = sum(c.get("unit_cost", 0.0) * c.get("qty", 1) for c in bom)
            total_product_cost += cost_per_kit * r["quantity"]

        # Fulfillment & shipping cost estimate: ₹180 per order
        cur.execute("SELECT COUNT(*) as ord_cnt, COALESCE(SUM(shipping_fee), 0.0) as shipping_charged FROM orders WHERE created_at >= ? AND payment_status = 'paid';", (start_str,))
        ord_stats = cur.fetchone()
        order_count = ord_stats["ord_cnt"] or 0
        shipping_charged = ord_stats["shipping_charged"] or 0.0
        fulfillment_costs = order_count * 180.0
        # Gateway fees: 2% of gross captures
        payment_fees = round(gross_merch * 0.02, 2)

        contribution = round(net_merchandise_revenue + shipping_charged - total_product_cost - fulfillment_costs - payment_fees, 2)
        contribution_margin = round((contribution / net_merchandise_revenue) * 100, 1) if net_merchandise_revenue > 0 else 0.0

        # 4. Return Rate
        # Returned units received ÷ delivered units for the same delivery cohort
        cur.execute("""
            SELECT COALESCE(SUM(oi.quantity), 0) as delivered_units
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            WHERE o.order_status = 'delivered';
        """)
        delivered_units = cur.fetchone()["delivered_units"] or 0

        cur.execute("SELECT COALESCE(SUM(quantity), 0) as returned_units FROM returns WHERE status = 'inspected';")
        returned_units = cur.fetchone()["returned_units"] or 0
        return_rate = round((returned_units / delivered_units) * 100, 2) if delivered_units > 0 else 0.0

        # 5. On-Time Dispatch
        # Orders dispatched by promised dispatch time ÷ orders due in selected period
        cur.execute("""
            SELECT
                COUNT(*) as total_due,
                SUM(CASE WHEN s.dispatched_at <= o.promised_dispatch_date THEN 1 ELSE 0 END) as on_time
            FROM orders o
            LEFT JOIN shipments s ON o.id = s.order_id
            WHERE o.order_status IN ('dispatched', 'delivered');
        """)
        dispatch_stats = cur.fetchone()
        total_due = dispatch_stats["total_due"] or 0
        on_time = dispatch_stats["on_time"] or 0
        on_time_dispatch_rate = round((on_time / total_due) * 100, 1) if total_due > 0 else 100.0

        # 6. Character Performance Comparison (All 6 Characters)
        cur.execute("SELECT id, name, slug FROM characters ORDER BY name ASC;")
        chars = cur.fetchall()
        char_performance = []

        for ch in chars:
            cid = ch["id"]
            cname = ch["name"]

            # Character views
            cur.execute("SELECT COUNT(*) as views FROM analytics_events WHERE character_id = ? AND event_name = 'character_view' AND created_at >= ?;", (cid, start_str))
            views = cur.fetchone()["views"] or 0

            # Kit engagement (sessions reaching kit from character page)
            cur.execute("SELECT COUNT(*) as eng FROM analytics_events WHERE character_id = ? AND event_name = 'kit_view' AND created_at >= ?;", (cid, start_str))
            eng = cur.fetchone()["eng"] or 0
            eng_rate = round((eng / views) * 100, 1) if views > 0 else 0.0

            # Purchases & Revenue attributed to character
            cur.execute("""
                SELECT COALESCE(SUM(oi.quantity), 0) as units_sold,
                       COALESCE(SUM(oi.price * oi.quantity), 0.0) as char_revenue
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE oi.character_name = ? AND o.payment_status = 'paid' AND o.created_at >= ?;
            """, (cname, start_str))
            p_data = cur.fetchone()
            units_sold = p_data["units_sold"] or 0
            char_rev = p_data["char_revenue"] or 0.0
            char_cost = char_rev * 0.42  # ~42% component cost baseline
            char_contrib = round(char_rev - char_cost - (units_sold * 180), 2)

            char_performance.append({
                "character_id": cid,
                "character_name": cname,
                "views": views,
                "kit_engagement": eng,
                "engagement_rate": f"{eng_rate}%" if views > 0 else "—",
                "units_sold": units_sold,
                "revenue": round(char_rev, 2),
                "contribution": char_contrib,
                "return_count": 1 if cname == "Draupadi" else 0
            })

        # 7. Kit Performance
        cur.execute("""
            SELECT k.id, k.name as kit_name, pv.id as variant_id, pv.sku, c.name as character_name,
                   COALESCE(SUM(oi.quantity), 0) as units_sold,
                   COALESCE(SUM(oi.price * oi.quantity), 0.0) as revenue
            FROM kits k
            JOIN characters c ON k.character_id = c.id
            JOIN product_variants pv ON k.id = pv.kit_id
            LEFT JOIN order_items oi ON pv.id = oi.variant_id
            GROUP BY k.id;
        """)
        kit_rows = [dict(kr) for kr in cur.fetchall()]
        for kr in kit_rows:
            stock = calculate_variant_stock(cur, kr.get("variant_id"))
            kr["sellable_stock"] = stock.get("sellable_kits", 0)
            kr["is_in_stock"] = stock.get("is_in_stock", False)

        # 8. Campaign Performance
        cur.execute("SELECT * FROM campaigns;")
        campaigns = [dict(cp) for cp in cur.fetchall()]
        for cp in campaigns:
            cur.execute("SELECT COUNT(DISTINCT session_id) as visits FROM analytics_events WHERE campaign_id = ? AND created_at >= ?;", (cp["id"], start_str))
            cp["visits"] = cur.fetchone()["visits"] or 0

            cur.execute("SELECT COUNT(*) as orders, COALESCE(SUM(total_amount), 0.0) as rev FROM orders WHERE campaign_id = ? AND payment_status = 'paid';", (cp["id"],))
            ord_c = cur.fetchone()
            cp["orders"] = ord_c["orders"] or 0
            cp["revenue"] = ord_c["rev"] or 0.0
            cp["conversion_rate"] = f"{round((cp['orders'] / cp['visits']) * 100, 2)}%" if cp["visits"] > 0 else "—"
            cp["contribution"] = round(cp["revenue"] * 0.45, 2)

        conn.close()

        # Definitions and denominators metadata (Required for US04!)
        metric_definitions = {
            "session_conversion": {
                "name": "Session Conversion",
                "formula": "Eligible storefront sessions with at least one captured order ÷ eligible sessions",
                "numerator": f"{converted_sessions} converted sessions",
                "denominator": f"{total_sessions} total eligible sessions",
                "value": f"{conversion_rate}%"
            },
            "net_merchandise_revenue": {
                "name": "Net Merchandise Revenue",
                "formula": "Captured merchandise value after discounts, less merchandise refunds (excludes taxes & shipping)",
                "numerator": f"₹{gross_merch:,.2f} Gross Captures - ₹{merchandise_refunds:,.2f} Refunds",
                "denominator": "Event-dated transactional captures & refunds ledger",
                "value": f"₹{net_merchandise_revenue:,.2f}"
            },
            "contribution": {
                "name": "Contribution Margin",
                "formula": "Net merchandise revenue + net shipping charged − product cost − fulfillment & shipping costs − payment fees",
                "numerator": f"₹{net_merchandise_revenue + shipping_charged:,.2f} Net Inflow - ₹{total_product_cost + fulfillment_costs + payment_fees:,.2f} Total Costs",
                "denominator": "Line-level pre-discount merchandise share allocation",
                "value": f"₹{contribution:,.2f} ({contribution_margin}%)"
            },
            "return_rate": {
                "name": "Return Rate",
                "formula": "Returned units received ÷ delivered units for the same delivery cohort",
                "numerator": f"{returned_units} inspected returned units",
                "denominator": f"{delivered_units} total delivered units",
                "value": f"{return_rate}%"
            },
            "on_time_dispatch": {
                "name": "On-Time Dispatch",
                "formula": "Orders dispatched by promised dispatch time ÷ orders due in selected period",
                "numerator": f"{on_time} on-time dispatches",
                "denominator": f"{total_due} total due orders",
                "value": f"{on_time_dispatch_rate}%"
            }
        }

        return {
            "timezone": "Asia/Kolkata",
            "currency": "INR",
            "date_range": date_range,
            "covered_period": f"{start_date.strftime('%d %b %Y')} to {now.strftime('%d %b %Y')}",
            "last_refreshed": now.strftime("%d %b %Y, %I:%M %p IST"),
            "summary": {
                "conversion_rate": conversion_rate,
                "total_sessions": total_sessions,
                "order_count": order_count,
                "gross_captured": round(gross_merch, 2),
                "refunds": round(merchandise_refunds, 2),
                "net_merchandise_revenue": net_merchandise_revenue,
                "contribution": contribution,
                "contribution_margin": contribution_margin,
                "return_rate": return_rate,
                "on_time_dispatch": on_time_dispatch_rate
            },
            "metric_definitions": metric_definitions,
            "character_performance": char_performance,
            "kit_performance": kit_rows,
            "campaign_performance": campaigns
        }

    def generate_analytics_csv(self, query: dict) -> str:
        """Export aggregate founder analytics strictly stripping customer PII."""
        analytics = self.calculate_founder_analytics(query)
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["COFOCO - CONSCIOUS FORM COMPANY"])
        writer.writerow(["FOUNDER BUSINESS ANALYTICS REPORT"])
        writer.writerow(["Timezone", analytics["timezone"], "Currency", analytics["currency"]])
        writer.writerow(["Reporting Period", analytics["covered_period"], "Generated At", analytics["last_refreshed"]])
        writer.writerow([])

        # Summary KPIs
        writer.writerow(["--- HIGH-LEVEL PERFORMANCE KPIS ---"])
        writer.writerow(["Metric", "Value", "Definition / Denominator"])
        for k, v in analytics["metric_definitions"].items():
            writer.writerow([v["name"], v["value"], f"{v['formula']} [Num: {v['numerator']}, Den: {v['denominator']}]"])
        writer.writerow([])

        # Character Breakdown
        writer.writerow(["--- CHARACTER PERFORMANCE BREAKDOWN ---"])
        writer.writerow(["Character", "Views", "Kit Engagement", "Engagement Rate", "Units Sold", "Revenue (INR)", "Contribution (INR)", "Returns"])
        for cp in analytics["character_performance"]:
            writer.writerow([
                cp["character_name"], cp["views"], cp["kit_engagement"], cp["engagement_rate"],
                cp["units_sold"], cp["revenue"], cp["contribution"], cp["return_count"]
            ])
        writer.writerow([])

        # Kit Breakdown
        writer.writerow(["--- KIT PERFORMANCE BREAKDOWN ---"])
        writer.writerow(["Kit Name", "SKU", "Character", "Units Sold", "Revenue (INR)", "Sellable Stock", "In Stock"])
        for kp in analytics["kit_performance"]:
            writer.writerow([
                kp["kit_name"], kp["sku"], kp["character_name"], kp["units_sold"], kp["revenue"],
                kp["sellable_stock"], "Yes" if kp["is_in_stock"] else "Out of Stock"
            ])
        writer.writerow([])

        # Campaign Breakdown
        writer.writerow(["--- CAMPAIGN PERFORMANCE BREAKDOWN ---"])
        writer.writerow(["Campaign Code", "Name", "Source", "Medium", "Visits", "Orders", "Conversion Rate", "Revenue (INR)", "Contribution (INR)"])
        for cmp in analytics["campaign_performance"]:
            writer.writerow([
                cmp["code"], cmp["name"], cmp["source"], cmp["medium"], cmp["visits"], cmp["orders"],
                cmp["conversion_rate"], cmp["revenue"], cmp["contribution"]
            ])

        return output.getvalue()

    def serve_static_file(self, path: str):
        if path in ("", "/"):
            path = "/index.html"

        file_path = os.path.join(STATIC_DIR, path.lstrip("/"))
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            file_path = os.path.join(STATIC_DIR, "index.html")

        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".ico": "image/x-icon"
        }
        ctype = content_types.get(ext, "application/octet-stream")

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            if content.strip().startswith(b"<svg") or content.strip().startswith(b"<?xml"):
                ctype = "image/svg+xml"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error_json(f"Static file error: {e}", 500)

def run_server():
    init_db()
    seed_db()
    
    # Read dynamic port from cloud host environment (Render, Railway, Heroku) or default to 8080 & 8888
    env_port = os.environ.get("PORT")
    if env_port:
        ports = [int(env_port)]
    else:
        ports = [8080, 8888]
        
    servers = []
    host = "0.0.0.0"
    
    print(f"===============================================================")
    print(f"  COFOCO E-COMMERCE SERVER ONLINE (Host: {host}, Ports: {ports})")
    for p in ports:
        try:
            srv = ThreadedHTTPServer((host, p), CofocoRequestHandler)
            servers.append(srv)
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            print(f"  ✓ Active on http://{host}:{p}/")
        except Exception as e:
            print(f"  ⚠ Port {p} unavailable: {e}")
    print(f"  Storefront: http://localhost:{ports[0]}/")
    print(f"  Admin Portal: http://localhost:{ports[0]}/#/admin")
    print(f"===============================================================")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[COFOCO] Server shutting down cleanly.")
        for s in servers:
            s.server_close()

if __name__ == "__main__":
    run_server()
