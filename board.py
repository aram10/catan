import itertools
import math
import random
from collections import defaultdict, deque
from random import shuffle, sample
from typing import List, TYPE_CHECKING, Tuple, Set, Dict, Iterable
import networkx as nx

import numpy as np

import constants
from port import Port

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


def generate_board(n: int) -> Tuple[List[List[Tile]], List[Tuple[int]]]:
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


def get_edge_coords_from_tile(tile: Tile) -> Set[Tuple[int, int]]:
    q, r = tile.get_coords()
    return {(2 * q, 2 * r - 1),
            (2 * q + 1, 2 * r - 1),
            (2 * q + 1, 2 * r),
            (2 * q, 2 * r + 1),
            (2 * q - 1, 2 * r + 1),
            (2 * q - 1, 2 * r)}


def get_shared_edge_coords(t1: Tile, t2: Tile) -> Tuple[int, int]:
    res = get_edge_coords_from_tile(t1).intersection(get_edge_coords_from_tile(t2))
    if len(res) != 1:
        return None
    return list(res)[0]


class Board:

    def __init__(self, board_size: int):
        # TODO: Cache boards for re-use
        self.board_size = board_size
        num_tiles = 1 + sum([6 * i for i in range(1, board_size + 1)])
        self.tiles, self.tile_coords = generate_board(board_size)
        # models adjacent vertices (i.e., edges)
        self.vertex_graph = nx.Graph()
        # models tile-vertex relations
        self.tile_graph = nx.Graph()
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
            self.tile_graph.add_node(tile)
        # create vertices and add them to the graph
        tiles = []
        for tile in self.get_tiles():
            vertices = self.__link_tile_and_vertices(tile)
            tiles.append((tile, vertices))
        self.__add_port_objects()
        # port objects (which are vertices) aren't actually initialized until __add_port_objects()
        # this is why we have to delay setting a tile's vertices
        for el in tiles:
            tile, vertices = el
            tile.set_vertices({self.vertex_objects[v] for v in vertices})
        # Note that edges have their own coordinate system while vertices are defined by their incident tiles
        self.edges = [[Edge(i, j) for j in range(2 * num_tiles + 2)] for i in range(2 * num_tiles + 2)]

    def __link_tile_and_vertices(self, tile: Tile) -> Set[Vertex]:
        """
        Invoked during board creation. A Tile has 6 vertices (we will ignore 2 or 3 of them if tile is water tile).
        Each of these vertices is uniquely defined by 3 tiles (resource or otherwise).
        Given a Tile, this method links vertices in the graph to their incident tiles and to adjacent vertices.

        Side effects: new vertices added to graph, new vertex/port objects created, and adjacent vertices in graph linked.
        """
        attrs = {}
        vertices = set()
        neighbors = self.get_neighboring_tiles(tile)
        tile_coords = tile.get_coords()
        tile_shore = (tile.get_resource() == RESOURCE.WATER)
        for n1 in neighbors:
            n1_shore = (n1.get_resource() == RESOURCE.WATER)
            n1_neighbors = self.get_neighboring_tiles(n1)
            n2_neighbors = list(neighbors.intersection(n1_neighbors))
            assert (len(n2_neighbors) == 2 or len(n2_neighbors) == 1)
            # neighboring tiles share 2 common neighbors (if neither are corner water tiles)
            # defines two vertices connected by an edge - add this connection to the graph
            t1 = n2_neighbors[0]
            t1_shore = (t1.get_resource() == RESOURCE.WATER)
            v1 = frozenset({tile_coords, n1.get_coords(), t1.get_coords()})
            vertices.add(v1)
            if v1 not in self.vertex_graph:
                shore = (tile_shore or n1_shore or t1_shore)
                self.vertex_graph.add_node(v1, on_shore=shore)
                self.tile_graph.add_node(v1, on_shore=shore)
                if not shore:
                    self.vertex_objects[v1] = Vertex(v1)
            self.tile_graph.add_edge(tile, v1)
            if len(n2_neighbors) == 2:
                t2 = n2_neighbors[1]
                t2_shore = (t2.get_resource() == RESOURCE.WATER)
                v2 = frozenset({tile_coords, n1.get_coords(), t2.get_coords()})
                vertices.add(v2)
                if v2 not in self.vertex_graph:
                    shore = (tile_shore or n1_shore or t2_shore)
                    self.vertex_graph.add_node(v2, on_shore=shore)
                    self.tile_graph.add_node(v2, on_shore=shore)
                    if not shore:
                        self.vertex_objects[v2] = Vertex(v2)
                self.tile_graph.add_edge(tile, v2)
                self.vertex_graph.add_edge(v1, v2)
                shared_edge_coords = get_shared_edge_coords(tile, n1)
                assert (shared_edge_coords is not None)
                attrs[(v1, v2)] = {'obj': shared_edge_coords}
        nx.set_edge_attributes(self.vertex_graph, attrs)
        return vertices

    def __add_port_objects(self):
        """
        The job of this routine is to initialize ports intermittently around the edge of the map. Drawing from the
        original game, ports always come in pairs of two (i.e., two adjacent port vertices with same trading resource)
        and no two "port pairs" are directly adjacent.
        """
        shore_vertices = [x for x, y in self.vertex_graph.nodes(data=True) if y['on_shore']]
        visited = {x: False for x in shore_vertices}
        num_ports = 3 * self.board_size
        port_resources = [RESOURCE.GRAIN, RESOURCE.ORE, RESOURCE.WOOL, RESOURCE.LUMBER, RESOURCE.BRICK, None]*(math.ceil(num_ports/6))
        shuffle(port_resources)
        # begin initializing the first port
        curr_resource = port_resources.pop()
        curr = shore_vertices[0]
        curr_neighbors = [x for x in self.vertex_graph.neighbors(curr) if self.vertex_graph.nodes[x]['on_shore']]
        assert(len(curr_neighbors) == 2)
        self.vertex_objects[curr] = Port(curr, curr_resource)
        self.vertex_objects[curr_neighbors[0]] = Port(curr_neighbors[0], curr_resource)
        visited[curr] = True
        visited[curr_neighbors[0]] = True
        self.vertex_objects[curr_neighbors[1]] = Vertex(curr_neighbors[1])
        visited[curr_neighbors[1]] = True
        curr = [x for x in self.vertex_graph.neighbors(curr_neighbors[1]) if self.vertex_graph.nodes[x]['on_shore'] and not visited[x]]
        assert(len(curr) == 1)
        curr = curr[0]
        # at this point, there is one "port" pair
        i = 0
        while True:
            visited[curr] = True
            if i == 0:
                curr_resource = port_resources.pop()
                self.vertex_objects[curr] = Port(curr, curr_resource)
                i += 1
            elif i == 1:
                self.vertex_objects[curr] = Port(curr, curr_resource)
                i += 1
            else:
                self.vertex_objects[curr] = Vertex(curr)
                i = 0
            neighbors = [x for x in self.vertex_graph.neighbors(curr) if self.vertex_graph.nodes[x]['on_shore'] and not visited[x]]
            assert(len(neighbors) <= 1)
            if len(neighbors) == 0:
                break
            curr = neighbors[0]

    def get_tile(self, q: int, r: int) -> Tile:
        try:
            return self.tiles[r][q - max(0, self.board_size - (2 * self.board_size + 1 - abs(self.board_size - r)))]
        except IndexError:
            return None

    def get_tiles(self) -> Iterable[Tile]:
        return iter(tile for row in self.tiles for tile in row if tile is not None)

    def get_neighboring_tiles(self, tile: Tile) -> Set[Tile]:
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

    def get_edges_from_tile(self, tile: Tile) -> Set[Edge]:
        return {self.edges[x][y] for (x, y) in get_edge_coords_from_tile(tile)}

    def get_tile_coords(self) -> Set[Tuple[int]]:
        return self.tile_coords

    def get_tiles_with_chit(self, chit: int) -> List[Tile]:
        """
        Gets all board tiles that have a given chit value.
        :param chit: The chit value.
        :return: A list of tiles.
        """
        res = []
        for tile in self.get_tiles():
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

    def get_desert_tiles(self) -> Set[Tile]:
        tiles = set()
        for tile in self.get_tiles():
            if tile.get_resource() == RESOURCE.DESERT:
                tiles.add(tile)
        return tiles

    def get_tiles_from_vertex(self, v: Vertex) -> Set[Tile]:
        return set(self.tile_graph.adj[v.vertex_id])

    def get_vertices_from_tile(self, t: Tile) -> Set[Vertex]:
        return set(self.vertex_objects[x] for x in self.tile_graph.adj[t])


if __name__ == '__main__':
    b = Board(3)
    draw.draw(b)
