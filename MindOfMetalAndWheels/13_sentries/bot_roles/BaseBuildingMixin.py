#state code for conveyor_bot
# Team Mind of Metal and Wheels
# Author: Multiple, March 2026. Α⳩ω
from cambc import Direction, Position, EntityType, Environment, GameError
import math
from bot_roles.builder_base import *
from tools import *
import pathfinding as pfind

class BaseBuildingMixin (BuilderBase):
  #all varibles here should be declared in the conveyor_bot init function!
  mode: Modes
  harvesters: int
  coreLocation: Position | None
  possibleEnemyCorePositions: list[Position]
  targetPos: Position | None
  leeching: bool

  def runConveyorLaying(self, ct: Controller) -> None:

    # make sure we can afford a harvester, and not just wander around spamming conveyors
    # random is to make sure bots run later during the turn don't get entirely excluded by earlier bots using up the Titanium
    if ct.get_global_resources()[0] < ct.get_harvester_cost()[0] * (1 + random.random() / 4):
      return

    self.checkForEnemyCore(ct)

    if self.tryBuildAdjacentHarvester(ct):
      self.harvesters += 1
      # just made a harvester, can't make a conveyor to move onto
      return

    #not in the above if statement to let tryBuildSentry run.
    if self.harvesters >= 4:
      self.mode = Modes.RETURN_TO_CORE

    if self.tryBuildSentry(ct):
      return

    self.aquireHarvester(ct)

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
      elif posIsInbounds(ct, movePos) and ct.get_entity_type(ct.get_tile_building_id(movePos)) == EntityType.ROAD and ct.get_team(ct.get_tile_building_id(movePos)) == ct.get_team():
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
        leftCheck = posIsInbounds(ct, leftPos) and ct.is_tile_empty(leftPos) and not ct.is_tile_passable(leftPos)
        rightCheck = posIsInbounds(ct, rightPos) and ct.is_tile_empty(rightPos) and not ct.is_tile_passable(rightPos)
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

    nearbyBuildingIds = ct.get_nearby_buildings()
    for id in nearbyBuildingIds:
      if ct.get_team() == ct.get_team(id):
        continue
      if ct.get_entity_type(id) == EntityType.HARVESTER:
        continue
      if random.random() < 0.01:
        self.mode = Modes.SABOTUER

  def tryBuildSentry(self, ct: Controller):
    i = 0
    xAve: float = 0
    yAve: float = 0
    for potPos in self.possibleEnemyCorePositions:
      xAve += potPos.x
      yAve += potPos.y
      i+=1
    xAve /= i
    yAve /= i
    aimingPos = Position( math.floor(xAve),math.floor(yAve) )
    print(self.possibleEnemyCorePositions)
    print(aimingPos)

    #can we see both NO sentinals and at least ONE harvester
    nearbyBuildingIds = ct.get_nearby_buildings()
    seeSentry = False
    harvesters: list[int] = []
    for buildingId in nearbyBuildingIds:
      if ct.get_entity_type(buildingId) == EntityType.SENTINEL and ct.get_team() == ct.get_team(buildingId):
        seeSentry = True
      elif ct.get_entity_type(buildingId) == EntityType.HARVESTER:
        harvesters.append(buildingId)
    print("hey2",seeSentry, harvesters)
    if len(harvesters) == 0 or seeSentry:
      print("exit 1")
      return False
    #get all possible places we can build right now
    myPos = ct.get_position()
    buildablePositions: list[Position] = []
    for dir in OCT_DIRECTIONS:
      testPos = myPos.add(dir)
      if not posIsInbounds(ct, testPos):
        continue
      if ct.get_tile_env(testPos) != Environment.EMPTY or not ct.can_build_sentinel(testPos, testPos.direction_to(aimingPos)):
        continue
      buildablePositions.append(testPos)

    if len(buildablePositions) == 0:
      return False
    print("hey3")
    #see if any of those positions are also next to a harvester
    for harvId in harvesters:
      harvPos = ct.get_position(harvId)
      if ct.get_tile_env(harvPos) != Environment.ORE_TITANIUM:
        continue
      for dir in [d for d in QUAD_DIRECTIONS if d != harvPos.direction_to(aimingPos).opposite()]:
        testPos = harvPos.add(dir)
        if testPos in buildablePositions:
          print("hey4", testPos)
          ct.build_sentinel(testPos, testPos.direction_to(aimingPos))
          return True
  
  def aquireHarvester(self, ct: Controller):
    myPos = ct.get_position()
    #home in on un-harvestered ores
    targetDist = 99
    for nearTile in ct.get_nearby_tiles():
      if ct.get_tile_env(nearTile) not in [Environment.ORE_AXIONITE, Environment.ORE_TITANIUM]:
        continue
      if(ct.get_tile_building_id(nearTile) != None):
        continue
      testDist = pfind.getManhattanDistance(myPos, nearTile)
      if testDist >= targetDist:
        continue
      
      testDir = pfind.safeQuadVisionBfsNocrossPath(myPos, nearTile, ct)
      if testDir is None or testDir is Direction.CENTRE:
        continue
      self.moveDir = testDir
      self.revDir = self.moveDir.opposite()
      targetDist = testDist