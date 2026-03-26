# Main code for Cambridge Battlecode 2026
# Team Mind of Metal and Wheels
# Author: Multiple, March 2026. Α⳩ω

import random

from cambc import Controller, Direction, EntityType, Environment, Position

# non-centre directions
SPAWN_DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
# Job types:
PAVER = 0
BUILDER = 1
EXPLORER = 2

DIRECTIONS4 = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
class Player:
  def __init__(self):
    self.numSpawned = 0 # number of builder bots spawned so far (core)
    # direction to move in (builder bot) - conveyors (and the opposite-direction logic below) assume cardinal moves
    self.moveDir = random.choice(DIRECTIONS4)
    self.revDir = Direction.opposite(self.moveDir) # direction opposite to move_dir, used for building conveyors

  #
  def run(self, ct: Controller) -> None:
    entityType = ct.get_entity_type()

    # ----------------------------------------------
    # Core logic
    # ----------------------------------------------
    if entityType == EntityType.CORE:
      if self.numSpawned >= 1:
        return
      spawn_pos = ct.get_position().add(random.choice(SPAWN_DIRECTIONS))
      if not ct.can_spawn(spawn_pos):
        return
      ct.spawn_builder(spawn_pos)

      # Increment numSpawned by 1
      self.numSpawned += 1

      # place a marker on an adjacent tile with the job number of the bot
      markerPos = ct.get_position().add(random.choice(SPAWN_DIRECTIONS)).add(random.choice(SPAWN_DIRECTIONS))
      if ct.can_place_marker(markerPos):
        ct.place_marker(markerPos, self.numSpawned % 3)

    # ----------------------------------------------
    # Builder bot logic
    # ----------------------------------------------
    elif entityType == EntityType.BUILDER_BOT:
      if (self.numSpawned % 3) == PAVER:
        for d in Direction:
          checkPos = ct.get_position().add(d)
          if ct.can_build_harvester(checkPos):
            ct.build_harvester(checkPos)
            #just made a harvester, can't make a conveyor to move onto
            return

        # move logic
        while True:
          movePos = ct.get_position().add(self.moveDir)

          if self.isEnemyAt(ct, movePos):
            self.changeMoveDir()
            continue
          if ct.can_build_conveyor(movePos, self.revDir):
            ct.build_conveyor(movePos, self.revDir)
          elif ct.can_move(self.moveDir) and random.random() < 0.2:
            #can't build but can move means we are conveyor following
            #TODO check if conveyor is perpendicular to move, and if so don't turn??
            self.changeMoveDir()
            continue

          if ct.can_move(self.moveDir):
            ct.move(self.moveDir)
            break
          self.changeMoveDir()

        # place a marker on an adjacent tile with the current round number
        # holdover from starter bot
        # markerPos = ct.get_position().add(random.choice(SPAWN_DIRECTIONS))
        # if ct.can_place_marker(markerPos):
        #   ct.place_marker(markerPos, ct.get_current_round())

  def isEnemyAt(self, ct: Controller, pos: Position) -> bool:
    # Avoid calling tile queries out-of-bounds.
    if pos.x < 0 or pos.y < 0 or pos.x >= ct.get_map_width() or pos.y >= ct.get_map_height():
      return False

    # Enemy builder bot?
    #TODO consider removing, may not ever be relevant.
    botId = ct.get_tile_builder_bot_id(pos)
    if botId is not None and ct.get_team(botId) != ct.get_team():
      return True

    # Enemy building?
    buildingId = ct.get_tile_building_id(pos)
    if buildingId is not None and ct.get_team(buildingId) != ct.get_team() and ct.get_entity_type(buildingId) != EntityType.MARKER:
      return True

    return False

  def changeMoveDir(self):
    #exclude the current direction and turning back.
    possibleDirections = [d for d in DIRECTIONS4 if d != self.moveDir and d != self.revDir]
    self.moveDir = random.choice(possibleDirections)
    self.revDir = Direction.opposite(self.moveDir)
