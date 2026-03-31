# Conveyor builder bot logic for Cambridge Battlecode 2026
# Team Mind of Metal and Wheels

import random, sys
from enum import Enum

from cambc import Controller, EntityType, GameError, Direction

from bot_roles.builder_base import BuilderBase
import pathfinding as pfind
from bot_roles.suicide_bot import SuicideBot

class Modes(Enum):
  CONVEYOR_LAYING = 0
  RETURN_TO_CORE = 1
  FIND_NEW_CONVEYOR_BRANCH = 2
  FIND_NEW_CONVEYOR_LINE = 3

class ConveyorBot(BuilderBase):
  def __init__(self):
    super().__init__()
    self.mode = Modes.RETURN_TO_CORE
    self.harvesters = 0

  def run(self, ct: Controller) -> None:
    match self.mode:
      case Modes.CONVEYOR_LAYING:
        self.runConveyorLaying(ct)
      case Modes.RETURN_TO_CORE:
        self.runReturnToCore(ct)
    
  def runConveyorLaying(self, ct: Controller) -> None:
    # make sure we can afford a harvester, and not just wander around spamming conveyors
    # random is to make sure bots run later during the turn don't get entirely excluded by earlier bots using up the Titanium
    if ct.get_global_resources()[0] < ct.get_harvester_cost()[0] * (1 + random.random() / 4):
      return

    if self.tryBuildAdjacentHarvester(ct):
      self.harvesters += 1
      if self.harvesters >= 4:
        self.mode = Modes.RETURN_TO_CORE
      # just made a harvester, can't make a conveyor to move onto
      return

    # move logic
    i = 0
    while True:
      builtForward = False
      movePos = ct.get_position().add(self.moveDir)

      # Move away from enemy territory
      if self.isEnemyAt(ct, movePos):
        self.changeMoveDir()
        continue

      if ct.can_build_conveyor(movePos, self.revDir):
        ct.build_conveyor(movePos, self.revDir)

        sideDir = self.moveDir.rotate_right().rotate_right()
        sidePos = movePos.add(sideDir)

        if ct.can_build_conveyor(sidePos, self.revDir) and self.doublePlaced < 8:
          ct.build_conveyor(sidePos, self.revDir)
          self.doublePlaced += 1
          builtForward = True
      elif self.posIsInbounds(ct, movePos) and ct.get_entity_type(ct.get_tile_building_id(movePos)) == EntityType.ROAD and ct.get_team(ct.get_tile_building_id(movePos)) == ct.get_team():
        ct.destroy(movePos)
        try: 
          ct.build_conveyor(movePos, self.revDir)
        except GameError:
          print("Failed to build conveyor after destroying road, skipping turn")
      elif ct.can_move(self.moveDir):
        # THIS IS BROKEN AND NEEDS MORE TESTING
        # can't build but can move means we are conveyor following
        leftPos = ct.get_position().add(self.moveDir.rotate_left().rotate_left())
        rightPos = ct.get_position().add(self.moveDir.rotate_right().rotate_right())
        leftCheck = self.posIsInbounds(ct, leftPos) and ct.is_tile_empty(leftPos) and not ct.is_tile_passable(leftPos)
        rightCheck = self.posIsInbounds(ct, rightPos) and ct.is_tile_empty(rightPos) and not ct.is_tile_passable(rightPos)
        if (leftCheck or rightCheck) and random.random() < 0.9:
          # this can get caught in an infinite loop and I'm not sure why.
          # so I threw a random chance on this to break out.
          self.changeMoveDir()
          continue
        if random.random() < 0.1:
          self.changeMoveDir()
          continue

      if ct.can_move(self.moveDir):
        ct.move(self.moveDir)
        if builtForward and self.doublePlaced < 8:
          self.placeSideNext = True
        break
      self.changeMoveDir()
      if i > 5:
        return
      i += 1
  def runReturnToCore(self, ct: Controller):
    mypos = ct.get_position()
    entityUnderId = ct.get_tile_building_id(mypos)
    entityUnderType = ct.get_entity_type(entityUnderId)
    if entityUnderType is not None and ct.get_team() == ct.get_team(entityUnderId):
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
    if not self.posIsInbounds(ct, travelPos):
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
      if not self.posIsInbounds(ct, testPos):
        continue
      testBuilding = ct.get_tile_building_id(testPos)
      #TODO replace random.random when we have a way to 'adopt' an existing conveyor.
      if (ct.is_tile_empty(testPos) and testBuilding is None) or random.random() < 0.5:
        return dir
      if ct.is_tile_passable(testPos) and ct.get_entity_type(testBuilding) == EntityType.CORE:
        coreDir = dir
    return coreDir