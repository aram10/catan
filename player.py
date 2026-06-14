import random
from abc import ABC, abstractmethod

import numpy as np

from constants import Resource, PlayerColor
from edge import Edge
from port import Port
from trade import TradeProposal
from vertex import Vertex


class Player:
    """Tracks and manages points/cards/resources of a Catan player."""

    def __init__(self, player_id: int, color: PlayerColor, available_settlements: int = 5,
                 available_roads: int = 15, available_cities: int = 4):
        self.id = player_id
        self.color = color
        self.available_settlements = available_settlements
        self.available_roads = available_roads
        self.available_cities = available_cities
        self.resources = [0] * 5  # [BRICK, GRAIN, LUMBER, ORE, WOOL]
        self.dev_cards = [0] * 5  # [Knight, RoadBuilding, YearOfPlenty, Monopoly, VictoryPoint]
        self.victory_points = 0
        self.settlements = 0
        self.roads = 0
        self.cities = 0
        self.buildings = set()
        self.has_largest_army = False
        self.has_longest_road = False
        self.knights_played = 0
        self.first_settlement_played = False
        self.resource_exchange_rate = {
            Resource.BRICK: 4, Resource.GRAIN: 4, Resource.LUMBER: 4,
            Resource.ORE: 4, Resource.WOOL: 4, Resource.ANY: 4
        }
        self.start_of_turn_hand_count = 0
        self.start_of_turn_dev_card_count = 0

    def resource_count(self, r: Resource):
        return self.resources[r.value]

    def total_resource_count(self):
        return sum(self.resources)

    def total_dev_card_count(self):
        return sum(self.dev_cards)

    def get_random_available_resource(self, rng: random.Random):
        """Returns a random resource type this player has, or None if empty."""
        available = [Resource(i) for i in range(5) if self.resources[i] > 0]
        if not available:
            return None
        return rng.choice(available)

    def can_build_settlement(self) -> bool:
        r = self.resources
        return (r[Resource.BRICK] >= 1 and r[Resource.LUMBER] >= 1
                and r[Resource.GRAIN] >= 1 and r[Resource.WOOL] >= 1
                and self.settlements < self.available_settlements)

    def can_build_city(self) -> bool:
        return (self.resources[Resource.GRAIN] >= 2 and self.resources[Resource.ORE] >= 3
                and self.settlements >= 1 and self.cities < self.available_cities)

    def can_build_road(self) -> bool:
        return (self.resources[Resource.BRICK] >= 1 and self.resources[Resource.LUMBER] >= 1
                and self.roads < self.available_roads)

    def can_buy_dev_card(self) -> bool:
        r = self.resources
        return r[Resource.GRAIN] >= 1 and r[Resource.WOOL] >= 1 and r[Resource.ORE] >= 1

    def build_road(self, edge: Edge):
        edge.player_road_id = self.id
        self.roads += 1
        self.resources[Resource.BRICK] -= 1
        self.resources[Resource.LUMBER] -= 1

    def place_road(self, edge: Edge):
        """Place road during setup (no resource cost)."""
        edge.player_road_id = self.id
        self.roads += 1

    def build_settlement(self, vertex: Vertex):
        vertex.player_id = self.id
        self.settlements += 1
        self.victory_points += 1
        self.resources[Resource.BRICK] -= 1
        self.resources[Resource.LUMBER] -= 1
        self.resources[Resource.GRAIN] -= 1
        self.resources[Resource.WOOL] -= 1
        if isinstance(vertex, Port):
            self._apply_port(vertex)

    def _apply_port(self, port: Port):
        """Update exchange rates based on acquired port."""
        if port.resource == Resource.ANY:
            for i in range(5):
                self.resource_exchange_rate[Resource(i)] = min(
                    self.resource_exchange_rate[Resource(i)], port.ratio)
        else:
            self.resource_exchange_rate[port.resource] = min(
                self.resource_exchange_rate[port.resource], port.ratio)

    def place_settlement(self, vertex: Vertex):
        vertex.player_id = self.id
        self.settlements += 1
        self.victory_points += 1

    def build_city(self, vertex: Vertex):
        vertex.upgrade_to_city()
        self.settlements -= 1
        self.cities += 1
        self.victory_points += 1
        self.resources[Resource.GRAIN] -= 2
        self.resources[Resource.ORE] -= 3

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

    def give_resource(self, resource: Resource, amt: int):
        self.resources[resource] += amt

    def take_resource(self, resource: Resource, amt: int):
        if self.resources[resource] < amt:
            raise ValueError(
                f"Player {self.id} cannot give up {amt} of {resource.name}; only has {self.resources[resource]}")
        self.resources[resource] -= amt

    def give_victory_points(self, amt: int):
        self.victory_points += amt

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Player) and self.id == other.id


class Mask:
    """Creates action masks to prevent agents from taking disallowed actions."""

    def __init__(self, player: Player, game: 'Game'):
        self.player = player
        self.game = game

    def action_type_mask(self) -> np.array:
        """
        Top-level gate over action types, indexed by ActionType.value (see actions.py).
        Derived from get_legal_actions so legality has a single source of truth. The
        per-target Mask methods (settlement_mask, road_mask, city_mask, robber_mask, ...)
        then refine each enabled type.
        """
        mask = np.zeros(13)
        legal_actions = self.game.get_legal_actions(self.player.id)
        for action in legal_actions:
            mask[action.action_type.value] = 1.0
        return mask

    def city_mask(self):
        """Mask vertices where this player can place a city (own settlements, not already cities)."""
        return np.array([v.player_id == self.player.id and not v.is_city
                         for v in self.game.board.ordered_vertices], dtype=float)

    def dev_card_mask(self):
        """Mask playable dev cards (owned minus those bought this turn). Index 4 (VP) always 0."""
        return np.array([self.player.dev_cards[i] - self.game.num_dev_cards_bought_this_turn[i] > 0
                         if i < 4 else False
                         for i in range(5)], dtype=float)

    def exchange_mask(self):
        """Mask resources this player can exchange with the bank."""
        return np.array([self.player.resources[i] >= self.player.resource_exchange_rate[Resource(i)]
                         for i in range(5)], dtype=float)

    def in_bank_mask(self):
        """Mask resources available in the bank."""
        return np.array([self.game.remaining_resource(Resource(i)) > 0
                         for i in range(5)], dtype=float)

    def in_hand_mask(self):
        """Mask resources in this player's hand."""
        return np.array([self.player.resources[i] > 0 for i in range(5)], dtype=float)

    def road_mask(self):
        """Mask edges where this player can place a road."""
        avail = set(self.game.get_available_road_spots(self.player.id))
        edges = self.game.board.ordered_edges
        return np.array([e in avail for e in edges], dtype=float)

    def robber_mask(self):
        """Mask tiles where the robber can be moved (not water, not current robber tile)."""
        robber_tile = self.game.robber_tile
        return np.array([not (t == robber_tile or t.resource == Resource.WATER)
                         for t in self.game.board.ordered_tiles], dtype=float)

    def settlement_mask(self):
        """Mask vertices where this player can place a settlement."""
        avail = set(self.game.get_available_settlement_spots(self.player.id))
        return np.array([v in avail for v in self.game.board.ordered_vertices], dtype=float)

    def steal_from_mask(self):
        """Mask players this player can steal from (on robber tile, have resources, not self)."""
        players_on_tile = self.game.get_players_on_tile(self.game.robber_tile)
        mask = np.zeros(self.game.num_players)
        for p in players_on_tile:
            if p.id != self.player.id and p.total_resource_count() > 0:
                mask[p.id] = 1
        return mask

    def trade_response_mask(self, proposed_trade: TradeProposal):
        """
        Mask out 'yes' if this player is unable to accept the proposed trade.
        """
        return np.array([int(proposed_trade.is_trade_possible), 1])


class Agent(ABC):
    """Interface for computer players."""

    def __init__(self, player: Player, game: 'Game'):
        self.player = player
        self.game = game
        self.mask = Mask(player, game)

    @abstractmethod
    def choose_action(self, legal_actions: list) -> 'Action':
        """Given a list of legal Action objects, choose one to play."""
        ...


class RandomAgent(Agent):
    """Picks uniformly at random from legal actions."""

    def choose_action(self, legal_actions: list) -> 'Action':
        if not legal_actions:
            return None
        return self.game.rng.choice(legal_actions)
