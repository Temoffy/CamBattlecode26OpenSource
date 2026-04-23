#state code for conveyor_bot
# Team Mind of Metal and Wheels
# Author: Multiple, March 2026. Α⳩ω

import sys, math, random
from cambc import Controller, EntityType, Direction, Environment, Position
import pathfinding as pfind
from tools import *
from bot_roles.builder_base import BuilderBase
from collections import defaultdict

class SaboteurMixin(BuilderBase):
  #all varibles here should be declared in the conveyor_bot init function!
  possibleEnemyCorePositions: list[Position]
  follow: int

  def runSaboteur(self, ct: Controller):
    if ct.get_global_resources()[0] < ct.get_sentinel_cost()[0] * (1 + random.random() / 4):
      return
    
    self.checkForEnemyCore(ct)

    ct.draw_indicator_dot(ct.get_position(), 255, 0, 0)

    if self.__runTurretLeech(ct):
      return

    if self.follow > 0:
      self.follow -= 1

    buildingUnderId = ct.get_tile_building_id(ct.get_position())
    if self.follow == 0 and buildingUnderId != None and ct.get_team(buildingUnderId) != ct.get_team():
      if ct.get_entity_type(buildingUnderId) in [EntityType.CONVEYOR , EntityType.ARMOURED_CONVEYOR]:
        testDir = ct.get_direction(buildingUnderId)
        if random.random() < 0.95 and ct.can_move(testDir):
          print("following conveyor")
          ct.move(testDir)
          return
        elif (ct.get_entity_type(ct.get_tile_building_id(ct.get_position().add(testDir))) == EntityType.CORE or random.random()<0.1) and ct.can_fire(ct.get_position()) and ct.get_entity_type(buildingUnderId) != EntityType.SENTINEL:
          ct.fire(ct.get_position())
          return
        else:
          self.follow = 20

    nearbyBuildings = ct.get_nearby_buildings()
    random.shuffle(nearbyBuildings)
    myPos = ct.get_position()
    for id in nearbyBuildings:
      pos = ct.get_position(id)
      if not ct.is_in_vision(pos):
        print("How did this pos get here????", file=sys.stderr)
        continue
      if ct.get_team() == ct.get_team(id) or not ct.is_tile_passable(pos):
        continue
      testDir = pfind.safeOctVisionBfsConsideratePath(myPos, pos, ct)
      if testDir != None and testDir != Direction.CENTRE:
        if ct.can_build_road(myPos.add(testDir)):
          ct.build_road(myPos.add(testDir))
        if ct.can_move(testDir):
          print("pathing to enemy")
          ct.move(testDir)
          return

    mixedDirs = OCT_DIRECTIONS
    for dir in mixedDirs:
      if ct.can_move(dir):
        print("moving randomly")
        ct.move(dir)
        return
    return

  def __runTurretLeech(self, ct: Controller):
    #can we see a harvester to leech?
    nearbyBuildingIds = ct.get_nearby_buildings()
    nearbyTiles = ct.get_nearby_tiles()
    enemyTiles: list[Position] = []
    myPos = ct.get_position()
    harvesters: list[Position] = []
    for buildingId in nearbyBuildingIds:
      if ct.get_team() == ct.get_team(buildingId):
        continue

      entityType = ct.get_entity_type(buildingId)
      if entityType == EntityType.HARVESTER:
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
      else:
        # enemy building, not harvester
        enemyTiles.append(ct.get_position(buildingId))
        if entityType == EntityType.SENTINEL:
          enemyTiles.append(ct.get_position(buildingId))
          enemyTiles.append(ct.get_position(buildingId))

    if len(harvesters) == 0:
      return False

    #pick nearest reachable harvester
    harvesters.sort(key=lambda pos: pfind.getManhattanDistance(myPos, pos))
    harvToLeechPos = None
    for harvPos in harvesters:
      testDir = pfind.safeOctVisionBfsConsideratePath(myPos, harvPos, ct)
      if testDir != None:
        harvToLeechPos = harvPos
        break

    if not harvToLeechPos:
      return False

    targetPos: Position | None = None
    targetDir: Direction | None = None
    cantShootDir = None
    for dir in pfind.QUAD_DIRECTIONS:
      testPos = harvToLeechPos.add(dir)
      if ct.get_tile_building_id(testPos) == None and ct.get_tile_env(testPos) == Environment.EMPTY:
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
        if ct.is_tile_passable(testPos) or myPos == testPos:
          testDir = pfind.safeOctVisionBfsConsideratePath(myPos, testPos, ct)
          if testDir == None:
            continue
          targetPos = testPos
          targetDir = testDir
          cantShootDir = dir.opposite()
          break
    if targetPos == None or targetDir == None:
      print("How did we get here?", file=sys.stderr)
      print("How did we get here?")
      return False

    # Get best direction to shoot
    all_enemy_positions = enemyTiles + self.possibleEnemyCorePositions
    dir_count = defaultdict(int)
    for enemy_pos in all_enemy_positions:
      dir = targetPos.direction_to(enemy_pos)
      dir_count[dir] += 1

    # This seems broken and I don't know why - c95
    if dir_count:
      aimingDir = max(dir_count, key=dir_count.get)
    else:
      aimingDir = Direction.NORTH  # default
    if aimingDir == cantShootDir:
      # If it would face the harvester, choose another direction
      dir_count[aimingDir] = 0  # exclude it

      # Same as above
      if dir_count:
        aimingDir = max(dir_count, key=dir_count.get)
      else:
        aimingDir = Direction.EAST  # fallback

    if ct.can_build_sentinel(targetPos, aimingDir):
      ct.build_sentinel(targetPos, aimingDir)
      return True
    if targetDir != Direction.CENTRE:
      if ct.can_build_road(ct.get_position().add(targetDir)):
        ct.build_road(ct.get_position().add(targetDir))
      if ct.can_move(targetDir):
        print("moving to leech")
        ct.move(targetDir)
    if targetPos == ct.get_position():
      if ct.can_fire(targetPos):
        ct.fire(targetPos)
      else: ct.draw_indicator_dot(targetPos, 255,255,255)
      if ct.is_tile_passable(targetPos):
        return True
    for dir in pfind.OCT_DIRECTIONS:
      if ct.can_move(dir):
        print("moving off leech")
        ct.move(dir)
        if ct.can_build_sentinel(targetPos, aimingDir):
          ct.build_sentinel(targetPos, aimingDir)
        break
    return True