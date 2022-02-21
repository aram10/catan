from enum import Enum


class RESOURCE(Enum):
    BRICK = 1
    GRAIN = 2
    LUMBER = 3
    ORE = 4
    WOOL = 5
    NONE = 6


class DIRECTION(Enum):
    NORTH = 1
    NORTHWEST = 2
    WEST = 3
    SOUTHWEST = 4
    SOUTH = 5
    SOUTHEAST = 6
    EAST = 7
    NORTHEAST = 8