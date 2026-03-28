from nestai.placement_engine import place
from nestai.world_state import world_state

# Decide what room needs
place("seating")
place("surface")

print("World State:", world_state)
