
import random

from cambc import Controller, Direction, EntityType, Environment, Position

# non-centre directions
SPAWN_DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]

DIRECTIONS4 = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
#this code is roughly equivelent to a while loop
#with __init__ being run outside the loop, and run() being run once per iteration
class Player:
    def __init__(self):
        #variables created here will be remembered across rounds, and can be used in run()
        #but not remembered across different bots
        self.num_spawned = 0 # number of builder bots spawned so far (core)
        # direction to move in (builder bot) - conveyors (and the opposite-direction logic below) assume cardinal moves
        self.move_dir = random.choice(DIRECTIONS4)
        self.rev_dir = Direction.opposite(self.move_dir) # direction opposite to move_dir, used for building conveyors
        

    def run(self, ct: Controller) -> None:
        #ct is the thing we are controlling
        #self is a python thing, lets us refer to stuff set in __init__ (and elsewhere when we get there)
        entityType = ct.get_entity_type()
        if entityType == EntityType.CORE:
            #controlling the core
            if self.num_spawned >= 1:
                return
            # if we haven't spawned 3 builder bots yet, try to spawn one on a random tile
            spawn_pos = ct.get_position().add(random.choice(SPAWN_DIRECTIONS))
            if not ct.can_spawn(spawn_pos):
                return
            ct.spawn_builder(spawn_pos)
            self.num_spawned += 1
        elif entityType == EntityType.BUILDER_BOT:
            #controlling a builder bot
            # if we are adjacent to an ore tile, build a harvester on it
            for d in Direction:
                check_pos = ct.get_position().add(d)
                if ct.can_build_harvester(check_pos):
                    ct.build_harvester(check_pos)
                    #because we build a harvester, we can't build a conveyor this round.
                    #because we can't build a conveyor, we might not be able to move.
                    #because we might not be able to move, we might think we're stuck on a wall
                    #to avoid that, just stop the turn here.
                    return

            # move in set direction
            move_pos = ct.get_position().add(self.move_dir)
            
            # we need to place a conveyor or road to stand on, before we can move onto a tile
            if ct.can_build_conveyor(move_pos, self.rev_dir):
                ct.build_conveyor(move_pos, self.rev_dir)
            #this extra can_move check is because we might have built a harvester, and so couldn't build a road
            if ct.can_move(self.move_dir):
                ct.move(self.move_dir)
            else:
                #exclude the current direction and turning back.
                possibleDirections = [d for d in DIRECTIONS4 if d != self.move_dir and d != self.rev_dir]
                self.move_dir = random.choice(possibleDirections)
                self.rev_dir = Direction.opposite(self.move_dir)

            # place a marker on an adjacent tile with the current round number
            marker_pos = ct.get_position().add(random.choice(SPAWN_DIRECTIONS))
            if ct.can_place_marker(marker_pos):
                ct.place_marker(marker_pos, ct.get_current_round())
