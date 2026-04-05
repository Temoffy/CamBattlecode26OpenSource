# Shared builder-bot helpers for Cambridge Battlecode 2026
# Team Mind of Metal and Wheels

import random, enum

from cambc import Controller, Direction, EntityType, Position
from tools import *

class Modes(enum.Enum):
  CONVEYOR_LAYING = 0
  RETURN_TO_CORE = 1
  FIND_NEW_CONVEYOR_BRANCH = 2
  FIND_NEW_CONVEYOR_LINE = 3
  SABOTUER = 4

class BuilderBase:
  possibleEnemyCorePositions: list[Position]

  def __init__(self):
    # direction to move in - conveyors (and the opposite-direction logic below) assume cardinal moves
    self.moveDir: Direction = random.choice(QUAD_DIRECTIONS)
    self.revDir: Direction = Direction.opposite(self.moveDir) # direction opposite to moveDir, used for building conveyors
    self.doublePlaced: int = 0

  def startup(self, ct: Controller):
    #nothin
    return

  def checkForEnemyCore(self, ct: Controller):
    nearby_tiles = ct.get_nearby_tiles()
    for potentialPos in self.possibleEnemyCorePositions:
      if potentialPos not in nearby_tiles:
        continue
      building = ct.get_tile_building_id(potentialPos)
      if(ct.get_entity_type(building) != EntityType.CORE or ct.get_team()==ct.get_team(building)):
        self.possibleEnemyCorePositions.remove(potentialPos)
        return
      if( ct.get_entity_type(building)==EntityType.CORE and ct.get_team()!=ct.get_team(building)):
        self.possibleEnemyCorePositions = [potentialPos]
        return

  def isEnemyAt(self, ct: Controller, pos: Position) -> bool:
    # Avoid calling tile queries out-of-bounds.
    inBounds = posIsInbounds(ct, pos)
    if not inBounds:
      return False

    # Enemy builder bot?
    botId = ct.get_tile_builder_bot_id(pos)
    if botId is not None and ct.get_team(botId) != ct.get_team():
      return True

    # Enemy building?
    buildingId = ct.get_tile_building_id(pos)
    if buildingId is not None and ct.get_team(buildingId) != ct.get_team() and ct.get_entity_type(buildingId) != EntityType.MARKER:
      return True

    return False

  def changeMoveDir(self):
    # exclude the current direction and turning back.
    possibleDirections = [d for d in QUAD_DIRECTIONS if d != self.moveDir and d != self.revDir]
    self.moveDir = random.choice(possibleDirections)
    self.revDir = Direction.opposite(self.moveDir)

  def tryBuildAdjacentHarvester(self, ct: Controller) -> bool:
    for d in QUAD_DIRECTIONS:
      checkPos = ct.get_position().add(d)
      if ct.can_build_harvester(checkPos):
        ct.build_harvester(checkPos)
        return True
    return False

