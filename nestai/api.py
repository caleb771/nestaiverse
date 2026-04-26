from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
import json

# ─── LOAD MOCK CATALOG ────────────────────────────────────────────────────────
CATALOG_PATH = os.path.join(os.path.dirname(__file__), "mock_catalog.json")
with open(CATALOG_PATH) as f:
    RETAILER_DATA = json.load(f)

PRODUCTS = RETAILER_DATA["products"]

WALL_HEIGHTS = {
    "wall_decor": 1.5,
    "window":     1.2,
}

# ─── SPATIAL ENGINE ───────────────────────────────────────────────────────────
def compute_bounds(loc, dim):
    x, y = loc
    w, l = dim["w"], dim["l"]
    return {"min_x": x - w/2, "max_x": x + w/2,
            "min_y": y - l/2, "max_y": y + l/2}

def intersects(a, b, gap=0.05):
    return not (
        a["max_x"] + gap <= b["min_x"] or
        a["min_x"] >= b["max_x"] + gap or
        a["max_y"] + gap <= b["min_y"] or
        a["min_y"] >= b["max_y"] + gap
    )

def find_valid_position(product, placed_objects, room):
    w = product["dimensions"]["w"]
    l = product["dimensions"]["l"]
    half = room["w"] / 2 - 0.15
    step = 0.25

    if product["wall"]:
        for y_fixed in [-(half - l / 2), half - l / 2]:
            x = -half + w / 2
            while x <= half - w / 2 + 0.01:
                loc = (round(x, 2), round(y_fixed, 2))
                bounds = compute_bounds(loc, product["dimensions"])
                if all(not intersects(bounds, o["bounds"]) for o in placed_objects):
                    return loc, bounds
                x += step
    else:
        x = -half + w / 2
        while x <= half - w / 2 + 0.01:
            y = -half + l / 2
            while y <= half - l / 2 + 0.01:
                loc = (round(x, 2), round(y, 2))
                bounds = compute_bounds(loc, product["dimensions"])
                if all(not intersects(bounds, o["bounds"]) for o in placed_objects):
                    return loc, bounds
                y += step
            x += step

    return None, None

def choose_product(category, style, max_price, placed_skus):
    # Filter by category, style, budget, stock, not already placed
    candidates = [
        p for p in PRODUCTS
        if p["category"] == category
        and style in p["style"]
        and p["price"] <= max_price
        and p["in_stock"]
        and p["sku"] not in placed_skus
    ]
    if not candidates:
        # Relax style constraint
        candidates = [
            p for p in PRODUCTS
            if p["category"] == category
            and p["price"] <= max_price
            and p["in_stock"]
            and p["sku"] not in placed_skus
        ]
    if not candidates:
        return None
    # Pick highest rated
    return max(candidates, key=lambda p: p["rating"])

def run_placement(room, style, categories, budget):
    placed_objects = []
    results        = []
    skipped        = []
    placed_skus    = set()

    # Distribute budget evenly as a per-item max
    per_item_budget = (budget / len(categories)) * 1.5 if budget else float("inf")

    for category in categories:
        max_price = per_item_budget if budget else float("inf")
        product   = choose_product(category, style, max_price, placed_skus)

        if not product:
            skipped.append({"category": category, "reason": "No matching product in catalog"})
            continue

        loc, bounds = find_valid_position(product, placed_objects, room)
        if loc is None:
            skipped.append({"category": category, "reason": "No valid position found"})
            continue

        dim = product["dimensions"]
        z   = WALL_HEIGHTS.get(product["category"], 0.0)
        if z > 0:
            z = z - dim["h"] / 2

        placed_skus.add(product["sku"])
        placed_objects.append({"id": product["sku"], "bounds": bounds})

        results.append({
            "id":          product["sku"],
            "name":        product["name"],
            "category":    product["category"],
            "file":        product["asset_file"],
            "location":    [loc[0], loc[1], z],
            "rotation":    0.0,
            "dim":         [dim["w"], dim["l"], dim["h"]],
            "wall":        product["wall"],
            "price":       product["price"],
            "image_url":   product["image_url"],
            "product_url": product["product_url"],
            "rating":      product["rating"],
            "reviews":     product["reviews"],
        })

    total_cost = sum(r["price"] for r in results)
    floor_area = room["w"] * room["l"]
    used_area  = sum(r["dim"][0] * r["dim"][1] for r in results)

    return {
        "retailer":   RETAILER_DATA["retailer"],
        "currency":   RETAILER_DATA["currency"],
        "objects":    results,
        "skipped":    skipped,
        "total_cost": total_cost,
        "budget":     budget,
        "floor_used": round(used_area / floor_area * 100, 1),
        "room":       room,
        "style":      style,
    }

# ─── APP ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="NestAIverse API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ASSETS_DIR = r"C:\Users\USER PC\Documents\nestaiverse\assets"
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# ─── MODELS ───────────────────────────────────────────────────────────────────
class RoomRequest(BaseModel):
    room:       dict          = {"w": 6, "l": 6, "h": 3}
    style:      str           = "modern"
    categories: List[str]     = ["bed", "storage", "floor_decor", "wall_decor", "window"]
    budget:     Optional[float] = None

class CartRequest(BaseModel):
    skus:       List[str]
    session_id: Optional[str] = None

# ─── ROUTES ───────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status":   "ok",
        "version":  "0.2.0",
        "retailer": RETAILER_DATA["retailer"]
    }

@app.get("/catalog")
def get_catalog(
    category: Optional[str] = Query(None),
    style:     Optional[str] = Query(None),
    max_price: Optional[float] = Query(None),
    in_stock:  bool = Query(True)
):
    products = PRODUCTS
    if category:
        products = [p for p in products if p["category"] == category]
    if style:
        products = [p for p in products if style in p["style"]]
    if max_price:
        products = [p for p in products if p["price"] <= max_price]
    if in_stock:
        products = [p for p in products if p["in_stock"]]
    return {
        "retailer": RETAILER_DATA["retailer"],
        "currency": RETAILER_DATA["currency"],
        "count":    len(products),
        "products": products
    }

@app.post("/furnish")
def furnish(req: RoomRequest):
    return run_placement(req.room, req.style, req.categories, req.budget)

@app.post("/cart/prepare")
def prepare_cart(req: CartRequest):
    """Returns product details for all SKUs — retailer uses this to build the cart"""
    items = []
    for sku in req.skus:
        product = next((p for p in PRODUCTS if p["sku"] == sku), None)
        if product:
            items.append({
                "sku":         product["sku"],
                "name":        product["name"],
                "price":       product["price"],
                "product_url": product["product_url"],
                "image_url":   product["image_url"],
            })
    return {
        "retailer":    RETAILER_DATA["retailer"],
        "currency":    RETAILER_DATA["currency"],
        "items":       items,
        "total":       sum(i["price"] for i in items),
        "checkout_url": "https://furniturepalace.co.ke/checkout"
    }

@app.get("/room/presets")
def room_presets():
    return {
        "bedsitter":      {"w": 4,  "l": 4,  "h": 2.7},
        "bedroom_small":  {"w": 4,  "l": 5,  "h": 2.7},
        "bedroom_medium": {"w": 6,  "l": 6,  "h": 3.0},
        "bedroom_large":  {"w": 8,  "l": 8,  "h": 3.2},
        "studio":         {"w": 10, "l": 8,  "h": 3.0},
    }

@app.get("/debug")
def debug():
    return {
        "assets_dir": ASSETS_DIR,
        "exists":     os.path.exists(ASSETS_DIR),
        "products":   len(PRODUCTS),
        "retailer":   RETAILER_DATA["retailer"]
    }
