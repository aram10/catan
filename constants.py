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
