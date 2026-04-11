from furniture_catalog import FURNITURE_CATALOG

def choose_furniture(category, style):
    for key, item in FURNITURE_CATALOG.items():
        if item["category"] == category and style in item.get("style", []):
            return key
    # Fallback: match category only, ignore style
    for key, item in FURNITURE_CATALOG.items():
        if item["category"] == category:
            return key
    return None
