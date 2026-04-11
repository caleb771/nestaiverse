from World_state import world_state
from furniture_catalog import FURNITURE_CATALOG
from Asset_resolver import choose_furniture
from Spatial import compute_bounds, intersects

def find_valid_position(data):
    for x in range(-2, 3):
        for y in range(-2, 3):
            loc = (x, y, 0)
            bounds = compute_bounds(loc, data["dimensions"])
            valid = True
            for obj in world_state["objects"]:
                if intersects(bounds, obj["bounds"]):
                    valid = False
                    break
            if valid:
                return loc
    return (0, 0, 0)

def place(category):
    obj_id = choose_furniture(category, world_state["style"])
    if obj_id is None:
        print(f"Warning: No furniture found for category '{category}'")
        return None
    data = FURNITURE_CATALOG[obj_id]
    location = find_valid_position(data)
    bounds = compute_bounds(location, data["dimensions"])
    obj = {
        "id": obj_id,
        "location": location,
        "bounds": bounds
    }
    world_state["objects"].append(obj)
    return obj

