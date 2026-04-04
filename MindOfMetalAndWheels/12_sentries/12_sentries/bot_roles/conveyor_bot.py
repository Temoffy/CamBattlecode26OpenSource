# Conveyor builder bot logic for Cambridge Battlecode 2026
# Team Mind of Metal and Wheels

import random, sys, math
from enum import Enum

from cambc import Controller, EntityType, GameError, Direction, Environment, Position

from bot_roles.builder_base import BuilderBase
import pathfinding as pfind
from bot_roles.suicide_bot import SuicideBot

class Modes(Enum):
  CONVEYOR_LAYING = 0
  RETURN_TO_CORE = 1
  FIND_NEW_CONVEYOR_BRANCH = 2
  FIND_NEW_CONVEYOR_LINE = 3
  TURRET_LEECH = 4

class ConveyorBot(BuilderBase):
  def __init__(self):
    super().__init__()
    self.mode = Modes.RETURN_TO_CORE
    self.harvesters = 0
    self.coreLocation = None
    self.possibleEnemyCorePositions = []
    self.targetPos = None
    self.leeching = False

  def startup(self, ct: Controller):
    nearby_tiles = ct.get_nearby_tiles()
    for nearbyPos in nearby_tiles:
      nearbyBuilding = ct.get_tile_building_id(nearbyPos)
      nearbyEntity = ct.get_entity_type(nearbyBuilding)
      if nearbyPos is None or nearbyEntity == EntityType.CORE:
        self.coreLocation = nearbyPos
        self.justSpawned = False
        break

    self.possibleEnemyCorePositions = self.getPossibleEnemyPositions(ct)
    return

  def run(self, ct: Controller) -> None:
    match self.mode:
      case Modes.CONVEYOR_LAYING:
        self.runConveyorLaying(ct)
      case Modes.RETURN_TO_CORE:
        self.runReturnToCore(ct)
      case Modes.TURRET_LEECH:
        self.runTurretLeech(ct)
    
  def runConveyorLaying(self, ct: Controller) -> None:
    # make sure we can afford a harvester, and not just wander around spamming conveyors
    # random is to make sure bots run later during the turn don't get entirely excluded by earlier bots using up the Titanium
    if ct.get_global_resources()[0] < ct.get_harvester_cost()[0] * (1 + random.random() / 4):
      return

    if self.runTurretLeech(ct):
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

  def checkForEnemyCore(self, ct: Controller):
    nearby_tiles = ct.get_nearby_tiles()
    for potentialPos in self.possibleEnemyCorePositions:
      if potentialPos not in nearby_tiles:
        continue
      building = ct.get_tile_building_id(potentialPos)
      if(building != EntityType.CORE or ct.get_team()==ct.get_team(building)):
        self.possibleEnemyCorePositions.remove(potentialPos)
        return
      if( ct.get_entity_type(building)==EntityType.CORE and ct.get_team()!=ct.get_team(building)):
        self.possibleEnemyCorePositions = [potentialPos]
        return

  def tryBuildSentry(self, ct: Controller):
    i = 0
    xAve = 0
    yAve = 0
    for potPos in self.possibleEnemyCorePositions:
      xAve += potPos.x
      yAve += potPos.y
      i+=1
    xAve /= i
    yAve /= i
    aimingPos = Position(xAve,yAve)
    print(self.possibleEnemyCorePositions)
    print(aimingPos)

    #can we see both NO sentinals and at least ONE harvester
    nearbyBuildingIds = ct.get_nearby_buildings()
    seeSentry = False
    harvesters = []
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
    buildablePositions = []
    for dir in pfind.OCT_DIRECTIONS:
      testPos = myPos.add(dir)
      if not self.posIsInbounds(ct, testPos):
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
      for dir in [d for d in pfind.QUAD_DIRECTIONS if d != testPos.direction_to(aimingPos).opposite()]:
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
      if testDir in [None, Direction.CENTRE]:
        continue
      self.moveDir = testDir
      self.revDir = self.moveDir.opposite()
      targetDist = testDist

  def getPossibleEnemyPositions(self, ct: Controller):
    possiblePositions = []
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
  
  def runTurretLeech(self, ct: Controller):
    #can we see a harvester to leech?
    nearbyBuildingIds = ct.get_nearby_buildings()
    nearbyTiles = ct.get_nearby_tiles()
    enemyTiles = []
    myPos = ct.get_position()
    harvesters = []
    for buildingId in nearbyBuildingIds:
      if ct.get_team() == ct.get_team(buildingId):
        continue

      enemyTiles.append(ct.get_position(buildingId))

      if ct.get_entity_type(buildingId) == EntityType.SENTINEL:
        enemyTiles.append(ct.get_position(buildingId))
        enemyTiles.append(ct.get_position(buildingId))
        continue

      if ct.get_entity_type(buildingId) != EntityType.HARVESTER:
        continue
      buildingPos = ct.get_position(buildingId)
      if ct.get_tile_env(buildingPos) != Environment.ORE_TITANIUM:
        continue
      #is the harvester 1: unleeched, 2: neighboring the enemy?
      harvesterNoGood = True
      for dir in pfind.QUAD_DIRECTIONS:
        testPos = buildingPos.add(dir)
        if testPos not in nearbyTiles:
          #don't get stuck oscillating on the edge of seeing a sentry!
          harvesterNoGood = True
          break
        neighborBuildingId = ct.get_tile_building_id(testPos)
        if neighborBuildingId == None:
          continue
        if ct.get_entity_type(neighborBuildingId) == EntityType.SENTINEL and ct.get_team() == ct.get_team(neighborBuildingId):
          harvesterNoGood = True
          break
        if ct.get_team() != ct.get_team(neighborBuildingId):
          harvesterNoGood = False
          continue
      if harvesterNoGood:
        continue
      #can we build next to the harvester or can we destroy what's blocking us from so?
      harvesterNoGood = True
      for dir in pfind.QUAD_DIRECTIONS:
        testPos = buildingPos.add(dir)
        if ct.is_tile_passable(testPos) or ct.get_tile_building_id(testPos) == None:
          harvesterNoGood = False
          break
      if harvesterNoGood:
        continue

      harvesters.append(buildingPos)
      ct.draw_indicator_dot(buildingPos, 255, 0, 0)
    if len(harvesters) == 0 and not self.leeching:
      return False
    
    if len(harvesters) == 0 and self.leeching:
      return self.stopLeeching(ct)

    #pick nearest reachable harvester
    harvesters.sort(key=lambda pos: pfind.getChebyshevDistance(myPos, pos))
    harvToLeechPos = None
    for harvPos in harvesters:
      testDir = pfind.safeOctVisionBfsConsideratePath(myPos, harvPos, ct)
      if testDir != None:
        self.leeching = True
        self.targetPos = myPos

        harvToLeechPos = harvPos
        break

    if not harvToLeechPos and self.leeching:
      return self.stopLeeching(ct)
    if not harvToLeechPos:
      return False

    targetPos = None
    targetDir = None
    cantShootDir = None
    for dir in pfind.QUAD_DIRECTIONS:
      testPos = harvToLeechPos.add(dir)
      if ct.get_tile_building_id(testPos) == None:
        testDir = pfind.safeOctVisionBfsConsideratePath(myPos, testPos, ct)
        if testDir == None:
          continue
        targetPos = testPos
        targetDir = testDir
        cantShootDir = dir.opposite()
        break
    if targetPos == None:
      for dir in pfind.QUAD_DIRECTIONS:
        testPos = harvToLeechPos.add(dir)
        if ct.is_tile_passable(testPos):
          testDir = pfind.safeOctVisionBfsConsideratePath(myPos, testPos, ct)
          if testDir == None:
            continue
          targetPos = testPos
          targetDir = testDir
          cantShootDir = dir.opposite()
          break
    if targetPos == None:
      print("How did we get here????", file=sys.stderr)
      print("How did we get here????")
      return self.stopLeeching(ct)
    targetPos: Position

    #get best shooting direction
    i = 0
    xAve = 0
    yAve = 0
    for enemyPos in enemyTiles:
      xAve += enemyPos.x
      yAve += enemyPos.y
      i+=1
    for potPos in self.possibleEnemyCorePositions:
      xAve += potPos.x * 2
      yAve += potPos.y * 2
      i+=2
    xAve /= i
    yAve /= i
    aimingPos = Position(xAve,yAve)
    aimingDir = targetPos.direction_to(aimingPos)
    if aimingDir == cantShootDir:
      aimingDir = targetPos.direction_to(random.choice(enemyTiles))

    if ct.can_build_sentinel(targetPos, aimingDir):
      ct.build_sentinel(targetPos, aimingDir)
      return True
    if targetDir != Direction.CENTRE:
      ct.move(targetDir)
    if targetPos == ct.get_position() and ct.is_tile_passable(targetPos):
      ct.fire(targetPos)
      if ct.is_tile_passable(targetPos):
        return True
    for dir in pfind.OCT_DIRECTIONS:
      if ct.can_move(dir):
        ct.move(dir)
        if ct.can_build_sentinel(targetPos, aimingDir):
          ct.build_sentinel(targetPos, aimingDir)
        break
    return True

  def stopLeeching(self, ct: Controller):
    myPos = ct.get_position()
    if myPos == self.targetPos:
      #back on my territory
      self.leeching = False
      self.targetPos = None
      return False
    elif self.targetPos != None:
      dir = pfind.safeOctVisionBfsConsideratePath(myPos, self.targetPos, ct)
      if dir == None:
        dirs = pfind.OCT_DIRECTIONS
        random.shuffle(dirs)
        for dir in dirs:
          if ct.can_move(dir):
            ct.move(dir)
            break
      if ct.can_move(dir):
        ct.move(dir)
      return True
    else:
      print("No Home!! ")
      print("No Home!!",ct.get_current_round(), file=sys.stderr)
      ct.draw_indicator_dot(myPos, 0,255,255)
