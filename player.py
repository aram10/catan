import random
import uuid
from typing import List, Optional
from abc import ABC, abstractmethod

from constants import RESOURCE, PLAYERCOLOR
from edge import Edge
from game_window import GameWindow
from tile import Tile
from vertex import Vertex


class Player:

    def __init__(self, player_id: int, color: PLAYERCOLOR, available_settlements: int = 5, available_roads: int = 15,
                 available_cities: int = 4):
        self.id = player_id
        self.color = color
        self.available_settlements = available_settlements
        self.available_roads = available_roads
        self.available_cities = available_cities
        # resources (BRICK, GRAIN, LUMBER, ORE, WOOD)
        self.resources = [0, 0, 0, 0, 0]
        self.victory_points = 0
        self.settlements = 0
        self.roads = 0
        self.cities = 0
        self.buildings = set()
        self.has_largest_army = False
        self.has_longest_road = False
        self.first_settlement = None
        self.second_settlement = None

    def take_turn(self, game: 'Game'):
        pass

    def handle_roll(self, roll: int):
        """
        Invoked whenever the dice are rolled. Handles resource production for this player.
        :param roll: The dice roll.
        """
        pass

    def select_tile_for_robber(self, game: 'Game') -> Tile:
        return game.board.fetch_random_tile()

    def select_player_to_steal_from(self, game: 'Game', tile: Tile) -> 'Player':
        return random.choice(game.get_players_on_tile(tile))

    def select_road_building_spot(self, game: 'Game', available_spots: List[Edge]) -> Edge:
        return random.choice(available_spots)

    def select_year_of_plenty_resource(self, game: 'Game') -> RESOURCE:
        return RESOURCE(random.choice(range(5)))

    def select_monopoly_resource(self, game: 'Game') -> RESOURCE:
        return RESOURCE(random.choice(range(5)))

    def get_player_id(self) -> int:
        return self.id

    def get_resource_counts(self) -> List[int]:
        return self.resources

    def get_resource_count(self, r: RESOURCE):
        return self.resources[r.value]

    def get_random_available_resource(self) -> Optional[RESOURCE]:
        """
        Returns a random resource type that this player has for the purposes of stealing.
        """
        if sum(self.resources) == 0:
            return None
        return random.choice([RESOURCE(i) for i in range(5) if self.resources[i] > 0])

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
        return self.resources[RESOURCE.GRAIN] >= 2 and self.resources[
            RESOURCE.ORE] >= 3 and self.settlements >= 1 and self.cities < self.available_cities

    def can_build_road(self) -> bool:
        return self.resources[RESOURCE.BRICK] >= 1 and self.resources[
            RESOURCE.LUMBER] >= 1 and self.roads < self.available_roads

    def build_road(self, edge: Edge):
        edge.set_player_road_id(self.id)
        self.roads += 1
        self.resources[RESOURCE.BRICK] -= 1
        self.resources[RESOURCE.LUMBER] -= 1

    def place_road(self, edge: Edge):
        # used for initial road building at start of game
        edge.set_player_road_id(self.id)
        self.roads += 1

    def build_settlement(self, vertex: Vertex):
        vertex.set_player_id(self.id)
        self.settlements += 1
        self.victory_points += 1
        self.resources[RESOURCE.BRICK] -= 1
        self.resources[RESOURCE.LUMBER] -= 1
        self.resources[RESOURCE.GRAIN] -= 1
        self.resources[RESOURCE.WOOL] -= 1

    def place_settlement(self, vertex: Vertex):
        vertex.set_player_id(self.id)
        self.settlements += 1
        self.victory_points += 1

    def build_city(self, vertex: Vertex):
        vertex.upgrade_to_city()
        self.settlements -= 1
        self.cities += 1
        # lose a settlement, gain a city
        self.victory_points += 1
        self.resources[RESOURCE.GRAIN] -= 2
        self.resources[RESOURCE.ORE] -= 3

    def give_largest_army(self):
        self.has_largest_army = True
        self.victory_points += 2

    def remove_largest_army(self):
        self.has_largest_army = False
        self.victory_points -= 2

    def give_longest_road(self):
        self.has_longest_road = True
        self.victory_points += 2

    def remove_longest_road(self):
        self.has_longest_road = False
        self.victory_points -= 2

    def give_resource(self, resource: RESOURCE, amt: int):
        self.resources[resource] += amt

    def take_resource(self, resource: RESOURCE, amt: int):
        self.resources[resource] -= amt

    def get_available_resources(self) -> set[RESOURCE]:
        resources = set()
        for i in range(5):
            if self.resources[i] > 0:
                resources.add(RESOURCE(i))
        return resources

    def give_victory_points(self, amt: int):
        self.victory_points += amt

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Player) and self.id == other.get_player_id()


class VisualPlayer(Player):
    """
    Player class that interacts with tkinter Canvas to render building a settlement/city/road and moving the robber
    """

    def __init__(self, player_id: int, color: PLAYERCOLOR, gw: GameWindow, available_settlements: int = 5,
                 available_roads: int = 15, available_cities: int = 4):
        super().__init__(self, player_id, color, available_settlements, available_roads, available_cities)
        self.gw = gw

    def build_city(self, vertex: Vertex):
        Player.build_city(self, vertex)
        self.gw.draw_settlement(vertex, self.color)
