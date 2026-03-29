def intersects(a, b):

    return not (
        a["max_x"] < b["min_x"] or
        a["min_x"] > b["max_x"] or
        a["max_y"] < b["min_y"] or
        a["min_y"] > b["max_y"]
    )


def compute_bounds(location, dimensions):

    x, y, _ = location
    w, l, _ = dimensions

    return {
        "min_x": x - w/2,
        "max_x": x + w/2,
        "min_y": y - l/2,
        "max_y": y + l/2
    }
