# Conveyor builder bot logic for Cambridge Battlecode 2026
# Team Mind of Metal and Wheels

import sys

from cambc import Controller, EntityType, Direction, Position

from bot_roles.builder_base import *
from bot_roles.BaseBuildingMixin import BaseBuildingMixin
from bot_roles.SaboteurMixin import SaboteurMixin

class ConveyorBot(BaseBuildingMixin, SaboteurMixin, BuilderBase):
  def __init__(self):
    super().__init__()
    self.mode = Modes.RETURN_TO_CORE
    self.harvesters = 0
    self.coreLocation = None
    self.possibleEnemyCorePositions: list[Position] = []
    self.follow = 0
    self.targetPos = None
    self.leeching = False
    self.moveScoring: dict[Direction, float] = {}
    self.newPosition = False

  def startup(self, ct: Controller):
    nearby_tiles = ct.get_nearby_tiles()
    for nearbyPos in nearby_tiles:
      nearbyBuilding = ct.get_tile_building_id(nearbyPos)
      if nearbyBuilding is None:
        continue
      nearbyEntity = ct.get_entity_type(nearbyBuilding)
      if nearbyEntity == EntityType.CORE:
        self.coreLocation = nearbyPos
        break

    self.possibleEnemyCorePositions = self.getPossibleEnemyPositions(ct)
    return

  def run(self, ct: Controller) -> None:
    print(self.mode)
    match self.mode:
      case Modes.CONVEYOR_LAYING:
        self.runConveyorLaying(ct)
      case Modes.FIND_NEW_CONVEYOR_BRANCH:
        self.runFindNewBranch(ct)
      case Modes.RETURN_TO_CORE:
        self.runReturnToCore(ct)
      case Modes.SABOTUER:
        self.runSaboteur(ct)
      case _:
        print("unknown state!", file= sys.stderr)

    self.adjustSentinels(ct)

  def getPossibleEnemyPositions(self, ct: Controller):
    possiblePositions: list[Position] = []
    width = ct.get_map_width()
    height = ct.get_map_height()

    x1 = -self.coreLocation.x + width - 1#type: ignore
    y1 = self.coreLocation.y#type: ignore

    x2 = self.coreLocation.x#type: ignore
    y2 = -self.coreLocation.y + height - 1#type: ignore

    x3 = -self.coreLocation.x + width - 1#type: ignore
    y3 = -self.coreLocation.y + height - 1#type: ignore

    possiblePositions.append(Position(x1, y1)) 
    possiblePositions.append(Position(x2, y2)) 
    possiblePositions.append(Position(x3, y3)) 
    return possiblePositions

  
