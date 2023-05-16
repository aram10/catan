import itertools
import math
import random
from collections import defaultdict
from random import shuffle, sample
from typing import List, TYPE_CHECKING, Tuple, Set, Dict, Iterable
import networkx as nx

import numpy as np

import constants

if TYPE_CHECKING:
    import player

from constants import RESOURCE
from edge import Edge
from tile import Tile
from vertex import Vertex

import draw


def generate_resources_and_chits(num_tiles: int) -> List[Tuple[RESOURCE, int]]:
    """
    Creates resource/chit pairs that will be assigned to board tiles.

    :param num_tiles: Number of tiles to get resources/chits.
    :return: List of (resource, chit_value) tuples.
    """
    chits = ([2] + (list(range(3, 7)) + list(range(8, 12))) * 2 + [12]) * ((num_tiles // 19) + 1)
    shuffle(chits)
    base_resources = [RESOURCE.BRICK, RESOURCE.GRAIN, RESOURCE.LUMBER, RESOURCE.ORE, RESOURCE.WOOL]
    resources = base_resources * ((num_tiles // len(base_resources)) + 1)
    shuffle(resources)
    desert_tiles = set(sample(list(range(num_tiles)), max((num_tiles // 10), 1)))
    tile_data = []
    for idx in range(num_tiles):
        tile_data.append((resources.pop(), chits.pop()) if idx not in desert_tiles else (RESOURCE.DESERT, -1))
    return tile_data


def generate_board(n: int) -> tuple[List[List[Tile]], List[tuple[int]]]:
    """
    Fill in board with generated tiles.

    :param n: Number of rings around center tile.
    :return: The game board, and a list of all tile axial coordinates.
    """
    assert n > 0
    num_tiles = 1 + sum([6 * i for i in range(1, n + 1)])
    tiles = [Tile() for i in range(num_tiles)]
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


class Board:

    def __init__(self, board_size: int):
        # TODO: Cache boards for re-use
        self.board_size = board_size
        num_tiles = 1 + sum([6 * i for i in range(1, board_size + 1)])
        self.tiles, self.tile_coords = generate_board(board_size)
        # models vertices of tiles and adjacent vertices
        self.vertex_graph = nx.Graph()
        # holds actual Vertex objects referred to by the graph
        self.vertex_objects = {}
        # only generate resources/chits for non-water tiles
        tile_data = generate_resources_and_chits(num_tiles - 6 * board_size)
        remaining_chits = [2, 3, 4, 5, 9, 10, 11, 12]
        for coord in self.tile_coords:
            tile = self.get_tile(coord[0], coord[1])
            # if tile is on outer edge (i.e., water tile), don't give it resource/chit
            if coord[0] == 0 or coord[0] == 2 * board_size or coord[1] == 0 or coord[1] == 2 * board_size or coord[0] + \
                    coord[1] == board_size or coord[0] + coord[1] == 3 * board_size:
                tile.set_resource(RESOURCE.WATER)
            else:
                resource, chit_val = tile_data.pop()
                if resource != RESOURCE.DESERT:
                    # enforce rule that there are no 8-8, 6-6, or 8-6 connections
                    neighbor_rolls = {x.get_dice_num() for x in self.get_neighboring_tiles(tile)}
                    if 6 in neighbor_rolls or 8 in neighbor_rolls:
                        chit_val = remaining_chits[
                            np.where(np.random.multinomial(1, constants.CHIT_DIST_MOD) == 1)[0][0]]
                tile.set_resource(resource)
                tile.set_dice_num(chit_val)
            self.vertex_graph.add_node(tile)
        # create vertices and add them to the graph
        for tile in self.get_tiles():
            self.link_tile_and_vertices(tile)
        # Note that edges have their own coordinate system while vertices are defined by their incident tiles
        self.edges = [[Edge(i, j) for j in range(2 * num_tiles + 2)] for i in range(2 * num_tiles + 2)]

    def link_tile_and_vertices(self, tile: Tile):
        """
        Invoked during board creation. A Tile has 6 vertices (we will ignore 2 or 3 of them if tile is water tile).
        Each of these vertices is uniquely defined by 3 tiles (resource or otherwise).
        Given a Tile, this method links vertices in the graph to their incident tiles and to adjacent vertices.

        Side effects: new vertices added to graph, new vertex objects created, and adjacent vertices in graph linked.

        :param tile: The Tile object to get vertices for.
        """
        vertices = set()
        neighbors = self.get_neighboring_tiles(tile)
        tile_coords = tile.get_coords()
        for n1 in neighbors:
            n1_neighbors = self.get_neighboring_tiles(n1)
            n2_neighbors = list(neighbors.intersection(n1_neighbors))
            assert (len(n2_neighbors) == 2 or len(n2_neighbors) == 1)
            # neighboring tiles share 2 common neighbors (if neither are corner water tiles)
            # defines two vertices connected by an edge - add this connection to the graph
            t1 = n2_neighbors[0]
            v1 = frozenset({tile_coords, n1.get_coords(), t1.get_coords()})
            vertices.add(v1)
            if v1 not in self.vertex_graph:
                self.vertex_graph.add_node(v1)
                self.vertex_objects[v1] = Vertex(v1)
            self.vertex_graph.add_edge(tile, v1)
            if len(n2_neighbors) == 2:
                t2 = n2_neighbors[1]
                v2 = frozenset({tile_coords, n1.get_coords(), t2.get_coords()})
                vertices.add(v2)
                if v2 not in self.vertex_graph:
                    self.vertex_graph.add_node(v2)
                    self.vertex_objects[v2] = Vertex(v2)
                self.vertex_graph.add_edge(tile, v2)
                self.vertex_graph.add_edge(v1, v2)
        tile.set_vertices({self.vertex_objects[v] for v in vertices})

    def get_tile(self, q: int, r: int) -> Tile:
        try:
            return self.tiles[r][q - max(0, self.board_size - (2 * self.board_size + 1 - abs(self.board_size - r)))]
        except IndexError:
            return None

    def get_tiles(self) -> Iterable[Tile]:
        return iter(tile for row in self.tiles for tile in row if tile is not None)

    def get_edges_from_tile(self, tile: Tile) -> set[Edge]:
        q, r = tile.get_coords()
        return {self.edges[2 * q][2 * r - 1],
                self.edges[2 * q + 1][2 * r - 1],
                self.edges[2 * q + 1][2 * r],
                self.edges[2 * q][2 * r + 1],
                self.edges[2 * q - 1][2 * r + 1],
                self.edges[2 * q - 1][2 * r]}

    def get_neighboring_tiles(self, tile: Tile) -> set[Tile]:
        res = set()
        coords = tile.get_coords()
        q, r = coords[0], coords[1]
        if (t1 := self.get_tile(max(q - 1, 0), r + 1)) is not None:
            res.add(t1)
        if (t2 := self.get_tile(q, r + 1)) is not None:
            res.add(t2)
        if (t3 := self.get_tile(q + 1, r)) is not None:
            res.add(t3)
        if (t4 := self.get_tile(q + 1, max(r - 1, 0))) is not None:
            res.add(t4)
        if (t5 := self.get_tile(q, max(r - 1, 0))) is not None:
            res.add(t5)
        if (t6 := self.get_tile(max(q - 1, 0), r)) is not None:
            res.add(t6)
        return res.difference({tile})

    """
    This method serves as a sanity check that the results are the same
    as get_neighboring_tiles(). Otherwise it would be dumb to use this.
    """

    def get_neighboring_tiles_using_vertices(self, tile: Tile) -> set[Tile]:
        neighbors = set()
        vertices = self.get_vertices_from_tile(tile)
        for vertex in vertices:
            neighbors = neighbors.union({x.get_coords() for x in self.get_tiles_from_vertex(vertex)})
        return neighbors.difference({(tile.get_q(), tile.get_r())})

    """
    Same idea as above.
    """

    def get_neighboring_tiles_using_edges(self, tile: Tile) -> set[Tile]:
        neighbors = set()
        edges = self.get_edges_from_tile(tile)
        for tilerow in self.tiles:
            for t in tilerow:
                if t is not None:
                    if len(edges.intersection(self.get_edges_from_tile(t))) != 0:
                        neighbors = neighbors.union({t})
        return neighbors.difference({tile})

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

    def fetch_random_tile(self) -> Tile:
        """
        Temporary method for choosing robber position.
        """
        q = random.randint(0, 2 * self.board_size)
        r = random.randint(0, 2 * self.board_size)
        while (tile := self.get_tile(q, r)) is None:
            q = random.randint(0, 2 * self.board_size)
            r = random.randint(0, 2 * self.board_size)
        return tile

    def get_desert_tiles(self) -> set[Tile]:
        tiles = set()
        for tile_row in self.tiles:
            for tile in tile_row:
                if tile.get_resource() == RESOURCE.NONE:
                    tiles.add(tile)
        return tiles


if __name__ == '__main__':
    b = Board(4)
    draw.draw(b)
