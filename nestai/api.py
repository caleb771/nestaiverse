from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os

# ─── CATALOG ──────────────────────────────────────────────────────────────────
CATALOG = {
    "bed_agape":   {"file": "bed_agape.gltf",   "category": "bed",        "style": ["modern", "minimal"], "dim": (1.8, 2.1, 0.5),  "clearance": 0.7, "wall": False, "cost": 900},
    "wardrobe":    {"file": "wardrobe.gltf",     "category": "storage",    "style": ["modern", "classic"], "dim": (1.8, 0.6, 2.1),  "clearance": 0.8, "wall": True,  "cost": 500},
    "shelf_wood":  {"file": "shelf_wood.gltf",   "category": "storage",    "style": ["modern", "classic"], "dim": (0.9, 0.35, 1.8), "clearance": 0.5, "wall": True,  "cost": 150},
    "wall_mirror": {"file": "wall_mirror.gltf",  "category": "wall_decor", "style": ["modern", "minimal"], "dim": (0.6, 0.05, 1.2), "clearance": 0.3, "wall": True,  "cost": 80},
    "wall_shelf":  {"file": "wall_shelf.gltf",   "category": "wall_decor", "style": ["modern", "minimal"], "dim": (0.8, 0.2, 0.15), "clearance": 0.2, "wall": True,  "cost": 60},
    "carpet":      {"file": "carpet.gltf",       "category": "floor_decor","style": ["modern", "classic"], "dim": (2.0, 3.0, 0.02), "clearance": 0.0, "wall": False, "cost": 200},
    "curtains":    {"file": "curtains.gltf",     "category": "window",     "style": ["modern", "classic"], "dim": (1.5, 0.1, 2.4),  "clearance": 0.1, "wall": True,  "cost": 120},
}

WALL_HEIGHTS = {
    "wall_mirror": 1.5,
    "wall_shelf":  1.6,
    "curtains":    1.2,
}

# ─── SPATIAL ENGINE ───────────────────────────────────────────────────────────
def compute_bounds(loc, dim):
    x, y = loc
    w, l = dim[0], dim[1]
    return {"min_x": x - w/2, "max_x": x + w/2, "min_y": y - l/2, "max_y": y + l/2}

def intersects(a, b, gap=0.05):
    return not (
        a["max_x"] + gap <= b["min_x"] or
        a["min_x"] >= b["max_x"] + gap or
        a["max_y"] + gap <= b["min_y"] or
        a["min_y"] >= b["max_y"] + gap
    )

def find_valid_position(obj_id, placed_objects, room, style):
    data = CATALOG[obj_id]
    w, l = data["dim"][0], data["dim"][1]
    half = room["w"] / 2 - 0.15
    step = 0.25

    if data["wall"]:
        for y_fixed in [-(half - l / 2), half - l / 2]:
            x = -half + w / 2
            while x <= half - w / 2 + 0.01:
                loc = (round(x, 2), round(y_fixed, 2))
                bounds = compute_bounds(loc, data["dim"])
                valid = all(not intersects(bounds, o["bounds"]) for o in placed_objects)
                if valid:
                    return loc, bounds
                x += step
    else:
        x = -half + w / 2
        while x <= half - w / 2 + 0.01:
            y = -half + l / 2
            while y <= half - l / 2 + 0.01:
                loc = (round(x, 2), round(y, 2))
                bounds = compute_bounds(loc, data["dim"])
                valid = all(not intersects(bounds, o["bounds"]) for o in placed_objects)
                if valid:
                    return loc, bounds
                y += step
            x += step

    return None, None

def choose_furniture(category, style):
    for key, item in CATALOG.items():
        if item["category"] == category and style in item.get("style", []):
            return key
    for key, item in CATALOG.items():
        if item["category"] == category:
            return key
    return None

def run_placement(room, style, categories):
    placed_objects = []
    results = []
    skipped = []

    for category in categories:
        obj_id = choose_furniture(category, style)
        if not obj_id:
            skipped.append({"category": category, "reason": "No matching furniture"})
            continue

        # Don't place the same item twice
        if any(o["id"] == obj_id for o in placed_objects):
            skipped.append({"category": category, "reason": f"{obj_id} already placed"})
            continue

        loc, bounds = find_valid_position(obj_id, placed_objects, room, style)
        if loc is None:
            skipped.append({"category": category, "reason": "No valid position found"})
            continue

        data = CATALOG[obj_id]

        # Compute z position
        if obj_id in WALL_HEIGHTS:
            z = WALL_HEIGHTS[obj_id] - data["dim"][2] / 2
        else:
            z = 0.0

        placed_objects.append({"id": obj_id, "location": loc, "bounds": bounds})
        results.append({
            "id":       obj_id,
            "category": data["category"],
            "file":     data["file"],
            "location": [loc[0], loc[1], z],
            "rotation": 0.0,
            "dim":      list(data["dim"]),
            "wall":     data["wall"],
            "cost":     data["cost"],
        })

    total_cost = sum(r["cost"] for r in results)
    floor_area = room["w"] * room["l"]
    used_area  = sum(r["dim"][0] * r["dim"][1] for r in results)

    return {
        "objects":    results,
        "skipped":    skipped,
        "total_cost": total_cost,
        "floor_used": round(used_area / floor_area * 100, 1),
        "room":       room,
        "style":      style,
    }

# ─── API ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="NestAIverse API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve GLTF assets statically so the frontend can load them
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# ─── MODELS ───────────────────────────────────────────────────────────────────
class RoomRequest(BaseModel):
    room:       dict               = {"w": 6, "l": 6, "h": 3}
    style:      str                = "modern"
    categories: List[str]         = ["bed", "storage", "floor_decor", "wall_decor", "window"]
    budget:     Optional[float]   = None

class CatalogItem(BaseModel):
    id:       str
    category: str
    style:    List[str]
    dim:      List[float]
    cost:     int
    wall:     bool

# ─── ROUTES ───────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "NestAIverse API running"}

@app.get("/catalog")
def get_catalog():
    return {
        key: {
            "id":       key,
            "category": val["category"],
            "style":    val["style"],
            "dim":      list(val["dim"]),
            "cost":     val["cost"],
            "wall":     val["wall"],
            "file":     val["file"],
        }
        for key, val in CATALOG.items()
    }

@app.post("/furnish")
def furnish(req: RoomRequest):
    result = run_placement(req.room, req.style, req.categories)

    # Apply budget filter if provided
    if req.budget:
        filtered = []
        running_cost = 0
        for obj in result["objects"]:
            if running_cost + obj["cost"] <= req.budget:
                filtered.append(obj)
                running_cost += obj["cost"]
            else:
                result["skipped"].append({
                    "category": obj["category"],
                    "reason":   f"Exceeds budget (cost: {obj['cost']})"
                })
        result["objects"]    = filtered
        result["total_cost"] = running_cost

    return result

@app.get("/room/presets")
def room_presets():
    return {
        "bedroom_small":  {"w": 4, "l": 4, "h": 2.7},
        "bedroom_medium": {"w": 6, "l": 6, "h": 3.0},
        "bedroom_large":  {"w": 8, "l": 8, "h": 3.2},
    }
