from typing import Tuple, Set, List

from constants import Resource
from tile import Tile

GraphVertex = Set[Tuple[int, int]]
GraphEdge = Tuple[GraphVertex, GraphVertex]
TileCoords = List[Tuple[int, int]]
EdgeCoords = Set[Tuple[int, int]]
TileGrid = List[List[Tile]]
TileData = List[Tuple[Resource, int]]
