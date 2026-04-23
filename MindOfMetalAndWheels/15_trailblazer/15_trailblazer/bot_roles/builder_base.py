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
    # Direction to move in - conveyors (and the opposite-direction logic below) assume cardinal moves
    self.moveDir: Direction = random.choice(QUAD_DIRECTIONS)
    self.revDir: Direction = Direction.opposite(self.moveDir) # direction opposite to moveDir, used for building conveyors
    self.doublePlaced: int = 0
    self.coreLocation: Position | None = None

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
    # Avoid calling tile queries out-of-bounds
    inBounds = posIsInbounds(ct, pos)
    if not inBounds:
      return False

    # Check if a tile contains an enemy bot
    botId = ct.get_tile_builder_bot_id(pos)
    if botId is not None and ct.get_team(botId) != ct.get_team():
      return True

    # Check if a tile contains an enemy building
    buildingId = ct.get_tile_building_id(pos)
    if buildingId is not None and ct.get_team(buildingId) != ct.get_team() and ct.get_entity_type(buildingId) != EntityType.MARKER:
      return True

    return False

  def changeMoveDir(self):
    # Exclude the current direction and turn back.
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

  def adjustSentinels(self, ct: Controller) -> None:
    # Sentinel adjustment logic - future-proofed for all bot types
    my_pos = ct.get_position()
    nearby_tiles = ct.get_nearby_tiles()
    nearby_buildings = ct.get_nearby_buildings()
    nearby_bots = self.get_nearby_bots(ct)
    enemies = []
    for id in nearby_buildings:
      if ct.get_team(id) != ct.get_team() and ct.is_in_vision(ct.get_position(id)):
        pos = ct.get_position(id)
        is_sentinel = ct.get_entity_type(id) == EntityType.SENTINEL
        enemies.append((pos, is_sentinel))
    for id in nearby_bots:
      if ct.get_team(id) != ct.get_team() and ct.is_in_vision(ct.get_position(id)):
        pos = ct.get_position(id)
        is_sentinel = False
        enemies.append((pos, is_sentinel))
    if not enemies:
      return
    for d in QUAD_DIRECTIONS:
      adj_pos = my_pos.add(d)
      if adj_pos not in nearby_tiles:
        continue
      building_id = ct.get_tile_building_id(adj_pos)
      if building_id is None or ct.get_entity_type(building_id) != EntityType.SENTINEL or ct.get_team(building_id) != ct.get_team():
        continue
      sentinel_dir = ct.get_direction(building_id)
      facing_enemy = False
      for enemy_pos, _ in enemies:
        enemy_dir = adj_pos.direction_to(enemy_pos)
        if enemy_dir == sentinel_dir:
          facing_enemy = True
          break
      if not facing_enemy:
        ct.destroy(adj_pos)
        # Pick an enemy not towards core, prioritizing sentinels
        core_pos = self.coreLocation
        target_enemy = None
        if core_pos is not None:
          # First, try enemy sentinels not towards core
          for enemy_pos, is_sentinel in enemies:
            if not is_sentinel:
              continue
            dir_to_enemy = adj_pos.direction_to(enemy_pos)
            dir_to_core = adj_pos.direction_to(core_pos)
            if dir_to_enemy != dir_to_core:
              target_enemy = enemy_pos
              break
          if target_enemy is None:
            # Then, any enemy not towards core
            for enemy_pos, is_sentinel in enemies:
              dir_to_enemy = adj_pos.direction_to(enemy_pos)
              dir_to_core = adj_pos.direction_to(core_pos)
              if dir_to_enemy != dir_to_core:
                target_enemy = enemy_pos
                break
        if target_enemy is None and enemies:
          # Fallback, pick first enemy (prefer sentinel)
          for enemy_pos, is_sentinel in enemies:
            if is_sentinel:
              target_enemy = enemy_pos
              break
          if target_enemy is None:
            target_enemy = enemies[0][0]
        if target_enemy is not None:
          aiming_dir = adj_pos.direction_to(target_enemy)
          if ct.can_build_sentinel(adj_pos, aiming_dir):
            ct.build_sentinel(adj_pos, aiming_dir)

  def get_nearby_bots(self, ct: Controller):
    nearbyBots = ct.get_nearby_units()
    nearbyBots = [bot for bot in nearbyBots if ct.get_team(bot) != ct.get_team()]
    return nearbyBots