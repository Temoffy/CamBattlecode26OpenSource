# turret handling logic
# Team Mind of Metal and Wheels
# Author: Multiple, March 2026. Α⳩ω

from cambc import Controller, Direction, EntityType, Environment, Position
import random, sys

class Turret():
  def __new__(cls, eType: EntityType):
    match eType:
      case EntityType.GUNNER:
        return Gunner()
    print("can't find turret type error!", eType, file=sys.stderr)

class Gunner():
  def __init__(self):
    pass

  def run(self, ct: Controller):
    target = ct.get_gunner_target()
    if target != None:
      ct.fire(target)