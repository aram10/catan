from random import shuffle, sample
from typing import NewType, List

from constants import RESOURCE
from edge import Edge
from tile import Tile
from vertex import Vertex


class Board:

    def __init__(self, mid_row_len: int, top_row_len: int):

        self.offset = mid_row_len // 2
        self.tiles = [[None for _ in range(mid_row_len)] for _ in range(mid_row_len)]
        self.vertices = [[None for _ in range(2 * mid_row_len + 1)] for _ in range(2 * mid_row_len + 1)]
        self.edges = [[None for _ in range(2 * mid_row_len + 1)] for _ in range(2 * mid_row_len + 1)]
        self.cache = {}

        def _init_vertices_and_edges(_q: int, _r: int):
            r_offset = _q % 2
            self.vertices[self.offset + _q][self.offset + 2 * _r + r_offset] = Vertex(_q, 2 * _r + r_offset)
            self.vertices[self.offset + _q][self.offset + 2 * _r + 1 + r_offset] = Vertex(_q, 2 * _r + 1 + r_offset)
            self.vertices[self.offset + _q][self.offset + 2 * _r + 2 + r_offset] = Vertex(_q, 2 * _r + 2 + r_offset)
            self.vertices[self.offset + _q + 1][self.offset + 2 * _r + r_offset] = Vertex(_q + 1, 2 * _r + r_offset)
            self.vertices[self.offset + _q + 1][self.offset + 2 * _r + 1 + r_offset] = Vertex(_q + 1,
                                                                                              2 * _r + 1 + r_offset)
            self.vertices[self.offset + _q + 1][self.offset + 2 * _r + 2 + r_offset] = Vertex(_q + 1,
                                                                                              2 * _r + 2 + r_offset)

            self.edges[self.offset + 2 * _q][self.offset + 2 * _r + r_offset] = Edge(2 * _q, 2 * _r + r_offset)
            self.edges[self.offset + 2 * _q][self.offset + 2 * _r + 1 + r_offset] = Edge(2 * _q, 2 * _r + 1 + r_offset)
            self.edges[self.offset + 2 * _q + 1][self.offset + 2 * _r + r_offset] = Edge(2 * _q + 1, 2 * _r + r_offset)
            self.edges[self.offset + 2 * _q + 1][self.offset + 2 * _r + 2 + r_offset] = Edge(2 * _q + 1, 2 * _r + 2 + r_offset)
            self.edges[self.offset + 2 * _q + 2][self.offset + 2 * _r + r_offset] = Edge(2 * _q + 2, 2 * _r + r_offset)
            self.edges[self.offset + 2 * _q + 2][self.offset + 2 * _r + 1 + r_offset] = Edge(2 * _q + 2, 2 * _r + 1 + r_offset)

        num_tiles = 2 * sum(range(top_row_len, mid_row_len + 1))
        base_chits = [2] + list(range(3, 12)) * 2 + [12]
        chits = base_chits * ((num_tiles // len(base_chits)) + 1)
        shuffle(chits)
        base_resources = [RESOURCE.BRICK, RESOURCE.GRAIN, RESOURCE.LUMBER, RESOURCE.ORE, RESOURCE.WOOL]
        resources = base_resources * ((num_tiles // len(base_resources)) + 1)
        shuffle(resources)
        desert_tiles = set(sample(list(range(num_tiles)), num_tiles // 10))  # 1 desert tile for every 10 tiles
        # keep track of tile index to assign desert tiles
        idx = 0
        # create middle tiles
        tile = Tile(0, 0, resources.pop(), chits.pop()) if idx not in desert_tiles else Tile(0, 0, RESOURCE.NONE, -1)
        idx = idx + 1
        self.tiles[self.offset][self.offset] = tile
        middle_tiles = [(0, 0)]
        q = 1
        r = 0
        while len(middle_tiles) < mid_row_len:
            end_tile = Tile(q, r, resources.pop(), chits.pop()) \
                if idx not in desert_tiles else Tile(q, r, RESOURCE.NONE, -1)
            idx = idx + 1
            start_tile = Tile(-q, r, resources.pop(), chits.pop()) \
                if idx not in desert_tiles else Tile(-q, r, RESOURCE.NONE, -1)
            idx = idx + 1
            self.tiles[self.offset + q][self.offset + r] = end_tile
            _init_vertices_and_edges(q, r)
            self.tiles[self.offset + -q][self.offset + r] = start_tile
            _init_vertices_and_edges(-q, r)
            middle_tiles.append((q, r))
            middle_tiles.insert(0, (-q, r))
            q = q + 1
        curr_row = middle_tiles
        # add tiles above, offset to the right
        # add 1 to q, subtract 1 from r
        while len(curr_row) > top_row_len:
            temp_row = []
            for i in range(len(curr_row) - 1):
                el = curr_row[i]
                q = el[0] + 1
                r = el[1] - 1
                new_tile = Tile(q, r, resources.pop(), chits.pop()) \
                    if idx not in desert_tiles else Tile(q, r, RESOURCE.NONE, -1)
                idx = idx + 1
                self.tiles[self.offset + q][self.offset + r] = new_tile
                _init_vertices_and_edges(q, r)
                temp_row.append((q, r))
                # mirrored tile
                q_bottom = q + r
                r_bottom = -r
                new_tile_bottom = Tile(q_bottom, r_bottom, resources.pop(), chits.pop()) \
                    if idx not in desert_tiles else Tile(q_bottom, r_bottom, RESOURCE.NONE, -1)
                self.tiles[self.offset + q_bottom][self.offset + r_bottom] = new_tile_bottom
                _init_vertices_and_edges(q_bottom, r_bottom)
            curr_row = temp_row

    def get_tile_coords(self):
        if 'coords' not in self.cache:
            coords = []
            for row in self.tiles:
                for tile in row:
                    if tile is not None:
                        coords.append((tile.q, tile.r, tile.s))
            self.cache['coords'] = coords
        return self.cache['coords']

    def get_resources(self):
        if 'resources' not in self.cache:
            resources = []
            for row in self.tiles:
                for tile in row:
                    if tile is not None:
                        resources.append(tile.resource)
            self.cache['resources'] = resources
        return self.cache['resources']

    def tiles_from_vertex(self, v: Vertex) -> List[Tile]:
        """
        Fetch the tiles that make up the given vertex.
        :param v: Vertex in question.
        :return: List of tiles.
        """
        """
        var x = vertex.X; var y = vertex.Y;
        var xoffset = x % 2;
        var yoffset = y % 2;
        return new[]
        {
            Hexes[x-1,(y+xoffset)/2-1],
            Hexes[x-(1-yoffset)*xoffset,(y-1)/2],
            Hexes[x,(y-xoffset)/2],
        };
        """
        xoffset = v.x % 2
        yoffset = v.y % 2
        return [self.tiles[self.offset + v.x][self.offset + (v.y+xoffset)]]

b = Board(5,3)


