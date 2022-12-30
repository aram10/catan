import math
from random import shuffle, sample
from typing import NewType, List

from constants import RESOURCE
from edge import Edge
from tile import Tile
from vertex import Vertex

import draw


def generate_tiles(num_tiles: int) -> List[Tile]:
    """
    Create tiles for board.

    :param num_tiles: Number of tiles to generate.
    :return: List of generated Tile objects.
    """
    chits = ([2] + list(range(3, 12)) * 2 + [12]) * ((num_tiles // 20) + 1)
    shuffle(chits)
    base_resources = [RESOURCE.BRICK, RESOURCE.GRAIN, RESOURCE.LUMBER, RESOURCE.ORE, RESOURCE.WOOL]
    resources = base_resources * ((num_tiles // len(base_resources)) + 1)
    shuffle(resources)
    # 1 desert tile for every 10 tiles
    desert_tiles = set(sample(list(range(num_tiles)), max((num_tiles // 10), 1)))
    tiles = []
    idx = 0
    while idx < num_tiles:
        tiles.append(
            Tile(resources.pop(), chits.pop()) if idx not in desert_tiles else Tile(RESOURCE.NONE, -1))
        idx += 1
    return tiles


def generate_board(n: int) -> tuple[List[List[Tile]], List[tuple[int]]]:
    """
    Fill in board with generated tiles.

    :param n: Number of rings around center tile.
    :return: The game board, and a list of all tile axial coordinates.
    """
    assert n > 0
    num_tiles = 1 + sum([6 * i for i in range(1, n + 1)])
    tiles = generate_tiles(num_tiles)
    tile_grid = [[None for j in range(2 * n + 1)] for i in range(2 * n + 1)]
    tile_coords = set()
    # fill in center row
    for i in range(2 * n + 1):
        tile_grid[n][i] = tiles.pop().set_coords(i, n)
        tile_coords.add((i, n, -i - n))
    # fill in everything above and below center row
    i = 1
    j = n - 1
    while j >= 0:
        tiles_upper = []
        tiles_lower = []
        for k in range(i, 2 * n + 1):
            tiles_upper.append(tiles.pop().set_coords(k, j))
            tile_coords.add((k, j, -k - j))
        tile_grid[j][i:] = tiles_upper
        for k in range(2 * n - i + 1):
            tiles_lower.append(tiles.pop().set_coords(k, 2 * n - j))
            tile_coords.add((k, 2 * n - j, -k - 2 * n + j))
        tile_grid[2 * n - j][:2 * n - i + 1] = tiles_lower
        i += 1
        j -= 1
    return tile_grid, tile_coords


def get_vertices_from_tile(tile: Tile) -> set[tuple[int]]:
    q, r = tile.get_coords()
    offset = q % 2
    return {(q, 2 * r + offset), (q, 2 * r + 1 + offset),
            (q, 2 * r + 2 + offset), (q + 1, 2 * r + offset),
            (q + 1, 2 * r + 1 + offset), (q + 1, 2 * r + 2 + offset)}


class Board:

    # TODO: debug coordinate transformations for edges and vertices

    def __init__(self, board_size: int):
        num_tiles = 1 + sum([6 * i for i in range(1, board_size + 1)])
        self.tiles, self.tile_coords = generate_board(board_size)
        for tilerow in self.tiles:
            for tile in tilerow:
                if tile is not None:
                    tile.set_vertices(get_vertices_from_tile(tile))
        self.vertices = [[Vertex(i, j) for j in range(2 * num_tiles + 2)] for i in range(2 * num_tiles + 2)]
        self.edges = [[Edge(i, j) for j in range(2 * num_tiles + 2)] for i in range(2 * num_tiles + 2)]
        self.n = board_size

    def get_tile(self, q: int, r: int) -> Tile:
        return self.tiles[r][q - max(0, self.n - (2 * self.n + 1 - abs(self.n - r)))]

    def get_vertex_from_tiles(self, tiles: tuple[Tile]):
        if len(tiles) != 3:
            raise ValueError("Attempted to get vertex from " + len(tiles) + " tiles; can only use 3 tiles.")
        res = list(get_vertices_from_tile(tiles[0]).intersection(
            get_vertices_from_tile(tiles[1]).intersection(get_vertices_from_tile(tiles[2]))))
        if len(res) == 0:
            raise ValueError("Tiles do not share a vertex")
        return self.vertices[res[0][0]][res[0][1]]

    def get_tiles_from_vertex(self, vertex: Vertex) -> set[Tile]:
        x, y = vertex.get_coords()
        xoffset = x % 2
        yoffset = y % 2
        return {self.get_tile(x - 1, (y + xoffset) // 2 - 1), self.get_tile(x - (1 - yoffset) * xoffset, (y - 1) // 2), self.get_tile(x, (y - xoffset) // 2)}

    def get_edges_from_vertex(self, vertex: Vertex):
        x, y = vertex.get_coords()
        offset = -1
        if x % 2 == y % 2:
            offset = 1
        return {self.edges[x*2][y-1], self.edges[x*2][y], self.edges[x*2+offset][y]}

    def get_edges_from_tile(self, tile: Tile):
        q, r = tile.get_coords()
        offset = -(q % 2)
        return {self.edges[2*q][2*r+offset],
                self.edges[2*q][2*r+1+offset],
                self.edges[2*q+1][2*r+offset],
                self.edges[2*q+1][2*r+2+offset],
                self.edges[2*q+2][2*r+offset],
                self.edges[2*q+2][2*r+1+offset]}

    def get_tile_coords(self) -> set[tuple[int]]:
        return self.tile_coords

    def get_tiles_with_chit(self, chit: int) -> List[Tile]:
        """
        Gets all board tiles that have a given chit value.
        :param chit: The chit value.
        :return: A list of tiles.
        """
        res = []
        for tile in self.tiles:
            if tile.get_dice_num() == chit:
                res.append(tile)
        return res


b = Board(3)
draw.draw(b)
