from cambc import Direction, Controller, Position

# Direction lists to reference later
OCT_DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
QUAD_DIRECTIONS = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]

# Makes sure a position is in the bounds of the map
def posIsInbounds( ct: Controller, pos: Position) -> bool:
  if pos.x < 0 or pos.y < 0 or pos.x >= ct.get_map_width() or pos.y >= ct.get_map_height():
    return False
  return True