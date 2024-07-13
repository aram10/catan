from typing import Tuple, Set


class Tile:
    """
    This class represents one hexagonal tile on the Catan grid.

    All tiles are associated with an integer dice roll in the range [1,12] and a resource in the set {'BRICK', 'GRAIN',
    'LUMBER', 'ORE', 'WOOL'}.
    """

    def __init__(self):
        self.q = -1
        self.r = -1
        self.resource = None
        self.dice_num = -1
        self.vertices = None
        self.robber = False
        self.is_water_tile = False
        # used for drawing the game
        self.canvas_pos = None

    def __hash__(self):
        return hash((self.q, self.r, self.resource))

    def __eq__(self, other):
        return isinstance(other, Tile) and self.coords == other.coords

    @property
    def coords(self) -> Tuple[int, int]:
        return self.q, self.r

    @coords.setter
    def coords(self, value):
        self.q, self.r = value
