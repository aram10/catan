from constants import DIRECTION


class Vertex:

    def __init__(self, q: int, r: int):
        self.q = q
        self.r = r
        self.player_building_id = None
        self.is_city = False

    def get_coords(self) -> tuple[int]:
        return self.q, self.r

