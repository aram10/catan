from typing import Tuple


class Edge:

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.player_road_id = -1
        # used for drawing the game
        self.canvas_pos = None
        self.rotation_angle = None

    def __eq__(self, other):
        return isinstance(other, Edge) and self.coords == other.coords

    def __hash__(self):
        return hash((self.x, self.y))

    @property
    def coords(self) -> Tuple[int]:
        return self.x, self.y

    @coords.setter
    def coords(self, value):
        self.x, self.y = value
