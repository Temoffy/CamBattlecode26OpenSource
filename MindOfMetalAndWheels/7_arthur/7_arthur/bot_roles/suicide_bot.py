# Reliable Suicide Bomber Builder Bot for Cambridge Battlecode 2026
# Team Mind of Metal and Wheels

import random
from cambc import Controller, Direction, EntityType, GameError
from bot_roles.builder_base import BuilderBase

SPAWN_DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]

class SuicideBot(BuilderBase):
  def __init__(self):
      super().__init__()
      self.moveDir = random.choice(SPAWN_DIRECTIONS)
      self.pos = None

  def run(self, ct: Controller) -> None:
      self.pos = ct.get_position()

      # --- Step 1: Follow conveyor beneath ---
      tileUnderneath = ct.get_tile_building_id(self.pos)
      if tileUnderneath is not None and ct.get_entity_type(tileUnderneath) == EntityType.CONVEYOR:
          if ct.get_team(tileUnderneath) != ct.get_team():
              conveyorDir = ct.get_direction(tileUnderneath)
              self.moveDir = conveyorDir

      # --- Step 2: Check nearby tiles for enemy core ---
      nearby_tiles = ct.get_nearby_tiles()
      for tile in nearby_tiles:
          tile = ct.get_tile_building_id(tile)
          if tile is not None and ct.get_entity_type(tile) == EntityType.CORE:
              if ct.get_team(tile) != ct.get_team() and (ct.get_team(tileUnderneath) != ct.get_team()):
                  try:
                      ct.self_destruct()
                      return  # Stop running after exploding
                  except GameError:
                      pass  # Safety if self_destruct fails

      # --- Step 3: Move along conveyor ---
      if random.random() < 0.05:
          # Occasionally change direction to avoid getting stuck
          self.moveDir = random.choice(SPAWN_DIRECTIONS)

      nextPos = self.pos.add(self.moveDir)
      if ct.can_build_road(nextPos):
          #building roads can drain our resources if we aren't careful.
          if ct.get_global_resources()[0] < ct.get_harvester_cost()[0] * (1 + random.random() / 4):
            return
          ct.build_road(nextPos)

      if ct.can_move(self.moveDir):
          ct.move(self.moveDir)
      else:
          #if it's not shuffled, prefers to go north/east over all other directions.
          randomDirections = [d for d in Direction]
          random.shuffle(randomDirections)
          # If blocked, pick any valid direction (preferably towards conveyors)
          for d in randomDirections:
              if d != Direction.CENTRE and ct.can_move(d):
                  self.moveDir = d
                  ct.move(d)
                  break