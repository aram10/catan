import uuid

from constants import RESOURCE, PLAYERCOLOR
from edge import Edge
from vertex import Vertex
from board import get_edges_from_vertex


class Player:

    def __init__(self, player_id: int, color: PLAYERCOLOR, available_settlements: int = 5):
        self.id = player_id
        self.color = color
        self.available_settlements = available_settlements
        # resources (BRICK, GRAIN, LUMBER, ORE, WOOD)
        self.resources = [0, 0, 0, 0, 0]
        self.victory_points = 0
        self.settlements = 0
        self.cities = 0
        self.buildings = set()

    def get_resource_count(self, r: RESOURCE):
        return self.resources[r.value]

    def handle_roll(self, roll: int):
        """
        Invoked whenever the dice are rolled. Handles resource production for this player.
        :param roll: The dice roll.
        """
        raise NotImplementedError()

    def can_build(self, vertex: Vertex) -> bool:
        """
        False if the player may not build on this vertex due to the distance rule, no connecting road, or another
        building, and true otherwise.
        :param vertex: Spot to be built on.
        :return: Whether the player may build here.
        """
        edges = [get_edges_from_vertex(vertex)]


    def can_build_settlement(self) -> bool:
        """
        True if this player is able to build a settlement and false otherwise.
        """
        return (self.resources[RESOURCE.BRICK] >= 1
                and self.resources[RESOURCE.LUMBER] >= 1
                and self.resources[RESOURCE.GRAIN] >= 1
                and self.resources[RESOURCE.WOOL] >= 1
                and self.settlements < self.available_settlements)

    def can_build_city(self) -> bool:
        """
        True if this play is able to build a city and false otherwise.
        """
        return self.resources[RESOURCE.GRAIN] >= 2 and self.resources[RESOURCE.ORE] >= 3 and self.settlements >= 1

    def build_road(self, edge: Edge):
        raise NotImplementedError()

    def build_settlement(self, vertex: Vertex):
        vertex.set_player_id(self.id)
        self.settlements += 1
        self.victory_points += 1
        self.resources[RESOURCE.BRICK] -= 1
        self.resources[RESOURCE.LUMBER] -= 1
        self.resources[RESOURCE.GRAIN] -= 1
        self.resources[RESOURCE.WOOL] -= 1

    def build_city(self, vertex: Vertex):
        vertex.upgrade_to_city()
        self.settlements -= 1
        self.cities += 1
        # lose a settlement, gain a city
        self.victory_points += 1
        self.resources[RESOURCE.GRAIN] -= 2
        self.resources[RESOURCE.ORE] -= 3
