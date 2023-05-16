from typing import Set, Tuple

from exceptions import FailedBuildError
from constants import DIRECTION
from tile import Tile


class Vertex:

    def __init__(self, vertex_id: Set[Tuple[int, int]]):
        """
        Vertex uniquely identified by coordinates of its incident tiles.
        """
        self.vertex_id = vertex_id
        self.player_building_id = -1
        self.is_city = False

    def __hash__(self):
        return hash(self.vertex_id)

    def get_coords(self) -> tuple[int]:
        return self.q, self.r

    def get_player_id(self) -> int:
        return self.player_building_id

    def set_player_id(self, player_building_id: int):
        self.player_building_id = player_building_id

    def upgrade_to_city(self) -> bool:
        self.is_city = True

    def is_city(self) -> bool:
        return self.is_city
