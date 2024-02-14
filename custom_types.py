from typing import Tuple, Set, List

from constants import RESOURCE
from tile import Tile

GraphVertex = Set[Tuple[int, int]]
GraphEdge = Tuple[GraphVertex, GraphVertex]
TileCoords = List[Tuple[int, int]]
EdgeCoords = Set[Tuple[int, int]]
TileGrid = List[List[Tile]]
TileData = List[Tuple[RESOURCE, int]]
