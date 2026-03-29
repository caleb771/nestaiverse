import bpy
import os
from furniture_catalog import FURNITURE_CATALOG


# Project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_PATH = os.path.join(BASE_DIR, "assets")


# -------------------------
# Scene Setup
# -------------------------

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def create_room():
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1.5))
    room = bpy.context.object
    room.scale = (3, 3, 1.5)
    room.name = "Room"


# -------------------------
# Asset Import
# -------------------------

def import_asset(asset_name, location):
    filepath = os.path.join(ASSET_PATH, asset_name)
    print("Loading asset:", filepath)
    bpy.ops.import_scene.gltf(filepath=filepath)
    for obj in bpy.context.selected_objects:
        if obj.parent is None:
            obj.location = location


# -------------------------
# Render Pipeline
# -------------------------

def render_world(world_state):

    clear_scene()
    create_room()

    for obj in world_state["objects"]:
        asset = FURNITURE_CATALOG[obj["id"]]["asset"]
        import_asset(asset, obj["location"])

    bpy.context.scene.render.filepath = os.path.join(BASE_DIR, "render.png")
    bpy.ops.render.render(write_still=True)
