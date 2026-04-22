# State code for conveyor_bot
# Team Mind of Metal and Wheels
# Author: Multiple, March 2026. Α⳩ω

from cambc import Direction, Position, EntityType, Environment
import math, sys, random
from bot_roles.builder_base import *
from tools import *
import pathfinding as pfind
import sensing

ABORT_CONVEYOR = 2

class BaseBuildingMixin (BuilderBase):
  # All varibles here should be declared in the conveyor_bot init function
  mode: Modes
  harvesters: int
  coreLocation: Position | None
  possibleEnemyCorePositions: list[Position]
  targetPos: Position | None
  leeching: bool

  moveScoring: dict[Direction, float]

  def runConveyorLaying(self, ct: Controller) -> None:
    myPos = ct.get_position()
    # Make sure we can afford a harvester, and not just wander around spamming conveyors
    # Random is to make sure bots which run later during the turn don't get entirely excluded by earlier bots using up the Titanium
    if ct.get_global_resources()[0] < ct.get_sentinel_cost()[0]:
      return
    
    self.checkForEnemyCore(ct)

    if self.__tryBuildSentry(ct):
      return

    if self.harvesters >= 4:
      self.mode = Modes.RETURN_TO_CORE
      return

    if self.__aquireHarvester(ct):
      return
    
    # make sure we can afford a harvester, and not just wander around spamming conveyors
    # random is to make sure bots run later during the turn don't get entirely excluded by earlier bots using up the Titanium
    if ct.get_global_resources()[0] < ct.get_sentinel_cost()[0] * (1 + random.random() / 4):
      return
    
    self.__sabateurModeCheck(ct)

    # trace existing conveyor line
    for dir in QUAD_DIRECTIONS:
      tile = myPos.add(dir)
      if not posIsInbounds(ct, tile):
        continue
      building = ct.get_tile_building_id(tile)
      if building == None:
        continue
      if ct.get_team() != ct.get_team(building):
        continue
      type = ct.get_entity_type(building)
      if type in [EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR]:
        if tile.add(ct.get_direction(building)) == myPos:
          if ct.can_move(dir):
            print("follow conveyor move")
            ct.move(dir)
            return

    #build possible directions
    possibleMoves: list[tuple[Direction, Position]] = []
    for dir in QUAD_DIRECTIONS:
      tile = myPos.add(dir)
      if not posIsInbounds(ct, tile):
        continue
      if ct.get_tile_env(tile) != Environment.EMPTY:
        continue
      building = ct.get_tile_building_id(tile)
      if building != None:
        if ct.get_team() != ct.get_team(building):
          continue
        if ct.get_entity_type(building) != EntityType.ROAD:
          continue
      possibleMoves.append((dir, tile))

    if len(possibleMoves) == 0:
      self.mode = Modes.FIND_NEW_CONVEYOR_BRANCH
      return

    forbidList = list(map(lambda x: x[1], possibleMoves))
    forbidList.append(myPos)
    for dir, pos in possibleMoves:
      if dir in self.moveScoring:
        continue
      score = sensing.scoreQuadNocrossReachableTiles(pos, ct, forbiddenPosList=forbidList)
      print("dir:",dir,"score:",score)
      self.moveScoring[dir] = score

    bestDir = possibleMoves[0][0]
    bestScore = -1 * math.inf
    for dir in self.moveScoring:
      if self.moveScoring[dir] > bestScore:
        bestScore = self.moveScoring[dir]
        bestDir = dir
    
    if bestScore < ABORT_CONVEYOR:
      self.mode = Modes.FIND_NEW_CONVEYOR_BRANCH
      return

    self.__conveyMove(bestDir, bestDir.opposite(), ct)

    self.moveScoring = {}

  def __sabateurModeCheck(self, ct: Controller):
    nearbyBuildingIds = ct.get_nearby_buildings()
    for id in nearbyBuildingIds:
      if ct.get_team() == ct.get_team(id):
        continue
      if ct.get_entity_type(id) == EntityType.HARVESTER:
        continue
      if random.random() < 0.01:
        self.mode = Modes.SABOTUER

  def __conveyMove(self, dir:Direction, convDir:Direction, ct:Controller):
    pos = ct.get_position().add(dir)
    if ct.can_destroy(pos):
      ct.destroy(pos)
    if ct.can_build_conveyor(pos, convDir):
      ct.build_conveyor(pos, convDir)
    if ct.can_move(dir):
      ct.move(dir)

  def __tryBuildSentry(self, ct: Controller):
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

    # Check if we can we see sentinels and harvesters
    # Build if we can see NO sentinels and at least one harvester
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
    # Get all possible places we can build right now
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
    # See if any of those positions are also next to a harvester
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

  def __aquireHarvester(self, ct: Controller):
    if self.tryBuildAdjacentHarvester(ct):
      self.harvesters += 1
      # just made a harvester, can't make a conveyor to move onto
      return True

    myPos = ct.get_position()
    #home in on un-harvestered ores
    tiles = sensing.getQuadNocrossReachableTiles(myPos, ct)
    tiles.sort(key=lambda pos: pfind.getManhattanDistance(myPos, pos))
    moveDir = None
    for nearTile in tiles:
      if ct.get_tile_env(nearTile) not in [Environment.ORE_AXIONITE, Environment.ORE_TITANIUM]:
        continue
      if(ct.get_tile_building_id(nearTile) != None):
        continue
      
      testDir = pfind.safeQuadVisionBfsNocrossPath(myPos, nearTile, ct)
      if testDir is None or testDir is Direction.CENTRE:
        continue
      moveDir = testDir
      break
    if moveDir is None:
      return False
    revDir = moveDir.opposite()
    if ct.can_build_conveyor(myPos.add(moveDir),revDir):
      ct.build_conveyor(myPos.add(moveDir),revDir)
      if ct.can_move(moveDir):
        print("aquire Harvester move")
        ct.move(moveDir)
    return True
    
  def runReturnToCore(self, ct: Controller):
    mypos = ct.get_position()
    entityUnderId = ct.get_tile_building_id(mypos)
    entityUnderType = ct.get_entity_type(entityUnderId)
    moveDir = Direction.CENTRE
    if entityUnderId is not None and ct.get_team() == ct.get_team(entityUnderId):
      if entityUnderType == EntityType.CONVEYOR:
        moveDir = ct.get_direction(entityUnderId)
        self.revDir = moveDir
      elif entityUnderType == EntityType.CORE:
        self.harvesters = 0
        moveDir = self.__getNewConveyorLineDir(ct)
        self.revDir = moveDir.opposite()
    if(moveDir == Direction.CENTRE):
      return
    travelPos = mypos.add(moveDir)
    if not posIsInbounds(ct, travelPos):
      moveDir = random.choice([Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST])
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
      print("return to core move")
      ct.move(moveDir)
      if self.harvesters == 0:
        self.mode = Modes.CONVEYOR_LAYING

  def __getNewConveyorLineDir(self, ct: Controller):
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
      if (ct.is_tile_empty(testPos) and testBuilding is None) or random.random() < 0.1:
        return dir
      if ct.is_tile_passable(testPos) and ct.get_entity_type(testBuilding) == EntityType.CORE:
        coreDir = dir
    return coreDir
  
  def runFindNewBranch(self, ct:Controller):
    myPos = ct.get_position()
    
    if ct.get_global_resources()[0] < ct.get_sentinel_cost()[0]:
      return
    
    self.checkForEnemyCore(ct)

    if self.__tryBuildSentry(ct):
      return
    
    #check if empty tiles around to branch too
    possibleDirs: list[Direction] = []
    possibleMoves: list[tuple[Direction, Position]] = []
    for dir in QUAD_DIRECTIONS:
      tile = myPos.add(dir)
      if not posIsInbounds(ct, tile):
        continue
      if ct.get_tile_env(tile) != Environment.EMPTY:
        continue
      building = ct.get_tile_building_id(tile)
      if building != None:
        if ct.get_team() != ct.get_team(building):
          continue
        if ct.get_entity_type(building) != EntityType.ROAD:
          continue
      possibleDirs.append(dir)
      possibleMoves.append((dir, tile))
    
    #did we wander all the way back to the core?
    buildingUnder = ct.get_tile_building_id(myPos)
    if ct.get_entity_type(buildingUnder) == EntityType.CORE:
      self.mode = Modes.RETURN_TO_CORE
      return
    
    if buildingUnder == None or ct.get_entity_type(buildingUnder) != EntityType.CONVEYOR:
      print("help! I can't find new branch!")
      print("help! I can't find new branch!",ct.get_current_round(), file=sys.stderr)
      dir = random.choice(OCT_DIRECTIONS)
      if ct.can_move(dir):
        ct.move(dir)
      return

    if len(possibleDirs) == 0:
      print('no branches yet')
      backDir = ct.get_direction(buildingUnder)
      if ct.can_move(backDir):
        ct.move(backDir)
        return
      print("help! I can't find new branch!")
      dir = random.choice(OCT_DIRECTIONS)
      if ct.can_move(dir):
        ct.move(dir)
      return
    
    forbidList = list(map(lambda x: x[1], possibleMoves))
    forbidList.append(myPos)
    for dir, pos in possibleMoves:
      if dir in self.moveScoring:
        continue
      score = sensing.scoreQuadNocrossReachableTiles(pos, ct, forbiddenPosList=forbidList)
      print("dir:",dir,"score:",score)
      self.moveScoring[dir] = score

    bestDir = possibleMoves[0][0]
    bestScore = -1 * math.inf
    for dir in self.moveScoring:
      if self.moveScoring[dir] > bestScore:
        bestScore = self.moveScoring[dir]
        bestDir = dir
    
    if bestScore < ABORT_CONVEYOR:
      print('no branches yet')
      backDir = ct.get_direction(buildingUnder)
      if ct.can_move(backDir):
        ct.move(backDir)
        return
      print("help! I can't find new branch!")
      dir = random.choice(OCT_DIRECTIONS)
      if ct.can_move(dir):
        ct.move(dir)
      return
    
    #check if an empty tile is where we expect the conveyor to lead
    #and fix it if so
    priorityDir = ct.get_direction(buildingUnder).opposite()
    print("priorityDir:",priorityDir)
    if priorityDir in possibleDirs:
      print('repairing')
      #conveyor line damaged, repair
      missingTile = myPos.add(priorityDir)
      missingDir = None
      possibleMissingDirs: list[Direction] = []
      for dir in QUAD_DIRECTIONS:
        tile = missingTile.add(dir)
        if not posIsInbounds(ct, tile):
          continue
        building = ct.get_tile_building_id(tile)
        if building == None:
          possibleMissingDirs.append(dir)
          continue
        if ct.get_team() != ct.get_team(building):
          continue
        type = ct.get_entity_type(building)
        if type == EntityType.CORE:
          missingDir = dir
          break
        if type == EntityType.BRIDGE:
          possibleMissingDirs.append(dir)
          continue
        if type == EntityType.CONVEYOR and ct.get_direction(building) != dir.opposite():
          possibleMissingDirs.append(dir)
          continue
      if missingDir == None:
        missingDir = random.choice(possibleMissingDirs)
      self.__conveyMove(priorityDir, missingDir, ct)
      print("repairing",ct.get_current_round(),file=sys.stderr)
      print("repairing",ct.get_current_round())
      return

    self.__conveyMove(bestDir, bestDir.opposite(), ct)
    self.mode = Modes.CONVEYOR_LAYING
    return