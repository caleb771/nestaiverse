import bpy
import os
from .furniture_catalog import FURNITURE_CATALOG

ASSET_DIR = os.path.abspath("assets")


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def create_room():
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,1.5))
    room = bpy.context.object
    room.scale = (3,3,1.5)


def import_asset(asset_name, location):

    path = os.path.join(ASSET_DIR, asset_name)

    bpy.ops.import_scene.gltf(filepath=path)

    for obj in bpy.context.selected_objects:
        obj.location = location


def render_world(world_state):

    clear_scene()
    create_room()

    for obj in world_state["objects"]:
        asset = FURNITURE_CATALOG[obj["id"]]["asset"]
        import_asset(asset, obj["location"])
