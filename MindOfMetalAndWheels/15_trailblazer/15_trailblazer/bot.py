# Bot role handling logic
# Team Mind  of Metal and Wheels
# Author: Multiple, March 2026. Α⳩ω

from cambc import Controller
from bot_roles.conveyor_bot import ConveyorBot

# Do we need this now? - c95
SUICIDE_BOT_CHANCE = 0.1

class Bot():
  def __new__(cls, ct: Controller):
    return ConveyorBot()