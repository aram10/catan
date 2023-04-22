from typing import Tuple

from constants import DIRECTION


class Edge:

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.player_road_id = None

    def __eq__(self, other):
        return isinstance(other, Edge) and self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

    def get_coords(self) -> Tuple[int]:
        return self.x, self.y
