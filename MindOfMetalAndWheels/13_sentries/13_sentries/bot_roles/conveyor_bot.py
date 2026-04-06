# Conveyor builder bot logic for Cambridge Battlecode 2026
# Team Mind of Metal and Wheels

import random, sys, math

from cambc import Controller, EntityType, Direction, Environment, Position

from bot_roles.builder_base import *
from bot_roles.BaseBuildingMixin import BaseBuildingMixin
from bot_roles.SaboteurMixin import SaboteurMixin
import pathfinding as pfind

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
    match self.mode:
      case Modes.CONVEYOR_LAYING:
        self.runConveyorLaying(ct)
      case Modes.RETURN_TO_CORE:
        self.runReturnToCore(ct)
      case Modes.SABOTUER:
        self.runSaboteur(ct)
      case _:
        print("unknown state!", file= sys.stderr)

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

  def runReturnToCore(self, ct: Controller):
    mypos = ct.get_position()
    entityUnderId = ct.get_tile_building_id(mypos)
    entityUnderType = ct.get_entity_type(entityUnderId)
    if entityUnderId is not None and ct.get_team() == ct.get_team(entityUnderId):
      if entityUnderType == EntityType.CONVEYOR:
        self.moveDir = ct.get_direction(entityUnderId)
        self.revDir = self.moveDir
      elif entityUnderType == EntityType.CORE:
        self.harvesters = 0
        self.moveDir = self.getNewConveyorLineDir(ct)
        self.revDir = self.moveDir.opposite()
    if(self.moveDir == Direction.CENTRE):
      return
    travelPos = mypos.add(self.moveDir)
    if not posIsInbounds(ct, travelPos):
      self.moveDir = random.choice([Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST])
      return
    entityInDirId = ct.get_tile_building_id(travelPos)
    if ct.get_entity_type(entityInDirId) == EntityType.ROAD and ct.get_team() == ct.get_team(entityInDirId):
      ct.destroy(travelPos)
    if ct.can_build_conveyor(travelPos, self.revDir):
      ct.build_conveyor(travelPos, self.revDir)
      #step out of the core onto a new path
      if self.harvesters == 0:
        self.mode = Modes.CONVEYOR_LAYING
    if ct.is_tile_passable(travelPos):
      ct.move(self.moveDir)

  def getNewConveyorLineDir(self, ct: Controller):
    QuadDirections = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
    random.shuffle(QuadDirections)
    coreDir = Direction.CENTRE
    pos = ct.get_position()
    for dir in QuadDirections:
      testPos = pos.add(dir)
      if not posIsInbounds(ct, testPos):
        continue
      testBuilding = ct.get_tile_building_id(testPos)
      #TODO replace random.random when we have a way to 'adopt' an existing conveyor.
      if (ct.is_tile_empty(testPos) and testBuilding is None) or random.random() < 0.5:
        return dir
      if ct.is_tile_passable(testPos) and ct.get_entity_type(testBuilding) == EntityType.CORE:
        coreDir = dir
    return coreDir
