from constants import DIRECTION


class Edge:
    """
    A tile "owns" its west, northwest, and southwest edges, analogously to a vertex. For example, an edge key might be
    '-21SW'.
    """

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.player_road_id = None
