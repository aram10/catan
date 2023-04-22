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

    def __init__(self, resource: RESOURCE, dice_num: int, is_water_tile: bool = False):
        self.q = -1
        self.r = -1
        self.resource = resource
        self.dice_num = dice_num
        self.vertices = set()
        self.robber = False
        self.is_water_tile = is_water_tile

    def __hash__(self):
        return hash((self.q, self.r, self.resource, self.dice_num))

    def __eq__(self, other):
        return isinstance(other, Tile) and self.q == other.q and self.r == other.r

    def set_coords(self, q: int, r: int):
        self.q = q
        self.r = r
        return self

    def get_coords(self) -> tuple:
        return self.q, self.r

    def get_q(self) -> int:
        return self.q

    def get_r(self) -> int:
        return self.r

    def get_dice_num(self) -> int:
        return self.dice_num

    def get_vertices(self) -> set[Vertex]:
        return self.vertices

    def set_vertices(self, vertices: set[Vertex]):
        """
        Invoked through board.py for initialization purposes.
        """
        self.vertices = vertices

    def get_resource(self) -> RESOURCE:
        return self.resource

    def place_robber(self):
        self.robber = True

    def remove_robber(self):
        self.robber = False

    def has_robber(self) -> bool:
        return self.robber
