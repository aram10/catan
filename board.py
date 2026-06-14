import math
import random
from collections import defaultdict
from typing import List, TYPE_CHECKING, Tuple, Set, Dict, Iterable, Optional
import networkx as nx

import constants
from custom_types import GraphEdge, TileCoords, EdgeCoords, TileGrid, TileData, GraphVertex
from port import Port

if TYPE_CHECKING:
    import player

from constants import Resource
from edge import Edge
from tile import Tile
from vertex import Vertex


def generate_resources_and_chits(num_tiles: int, rng: random.Random = None) -> TileData:
    """
    Creates resource/chit pairs that will be assigned to board tiles.

    :param num_tiles: Number of tiles to get resources/chits.
    :param rng: Optional random.Random instance for determinism.
    :return: List of (resource, chit_value) tuples.
    """
    if rng is None:
        rng = random.Random()
    chits = ([2] + (list(range(3, 7)) + list(range(8, 12))) * 2 + [12]) * ((num_tiles // 19) + 1)
    rng.shuffle(chits)
    base_resources = [Resource.BRICK, Resource.GRAIN, Resource.LUMBER, Resource.ORE, Resource.WOOL]
    resources = base_resources * ((num_tiles // len(base_resources)) + 1)
    rng.shuffle(resources)
    desert_tiles = set(rng.sample(list(range(num_tiles)), max((num_tiles // 10), 1)))
    tile_data = []
    for idx in range(num_tiles):
        tile_data.append((resources.pop(), chits.pop()) if idx not in desert_tiles else (Resource.DESERT, -1))
    return tile_data


def generate_board(n: int) -> Tuple[TileGrid, TileCoords]:
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
        temp = tiles.pop()
        temp.coords = (i, n)
        tile_grid[n][i] = temp
        tile_coords.add((i, n, -i - n))
    # fill in everything above and below center row
    i = 1
    j = n - 1
    while j >= 0:
        tiles_upper = []
        tiles_lower = []
        for k in range(i, 2 * n + 1):
            temp = tiles.pop()
            temp.coords = (k, j)
            tiles_upper.append(temp)
            tile_coords.add((k, j, -k - j))
        tile_grid[j][i:] = tiles_upper
        for k in range(2 * n - i + 1):
            temp = tiles.pop()
            temp.coords = (k, 2 * n - j)
            tiles_lower.append(temp)
            tile_coords.add((k, 2 * n - j, -k - 2 * n + j))
        tile_grid[2 * n - j][:2 * n - i + 1] = tiles_lower
        i += 1
        j -= 1
    return tile_grid, tile_coords


def get_edge_coords_from_tile(tile: Tile) -> EdgeCoords:
    q, r = tile.coords
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

    def __init__(self, board_size: int, rng: random.Random = None):
        # TODO: Cache boards for re-use
        self.board_size = board_size
        self.rng = rng or random.Random()
        num_tiles = 1 + sum([6 * i for i in range(1, board_size + 1)])
        self.tiles, self.tile_coords = generate_board(board_size)
        # models adjacent vertices (i.e., edges)
        self.vertex_graph = nx.Graph()
        # models tile-vertex relations
        self.tile_graph = nx.Graph()
        # holds actual Vertex objects referred to by the graph
        self.vertex_objects = {}
        # only generate resources/chits for non-water tiles
        tile_data = generate_resources_and_chits(num_tiles - 6 * board_size, self.rng)
        remaining_chits = [2, 3, 4, 5, 9, 10, 11, 12]
        for coord in self.tile_coords:
            tile = self.get_tile(coord[0], coord[1])
            # if tile is on outer edge (i.e., water tile), don't give it resource/chit
            if coord[0] == 0 or coord[0] == 2 * board_size or coord[1] == 0 or coord[1] == 2 * board_size or coord[0] + \
                    coord[1] == board_size or coord[0] + coord[1] == 3 * board_size:
                tile.resource = Resource.WATER
            else:
                resource, chit_val = tile_data.pop()
                if resource != Resource.DESERT:
                    # enforce rule that there are no 8-8, 6-6, or 8-6 connections
                    neighbor_rolls = {x.dice_num for x in self.get_neighboring_tiles(tile)}
                    if 6 in neighbor_rolls or 8 in neighbor_rolls:
                        chit_val = self.rng.choices(
                            remaining_chits, weights=constants.CHIT_DIST_MOD, k=1)[0]
                tile.resource = resource
                tile.dice_num = chit_val
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
            tile.vertices = {self.vertex_objects[v] for v in vertices}
        # Note that edges have their own coordinate system while vertices are defined by their incident tiles
        self.edges = [[Edge(i, j) for j in range(2 * num_tiles + 2)] for i in range(2 * num_tiles + 2)]
        # Need to give the tiles, vertices, and edges a canonical ordering
        self.ordered_tiles = [self.get_tile(q, r) for (q, r, _) in sorted(list(self.tile_coords))]
        self.ordered_vertices = [self.vertex_objects[coord] for coord in
                                 sorted(self.vertex_objects, key=lambda coords: min(coords))]
        self.ordered_edges = sorted(self.get_edges(), key=lambda e: e.coords)

    @property
    def num_edges(self):
        return len(self.ordered_edges)

    @property
    def num_tiles(self):
        return len(self.ordered_tiles)

    @property
    def num_vertices(self):
        return len(self.ordered_vertices)

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
        tile_shore = (tile.resource == Resource.WATER)
        for n1 in neighbors:
            n1_shore = (n1.resource == Resource.WATER)
            n1_neighbors = self.get_neighboring_tiles(n1)
            n2_neighbors = list(neighbors.intersection(n1_neighbors))
            assert (len(n2_neighbors) == 2 or len(n2_neighbors) == 1)
            # neighboring tiles share 2 common neighbors (if neither are corner water tiles)
            # defines two vertices connected by an edge - add this connection to the graph
            t1 = n2_neighbors[0]
            t1_shore = (t1.resource == Resource.WATER)
            v1 = frozenset({tile.coords, n1.coords, t1.coords})
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
                t2_shore = (t2.resource == Resource.WATER)
                v2 = frozenset({tile.coords, n1.coords, t2.coords})
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
                attrs[(v1, v2)] = {'obj': shared_edge_coords, 'visited': -1}
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
        port_resources = [Resource.GRAIN, Resource.ORE, Resource.WOOL, Resource.LUMBER, Resource.BRICK,
                          Resource.ANY] * (math.ceil(num_ports / 6) + 1)
        self.rng.shuffle(port_resources)
        # begin initializing the first port
        curr_resource = port_resources.pop()
        curr = shore_vertices[0]
        curr_neighbors = [x for x in self.vertex_graph.neighbors(curr) if self.vertex_graph.nodes[x]['on_shore']]
        assert (len(curr_neighbors) == 2)
        self.vertex_objects[curr] = Port(curr, curr_resource)
        self.vertex_objects[curr_neighbors[0]] = Port(curr_neighbors[0], curr_resource)
        visited[curr] = True
        visited[curr_neighbors[0]] = True
        self.vertex_objects[curr_neighbors[1]] = Vertex(curr_neighbors[1])
        visited[curr_neighbors[1]] = True
        curr = [x for x in self.vertex_graph.neighbors(curr_neighbors[1]) if
                self.vertex_graph.nodes[x]['on_shore'] and not visited[x]]
        assert (len(curr) == 1)
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
            neighbors = [x for x in self.vertex_graph.neighbors(curr) if
                         self.vertex_graph.nodes[x]['on_shore'] and not visited[x]]
            assert (len(neighbors) <= 1)
            if len(neighbors) == 0:
                break
            curr = neighbors[0]

    def longest_road_length(self, player_id: int) -> int:
        """
        Length of the longest continuous road (a trail: no edge reused) built by ``player_id``.

        A road is broken by an opponent's settlement/city: the traversal may end on, but never
        pass through, a vertex owned by another player. The player's road network is tiny
        (<= 15 edges), so an exhaustive DFS over edges is inexpensive.
        """
        adjacency = defaultdict(list)
        for u, v in self.vertex_graph.edges:
            if self.get_edge_from_graph_edge((u, v)).player_road_id == player_id:
                edge_key = frozenset((u, v))
                adjacency[u].append((v, edge_key))
                adjacency[v].append((u, edge_key))
        if not adjacency:
            return 0

        def can_pass_through(vertex_id: GraphVertex) -> bool:
            vertex_obj = self.vertex_objects.get(vertex_id)
            return vertex_obj is None or vertex_obj.player_id in (-1, player_id)

        best = 0

        def dfs(node: GraphVertex, used: set) -> None:
            nonlocal best
            best = max(best, len(used))
            if used and not can_pass_through(node):
                return
            for neighbor, edge_key in adjacency[node]:
                if edge_key not in used:
                    used.add(edge_key)
                    dfs(neighbor, used)
                    used.remove(edge_key)

        for start in list(adjacency):
            dfs(start, set())
        return best

    def get_tile(self, q: int, r: int) -> Tile:
        try:
            return self.tiles[r][q - max(0, self.board_size - (2 * self.board_size + 1 - abs(self.board_size - r)))]
        except IndexError:
            return None

    def get_tiles(self) -> Iterable[Tile]:
        return iter(tile for row in self.tiles for tile in row if tile is not None)

    def get_edges(self) -> Iterable[Edge]:
        return iter(self.get_edge_from_graph_edge(edge) for edge in self.vertex_graph.edges)

    def get_vertices(self) -> Iterable[Vertex]:
        return iter(self.vertex_objects[x] for x in self.vertex_objects.keys())

    def get_neighboring_tiles(self, tile: Tile) -> Set[Tile]:
        res = set()
        q, r = tile.coords
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

    def get_edges_from_vertex(self, vertex: Vertex) -> List[Edge]:
        v_id = vertex.vertex_id
        res = []
        for x in self.vertex_graph.adj[v_id]:
            i, j = self.vertex_graph.get_edge_data(v_id, x)['obj']
            res.append(self.edges[i][j])
        return res

    def get_tiles_with_chit(self, chit: int) -> List[Tile]:
        """
        Gets all board tiles that have a given chit value.
        :param chit: The chit value.
        :return: A list of tiles.
        """
        res = []
        for tile in self.get_tiles():
            if tile.dice_num == chit:
                res.append(tile)
        return res

    def fetch_random_tile(self) -> Tile:
        """
        Temporary method for choosing robber position.
        """
        q = self.rng.randint(0, 2 * self.board_size)
        r = self.rng.randint(0, 2 * self.board_size)
        while (tile := self.get_tile(q, r)) is None:
            q = self.rng.randint(0, 2 * self.board_size)
            r = self.rng.randint(0, 2 * self.board_size)
        return tile

    def get_desert_tiles(self) -> Set[Tile]:
        tiles = set()
        for tile in self.get_tiles():
            if tile.resource == Resource.DESERT:
                tiles.add(tile)
        return tiles

    def get_tiles_from_vertex(self, v: Vertex) -> Set[Tile]:
        return set(self.tile_graph.adj[v.vertex_id])

    def get_vertices_from_tile(self, t: Tile) -> Set[Vertex]:
        return set(self.vertex_objects[x] for x in self.tile_graph.adj[t])

    def vertices_are_adjacent(self, v1: Vertex, v2: Vertex) -> bool:
        return v1.vertex_id in self.vertex_graph.neighbors(v2.vertex_id)

    def get_edge_from_graph_edge(self, graph_edge: GraphEdge) -> Edge:
        i, j = self.vertex_graph.get_edge_data(graph_edge[0], graph_edge[1])['obj']
        return self.edges[i][j]

    def get_graph_edge_from_edge(self, edge: Edge) -> Optional[GraphEdge]:
        i, j = edge.coords
        graph_edge = [(u, v) for u, v, e in self.vertex_graph.edges(data=True) if e['obj'] == (i, j)]
        if len(graph_edge) == 0:
            return None
        return graph_edge[0]

    def get_vertices_from_edge(self, edge: Edge) -> Tuple[Vertex, Vertex]:
        v1, v2 = self.get_graph_edge_from_edge(edge)
        return self.vertex_objects[v1], self.vertex_objects[v2]
