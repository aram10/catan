from enum import Enum

from constants import RESOURCE
from edge import Edge
from vertex import Vertex


class Tile:
    """
    This class represents one hexagonal tile on the Catan grid.

    All tiles are associated with an integer dice roll in the range [1,12] and a resource in the set {'BRICK', 'GRAIN',
    'LUMBER', 'ORE', 'WOOL'}.
    """

    def __init__(self, q: int, r: int, resource: RESOURCE, dice_num: int):
        self.q = q
        self.r = r
        self.s = -q - r
        self.resource = resource
        self.dice_num = dice_num

    def get_coords(self) -> tuple:
        return self.q, self.r