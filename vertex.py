from exceptions import FailedBuildError
from constants import DIRECTION


class Vertex:

    def __init__(self, q: int, r: int):
        self.q = q
        self.r = r
        self.player_building_id = -1
        self.is_city = False

    def get_coords(self) -> tuple[int]:
        return self.q, self.r

    def get_player_id(self) -> int:
        return self.player_building_id

    def set_player_id(self, player_building_id: int):
        self.player_building_id = player_building_id

    def upgrade_to_city(self) -> bool:
        if self.player_building_id == -1:
            raise FailedBuildError("Cannot build a city without first building a settlement.")
        self.is_city = True
