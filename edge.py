from constants import DIRECTION


class Edge:

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.player_road_id = None
