from cambc import Controller, EntityType, Position
from tools import *
from collections import deque
import pathfinding as pfind

def scoreQuadNocrossReachableTiles(sourcePos: Position, ct: Controller, forbiddenPosList: list[Position] = []) -> float:
  queue: deque[ Position ] = deque()
  queue.append(sourcePos)
  visited: set[ tuple[int, int] ] = set()
  visited.add((sourcePos.x, sourcePos.y))

  forbid = set((p.x, p.y) for p in forbiddenPosList)

  visibleTile = ct.get_nearby_tiles()
  visible = set((t.x,t.y) for t in visibleTile)

  multi = 1
  score = 0
  dropoff = 0.95

  while queue:
    pos = queue.popleft()

    for dir in QUAD_DIRECTIONS:
      nextPos = pos.add(dir)
      key = (nextPos.x, nextPos.y)

      if key in visited:
        continue
      if key in forbid:
        continue
      if key not in visible:
        score += 3*multi/pfind.getChebyshevDistance(sourcePos, nextPos)
        multi *= dropoff
        continue
      if not (ct.is_tile_passable(nextPos) or ct.is_tile_empty(nextPos)):
        visited.add(key)
        continue
      buildingId = ct.get_tile_building_id(nextPos)
      if buildingId != None:
        if ct.get_team() != ct.get_team(buildingId):
          #TODO: remove this after we add combat code to fight through enemy buildings?
          visited.add(key)
          continue
        elif ct.get_entity_type(buildingId) is not EntityType.ROAD:
          score -= 1*multi/pfind.getChebyshevDistance(sourcePos, nextPos)
          visited.add(key)
          continue
      score += 1*multi/pfind.getChebyshevDistance(sourcePos, nextPos)
      multi *= dropoff
      visited.add(key)
      queue.append(nextPos)

  return score


def getQuadNocrossReachableTiles(sourcePos: Position, ct: Controller, forbiddenPosList: list[Position] = []) -> list[Position]:
  queue: deque[ Position ] = deque()
  queue.append(sourcePos)
  visited: set[ tuple[int, int] ] = set()
  visited.add((sourcePos.x, sourcePos.y))

  reachable: list[Position] = []

  forbid = set((p.x, p.y) for p in forbiddenPosList)

  visibleTile = ct.get_nearby_tiles()
  visible = set((t.x,t.y) for t in visibleTile)

  while queue:
    pos = queue.popleft()

    for dir in QUAD_DIRECTIONS:
      nextPos = pos.add(dir)
      key = (nextPos.x, nextPos.y)

      if key in visited:
        continue
      if key in forbid:
        continue
      if key not in visible:
        continue
      if not (ct.is_tile_passable(nextPos) or ct.is_tile_empty(nextPos)):
        visited.add(key)
        continue
      buildingId = ct.get_tile_building_id(nextPos)
      if buildingId != None:
        if ct.get_team() != ct.get_team(buildingId):
          #TODO: remove this after we add combat code to fight through enemy buildings?
          visited.add(key)
          continue
        elif ct.get_entity_type(buildingId) is not EntityType.ROAD:
          visited.add(key)
          continue

      visited.add(key)
      queue.append(nextPos)
      reachable.append(nextPos)

  return reachable
