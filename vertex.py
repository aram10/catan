from constants import DIRECTION
from tile import Tile


class Vertex:
    """
    A tile "owns" its northmost and southmost vertices. They are represented by 3 coordinates. The first 2 are the
    q and r coordinates of the corresponding hex tile. The third coordinate is an 'N' or 'S' representing north and
    south. For example, a vertex key might be '01S'
    """

    def __init__(self, tile: Tile, d: DIRECTION) -> None:
        assert d in [DIRECTION.NORTH, DIRECTION.SOUTH], 'Invalid vertex.'
        tile_coords = tile.get_coords()
        self.q = tile_coords[0]
        self.r = tile_coords[1]
        self.d = d
        self.player_building_id = None
        self.is_city = False
