#!/usr/bin/env python3
"""Setup script for shop-website project in Komajdon."""

import json, sys, os, time, urllib.request, urllib.error

BASE = "http://localhost:8000"
TOKEN = open("/tmp/shop_token.txt").read().strip()
HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}

def api(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  ERROR {e.code} on {method} {path}: {err[:200]}")
        return None

# ── 1. Create Project ──────────────────────────────────
print("=== Creating shop-website project ===")
r = api("POST", "/api/projects/", {"name": "Shop Website", "slug": "shop-website", "description": "E-commerce shop backend"})
if r: print(f"  Project created: {r.get('id','?')}")

PROJECT_ID = r.get("id") if r else None

# Set project header for subsequent calls
def api_p(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    h = dict(HEADERS)
    if PROJECT_ID: h["X-Project-Id"] = PROJECT_ID
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  ERROR {e.code} on {method} {path}: {err[:200]}")
        return None

# ── 2. Create Models ───────────────────────────────────
print("\n=== Creating Models ===")

models = [
    {
        "name": "Category",
        "fields": [
            {"name": "name", "type": "string", "required": True, "validation": {"unique": True}},
            {"name": "slug", "type": "string", "required": True, "validation": {"unique": True}},
            {"name": "description", "type": "string"},
            {"name": "image_url", "type": "string"},
        ],
        "indexes": [{"field": "slug", "direction": 1, "unique": True}],
        "auth_protected": False,
        "realtime_enabled": False,
    },
    {
        "name": "Product",
        "fields": [
            {"name": "name", "type": "string", "required": True},
            {"name": "description", "type": "string"},
            {"name": "price", "type": "number", "required": True, "validation": {"minimum": 0}},
            {"name": "category", "type": "relation", "relation": {"type": "belongs_to", "target_model": "Category", "foreign_key": "category_id"}},
            {"name": "image_url", "type": "string"},
            {"name": "stock", "type": "number", "required": True, "validation": {"minimum": 0}},
            {"name": "sku", "type": "string", "required": True, "validation": {"unique": True}},
            {"name": "is_active", "type": "boolean"},
        ],
        "indexes": [{"field": "sku", "direction": 1, "unique": True}, {"field": "category_id", "direction": 1}],
        "auth_protected": False,
        "realtime_enabled": False,
    },
    {
        "name": "Customer",
        "fields": [
            {"name": "first_name", "type": "string", "required": True},
            {"name": "last_name", "type": "string", "required": True},
            {"name": "email", "type": "string", "required": True, "validation": {"unique": True}},
            {"name": "phone", "type": "string"},
            {"name": "address", "type": "string"},
            {"name": "user_id", "type": "string"},
        ],
        "indexes": [{"field": "email", "direction": 1, "unique": True}],
        "auth_protected": True,
        "realtime_enabled": False,
    },
    {
        "name": "Order",
        "fields": [
            {"name": "customer", "type": "relation", "relation": {"type": "belongs_to", "target_model": "Customer", "foreign_key": "customer_id"}},
            {"name": "items", "type": "array"},
            {"name": "total", "type": "number", "required": True, "validation": {"minimum": 0}},
            {"name": "status", "type": "string", "validation": {"enum": ["pending", "confirmed", "shipped", "delivered", "cancelled"]}},
            {"name": "shipping_address", "type": "string"},
            {"name": "created_at", "type": "date"},
        ],
        "indexes": [{"field": "customer_id", "direction": 1}, {"field": "status", "direction": 1}],
        "auth_protected": True,
        "realtime_enabled": False,
    },
    {
        "name": "OrderItem",
        "fields": [
            {"name": "order", "type": "relation", "relation": {"type": "belongs_to", "target_model": "Order", "foreign_key": "order_id"}},
            {"name": "product", "type": "relation", "relation": {"type": "belongs_to", "target_model": "Product", "foreign_key": "product_id"}},
            {"name": "quantity", "type": "number", "required": True, "validation": {"minimum": 1}},
            {"name": "unit_price", "type": "number", "required": True, "validation": {"minimum": 0}},
        ],
        "indexes": [{"field": "order_id", "direction": 1}, {"field": "product_id", "direction": 1}],
        "auth_protected": True,
        "realtime_enabled": False,
    },
    {
        "name": "Cart",
        "fields": [
            {"name": "customer", "type": "relation", "relation": {"type": "belongs_to", "target_model": "Customer", "foreign_key": "customer_id"}},
            {"name": "items", "type": "array"},
            {"name": "created_at", "type": "date"},
        ],
        "indexes": [{"field": "customer_id", "direction": 1, "unique": True}],
        "auth_protected": True,
        "realtime_enabled": False,
    },
    {
        "name": "CartItem",
        "fields": [
            {"name": "cart", "type": "relation", "relation": {"type": "belongs_to", "target_model": "Cart", "foreign_key": "cart_id"}},
            {"name": "product", "type": "relation", "relation": {"type": "belongs_to", "target_model": "Product", "foreign_key": "product_id"}},
            {"name": "quantity", "type": "number", "required": True, "validation": {"minimum": 1}},
        ],
        "indexes": [{"field": "cart_id", "direction": 1}, {"field": "product_id", "direction": 1}],
        "auth_protected": True,
        "realtime_enabled": False,
    },
    {
        "name": "Review",
        "fields": [
            {"name": "product", "type": "relation", "relation": {"type": "belongs_to", "target_model": "Product", "foreign_key": "product_id"}},
            {"name": "customer", "type": "relation", "relation": {"type": "belongs_to", "target_model": "Customer", "foreign_key": "customer_id"}},
            {"name": "rating", "type": "number", "required": True, "validation": {"minimum": 1, "maximum": 5}},
            {"name": "comment", "type": "string"},
            {"name": "created_at", "type": "date"},
        ],
        "indexes": [{"field": "product_id", "direction": 1}, {"field": "customer_id", "direction": 1}],
        "auth_protected": False,
        "realtime_enabled": False,
    },
]

created_models = {}
for m in models:
    print(f"  Creating {m['name']}...", end=" ")
    r = api_p("POST", "/api/models/", m)
    if r:
        print("OK")
        created_models[m["name"]] = r.get("id")
    else:
        print("FAILED")

# ── 3. Seed Sample Data ────────────────────────────────
print("\n=== Seeding Sample Data ===")

# Categories
cats = [
    {"name": "Electronics", "slug": "electronics", "description": "Gadgets, devices, and accessories"},
    {"name": "Clothing", "slug": "clothing", "description": "Apparel and fashion"},
    {"name": "Home & Garden", "slug": "home-garden", "description": "Furniture, decor, and gardening"},
    {"name": "Books", "slug": "books", "description": "Physical and digital books"},
]
cat_ids = {}
for c in cats:
    print(f"  Category: {c['name']}...", end=" ")
    r = api_p("POST", "/api/Category", c)
    if r:
        cat_ids[c["name"]] = r.get("_id") or list(r.values())[0]
        print(f"OK ({cat_ids[c['name']]})")
    else:
        print("FAILED")

# Products
products_data = [
    {"name": "Wireless Headphones", "price": 79.99, "stock": 50, "sku": "WH-001", "is_active": True,
     "description": "Bluetooth 5.0 noise-cancelling headphones", "category_id": cat_ids.get("Electronics"), "image_url": ""},
    {"name": "Smart Watch", "price": 199.99, "stock": 30, "sku": "SW-002", "is_active": True,
     "description": "Fitness tracker with heart rate monitor", "category_id": cat_ids.get("Electronics"), "image_url": ""},
    {"name": "Cotton T-Shirt", "price": 24.99, "stock": 200, "sku": "CT-001", "is_active": True,
     "description": "100% organic cotton, available in 5 colors", "category_id": cat_ids.get("Clothing"), "image_url": ""},
    {"name": "Denim Jacket", "price": 89.99, "stock": 40, "sku": "DJ-002", "is_active": True,
     "description": "Classic denim jacket with a modern fit", "category_id": cat_ids.get("Clothing"), "image_url": ""},
    {"name": "Indoor Plant Pot", "price": 34.99, "stock": 100, "sku": "HP-001", "is_active": True,
     "description": "Ceramic pot with drainage, 12-inch diameter", "category_id": cat_ids.get("Home & Garden"), "image_url": ""},
    {"name": "LED Desk Lamp", "price": 49.99, "stock": 75, "sku": "LM-001", "is_active": True,
     "description": "Adjustable brightness, USB charging port", "category_id": cat_ids.get("Electronics"), "image_url": ""},
    {"name": "JavaScript: The Good Parts", "price": 29.99, "stock": 60, "sku": "BK-001", "is_active": True,
     "description": "Deep dive into JavaScript fundamentals", "category_id": cat_ids.get("Books"), "image_url": ""},
    {"name": "Design Patterns", "price": 44.99, "stock": 45, "sku": "BK-002", "is_active": True,
     "description": "Gang of Four design patterns explained", "category_id": cat_ids.get("Books"), "image_url": ""},
]
product_ids = {}
for p in products_data:
    print(f"  Product: {p['name']}...", end=" ")
    r = api_p("POST", "/api/Product", {k: v for k, v in p.items() if v is not None})
    if r:
        pid = r.get("_id") or list(r.values())[0]
        product_ids[p["sku"]] = pid
        print(f"OK ({pid[:8]}...)")
    else:
        print("FAILED")

# Customer
print(f"  Creating customer...", end=" ")
r = api_p("POST", "/api/Customer", {
    "first_name": "John", "last_name": "Doe",
    "email": "john@example.com", "phone": "+1-555-0100",
    "address": "123 Main St, Springfield, USA"
})
if r:
    customer_id = r.get("_id") or list(r.values())[0]
    print(f"OK ({customer_id[:8]}...)")
else:
    customer_id = None
    print("FAILED")

# Order
if customer_id:
    print(f"  Creating Order...", end=" ")
    r = api_p("POST", "/api/Order", {
        "customer_id": customer_id, "total": 289.96,
        "status": "delivered", "shipping_address": "123 Main St, Springfield, USA",
        "items": [
            {"product_id": product_ids.get("WH-001"), "quantity": 1, "unit_price": 79.99},
            {"product_id": product_ids.get("SW-002"), "quantity": 1, "unit_price": 199.99},
            {"product_id": product_ids.get("HP-001"), "quantity": 1, "unit_price": 34.99},
        ]
    })
    if r:
        order_id = r.get("_id") or list(r.values())[0]
        print(f"OK ({order_id[:8]}...)")

    # Second order
    print(f"  Creating Order 2...", end=" ")
    r = api_p("POST", "/api/Order", {
        "customer_id": customer_id, "total": 104.98,
        "status": "pending", "shipping_address": "123 Main St, Springfield, USA",
        "items": [
            {"product_id": product_ids.get("CT-001"), "quantity": 2, "unit_price": 24.99},
            {"product_id": product_ids.get("BK-001"), "quantity": 1, "unit_price": 29.99},
        ]
    })
    if r: print(f"OK")

# Review
for rating, comment, sku in [
    (5, "Amazing sound quality!", "WH-001"),
    (4, "Great watch, battery lasts 3 days", "SW-002"),
    (5, "Very comfortable, fits perfectly", "CT-001"),
    (3, "Nice pot but smaller than expected", "HP-001"),
]:
    if customer_id and product_ids.get(sku):
        print(f"  Review for {sku}...", end=" ")
        r = api_p("POST", "/api/Review", {
            "product_id": product_ids[sku], "customer_id": customer_id,
            "rating": rating, "comment": comment,
        })
        if r: print("OK")
        else: print("FAILED")

# ── 4. Create Aggregation Pipelines ───────────────────
print("\n=== Creating Aggregation Pipelines ===")

pipelines = [
    {
        "name": "Revenue by Category",
        "collection": "Order",
        "stages": [
            {"type": "match", "params": {"status": {"$ne": "cancelled"}}},
            {"type": "group", "params": {"_id": "$status", "total_revenue": {"$sum": "$total"}, "count": {"$sum": 1}}},
            {"type": "sort", "params": {"total_revenue": -1}},
        ],
    },
    {
        "name": "Top Selling Products",
        "collection": "OrderItem",
        "stages": [
            {"type": "group", "params": {"_id": "$product_id", "total_sold": {"$sum": "$quantity"}, "revenue": {"$sum": {"$multiply": ["$quantity", "$unit_price"]}}}},
            {"type": "sort", "params": {"total_sold": -1}},
            {"type": "limit", "params": {"limit": 10}},
        ],
    },
    {
        "name": "Average Ratings per Product",
        "collection": "Review",
        "stages": [
            {"type": "group", "params": {"_id": "$product_id", "avg_rating": {"$avg": "$rating"}, "total_reviews": {"$sum": 1}}},
            {"type": "sort", "params": {"avg_rating": -1}},
        ],
    },
    {
        "name": "Customer Order Summary",
        "collection": "Order",
        "stages": [
            {"type": "group", "params": {"_id": "$customer_id", "order_count": {"$sum": 1}, "total_spent": {"$sum": "$total"}}},
            {"type": "sort", "params": {"total_spent": -1}},
        ],
    },
    {
        "name": "Product Inventory Status",
        "collection": "Product",
        "stages": [
            {"type": "match", "params": {"is_active": True}},
            {"type": "group", "params": {"_id": None, "total_products": {"$sum": 1}, "total_stock": {"$sum": "$stock"}, "avg_price": {"$avg": "$price"}}},
        ],
    },
]

pipeline_ids = []
for p in pipelines:
    print(f"  Pipeline: {p['name']}...", end=" ")
    r = api_p("POST", "/api/pipelines/", p)
    if r:
        pid = r.get("id")
        pipeline_ids.append(pid)
        print(f"OK ({pid[:8]}...)")
    else:
        print("FAILED")

# Expose the first pipeline as an API endpoint
if pipeline_ids:
    print(f"  Exposing Revenue by Category as API...", end=" ")
    r = api_p("POST", f"/api/pipelines/{pipeline_ids[0]}/expose", {"expose_as_api": True, "api_method": "GET"})
    if r: print(f"OK: {r.get('path','?')}")
    else: print("FAILED")

# ── 5. Verify ─────────────────────────────────────────
print("\n=== Verification ===")

# List models
print("  Models:", end=" ")
r = api_p("GET", "/api/models/")
if r: print(f"{len(r)} created")
else: print("FAILED")

# Count data
for coll in ["Category", "Product", "Customer", "Order", "OrderItem", "Cart", "CartItem", "Review"]:
    r = api_p("GET", f"/api/{coll}")
    if r and isinstance(r, list):
        print(f"  {coll}: {len(r)} records")

# Run aggregation pipeline
if pipeline_ids:
    print(f"\n  Running Revenue by Category pipeline:")
    r = api_p("POST", f"/api/pipelines/run/{pipeline_ids[0]}", {})
    if r and "results" in r:
        for res in r["results"]:
            print(f"    {res.get('_id','?')}: ${res.get('total_revenue',0):.2f} ({res.get('count',0)} orders)")

# Test the exposed pipeline endpoint
print(f"\n  Test exposed API (/api/aggregated/revenue-by-category):")
r = api_p("GET", "/api/aggregated/Revenue by Category")
if r and "results" in r:
    for res in r["results"]:
        print(f"    {res.get('_id','?')}: ${res.get('total_revenue',0):.2f}")

print("\n=== Done! ===")
print(f"Project ID: {PROJECT_ID}")
print(f"Customer ID: {customer_id}")
print(f"Products created: {len(product_ids)}")
