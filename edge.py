from constants import DIRECTION
from tile import Tile


class Edge:
    """
    A tile "owns" its west, northwest, and southwest edges, analogously to a vertex. For example, an edge key might be
    '-21SW'.
    """

    def __init__(self, tile: Tile, d: DIRECTION) -> None:
        assert d in [DIRECTION.WEST, DIRECTION.NORTHWEST, DIRECTION.SOUTHWEST], 'Invalid edge.'
        tile_coords = tile.get_coords()
        self.q = tile_coords[0]
        self.r = tile_coords[1]
        self.d = d
        self.player_road_id = None
