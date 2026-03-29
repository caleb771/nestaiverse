from Placement_engine import place
from World_state import world_state

# Place bedroom furniture
place("bed")
place("storage")
place("storage")
place("wall_decor")
place("wall_decor")
place("floor_decor")
place("window")

print("\n=== World State ===")
for obj in world_state["objects"]:
    print(f"  {obj['id']} → location {obj['location']}, bounds {obj['bounds']}")
