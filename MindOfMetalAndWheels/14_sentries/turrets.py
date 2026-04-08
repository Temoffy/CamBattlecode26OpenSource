# turret handling logic
# Team Mind of Metal and Wheels
# Author: Multiple, March 2026. Α⳩ω

from cambc import Controller, EntityType, Direction
import random, sys

class Turret():
  def __new__(cls, eType: EntityType):
    match eType:
      case EntityType.GUNNER:
        return Gunner()
      case EntityType.SENTINEL:
        return Sentinel()
      case _:
        print("can't find turret type error!", eType, file=sys.stderr)

class Gunner():
  def __init__(self):
    pass

  def startup(self, ct: Controller):
    #nothin
    return

  def run(self, ct: Controller):
    target = ct.get_gunner_target()
    if target != None:
      ct.fire(target)

class Sentinel():
  def __init__(self):
    self.direction = Direction.NORTH  # initial facing

  def startup(self, ct: Controller):
    # perhaps get current direction if possible
    pass

  def run(self, ct: Controller):
    nearbyBuildings = ct.get_nearby_buildings()
    nearbyBots = self.get_nearby_bots(ct)
    targets = []
    for building in nearbyBuildings:
      if ct.get_team() == ct.get_team(building):
        continue
      if ct.get_entity_type(building) == EntityType.HARVESTER:
        continue
      buildingPos = ct.get_position(building)
      if ct.can_fire(buildingPos):
        if ct.get_entity_type(building) == EntityType.SENTINEL:
          targets.insert(0, buildingPos)  # prioritize sentinels
        else:
          targets.append(buildingPos)
    for bot in nearbyBots:
      if ct.get_team() == ct.get_team(bot):
        continue
      botPos = ct.get_position(bot)
      if ct.can_fire(botPos):
        targets.append(botPos)
    if targets:
      ct.fire(targets[0])
    else:
      # rotate if no targets
      self.direction = self.direction.rotate_right()
    return
  
  def get_nearby_bots(self, ct: Controller):
    nearbyBots = ct.get_nearby_units()
    nearbyBots = [bot for bot in nearbyBots if ct.get_team(bot) != ct.get_team()]
    return nearbyBots