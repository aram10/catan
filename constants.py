from enum import IntEnum


class RESOURCE(IntEnum):
    BRICK = 0
    GRAIN = 1
    LUMBER = 2
    ORE = 3
    WOOL = 4
    DESERT = 5
    WATER = 6


class DIRECTION(IntEnum):
    NORTH = 0
    NORTHWEST = 1
    WEST = 2
    SOUTHWEST = 3
    SOUTH = 4
    SOUTHEAST = 5
    EAST = 6
    NORTHEAST = 7


class PLAYERCOLOR(IntEnum):
    RED = 0
    BLUE = 1
    WHITE = 2
    YELLOW = 3
    GREEN = 4
    BROWN = 5


"""
If we extrapolate from the base game, the chits [2,3,4,5,6,8,9,10,11,12] follow the multinomial distribution:

[1/18, 1/9, 1/9, 1/9, 1/9, 1/9, 1/9, 1/9, 1/9, 1/18]

However, we are not allowed to have any two 6 or 8 chits adjacent to one another. So, if during generation, we must
pick a chit other than 6 or 8 due to this constraint, we can sample from this modified distribution, where the
probability mass for 6 and 8 have been equally divided among the remaining chits.
"""
CHIT_DIST_MOD = [1/18 + 1/36, 1/9 + 1/36, 1/9 + 1/36, 1/9 + 1/36, 1/9 + 1/36, 1/9 + 1/36, 1/9 + 1/36, 1/18 + 1/36]
