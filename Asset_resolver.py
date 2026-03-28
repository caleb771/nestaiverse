from .furniture_catalog import FURNITURE_CATALOG

def choose_furniture(category, style):

    for key, item in FURNITURE_CATALOG.items():
        if item["category"] == category and style in item["style"]:
            return key

    return None
