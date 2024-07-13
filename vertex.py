from typing import Set, Tuple

from custom_types import GraphVertex


class Vertex:

    def __init__(self, vertex_id: GraphVertex):
        """
        Vertex uniquely identified by coordinates of its incident tiles.
        """
        self.vertex_id = vertex_id
        self.player_id = -1
        self.is_city = False
        # used for drawing the game
        self.canvas_pos = None

    def __hash__(self):
        return hash(self.vertex_id)

    def upgrade_to_city(self) -> bool:
        self.is_city = True
