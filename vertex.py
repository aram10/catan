from typing import Set, Tuple

from custom_types import GraphVertex
from exceptions import FailedBuildError
from constants import DIRECTION
from tile import Tile


class Vertex:

    def __init__(self, vertex_id: GraphVertex):
        """
        Vertex uniquely identified by coordinates of its incident tiles.
        """
        self.vertex_id = vertex_id
        self.player_building_id = -1
        self.is_city = False
        # used for drawing the game
        self.canvas_pos = None

    def __hash__(self):
        return hash(self.vertex_id)

    def get_vertex_id(self) -> GraphVertex:
        return self.vertex_id

    def get_player_id(self) -> int:
        return self.player_building_id

    def set_player_id(self, player_building_id: int):
        self.player_building_id = player_building_id

    def upgrade_to_city(self) -> bool:
        self.is_city = True

    def is_city(self) -> bool:
        return self.is_city

    def get_canvas_pos(self) -> Tuple[int, int]:
        return self.canvas_pos

    def set_canvas_pos(self, pos: Tuple[int, int]):
        self.canvas_pos = pos
