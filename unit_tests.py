import unittest

from board import Board


class TestTileAndEdgeNeighbors(unittest.TestCase):

    def test_tile_neighbors(self):
        b = Board(3)
        for tile in b.get_tiles():
            tile_set = b.get_neighboring_tiles(tile)
            neighbors = set.intersection(*[b.get_neighboring_tiles(t) for t in tile_set])
            self.assertTrue(len(neighbors) == 1 and list(neighbors)[0] == tile)

    def test_tile_edges(self):
        b = Board(3)
        flag = True
        tiles = b.get_tiles()
        for tile in tiles:
            edge_set = b.get_edges_from_tile(tile)
            tile_set = b.get_neighboring_tiles(tile)
            try:
                self.assertTrue(all([len(edge_set.intersection(b.get_edges_from_tile(n))) == 1 for n in tile_set]))
            except AssertionError:
                flag = False
                coords = str(tile.get_coords())
                print(f"Inconsistency with tile {coords}.")
                print("="*50)
                print(f"Tile {coords} has neighbors {str([t.get_coords() for t in list(tile_set)])} and edges {str([e.get_coords() for e in edge_set])}.")
                for neighbor in tile_set:
                    neighbor_coords = str(neighbor.get_coords())
                    neighbor_edges = b.get_edges_from_tile(neighbor)
                    print(f"Tile {neighbor_coords}'s edges are: {str([e.get_coords() for e in neighbor_edges])}.")
                    print(f"Tile {coords} shares edges {str([e.get_coords() for e in edge_set.intersection(neighbor_edges)])} with tile {neighbor_coords}.")
                print("="*50)
                print('\n')
        self.assertTrue(flag)

    def test_tile_vertices(self):
        b = Board(3)
        flag = True
        tiles = b.get_tiles()
        for tile in tiles:
            vertex_set = tile.get_vertices()
            neighbor_tile_set = set.intersection(*[b.get_tiles_from_vertex(v) for v in vertex_set])
            try:
                if not (len(neighbor_tile_set) == 1 and list(neighbor_tile_set)[0] == tile):
                    # edge case for corner water tiles because we don't create vertices that aren't used in play
                    self.assertTrue(len(neighbor_tile_set) == 2 and len(b.get_neighboring_tiles(tile)) == 3 and tile in neighbor_tile_set)
            except AssertionError:
                flag = False
                coords = str(tile.get_coords())
                neighboring_tiles = b.get_neighboring_tiles(tile)
                print(f"Inconsistency with tile {coords}.")
                print("="*50)
                print(f"Tile {coords} has neighbors {str([t.get_coords() for t in list(neighboring_tiles)])} and vertices {str([v.vertex_id for v in vertex_set])}.")
                for neighbor in neighboring_tiles:
                    neighbor_coords = str(neighbor.get_coords())
                    neighbor_vertices = b.get_vertices_from_tile(neighbor)
                    print(f"Tile {neighbor_coords}'s vertices are: {str([v.vertex_id for v in neighbor_vertices])}.")
                    print(f"Tile {coords} shares vertices {str([v.vertex_id for v in vertex_set.intersection(neighbor_vertices)])} with tile {neighbor_coords}.")
                print("="*50)
                print('\n')
        self.assertTrue(flag)
