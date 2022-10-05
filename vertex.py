from constants import DIRECTION


class Vertex:

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.player_building_id = None
        self.is_city = False

