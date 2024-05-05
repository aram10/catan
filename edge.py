from typing import Tuple, AbstractSet

from constants import DIRECTION


class Edge:

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.player_road_id = -1
        # used for drawing the game
        self.canvas_pos = None
        self.rotation_angle = None

    def __eq__(self, other):
        return isinstance(other, Edge) and self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

    def get_coords(self) -> Tuple[int]:
        return self.x, self.y

    def get_player_road_id(self) -> int:
        return self.player_road_id

    def set_player_road_id(self, i: int):
        self.player_road_id = i

    def get_canvas_pos(self) -> Tuple[int, int]:
        return self.canvas_pos

    def set_canvas_pos(self, pos: Tuple[int, int]):
        self.canvas_pos = pos

    def set_rotation_angle(self, angle):
        self.rotation_angle = angle
