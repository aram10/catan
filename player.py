import random
import uuid
from typing import List, Optional
from abc import ABC, abstractmethod

import numpy as np

from constants import RESOURCE, PLAYERCOLOR
from edge import Edge
from game_window import GameWindow
from tile import Tile
from vertex import Vertex


class Player:
    """
    Anyone playing Catan, human or otherwise, extends the Player class, which tracks and manages the
    points/cards/resources of a player.
    """

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

    def resource_count(self, r: RESOURCE):
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
        edge.player_road_id = self.id
        self.roads += 1
        self.resources[RESOURCE.BRICK] -= 1
        self.resources[RESOURCE.LUMBER] -= 1

    def place_road(self, edge: Edge):
        # used for initial road building at start of game
        edge.player_road_id = self.id
        self.roads += 1

    def build_settlement(self, vertex: Vertex):
        vertex.player_id = self.id
        self.settlements += 1
        self.victory_points += 1
        self.resources[RESOURCE.BRICK] -= 1
        self.resources[RESOURCE.LUMBER] -= 1
        self.resources[RESOURCE.GRAIN] -= 1
        self.resources[RESOURCE.WOOL] -= 1

    def place_settlement(self, vertex: Vertex):
        vertex.player_id = self.id
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
        return isinstance(other, Player) and self.id == other.id


class Mask:
    """
    Abstracts away the logic of creating action masks, which prevent agents from taking disallowed actions.
    """

    def __init__(self, player: Player, game: 'Game'):
        self.player = player
        self.game = game

    def action_type_mask(self) -> np.array:
        """
        Possible actions:
            -Buy Development Card
                > it is player's turn
                > player has at least 1 grain, 1 wool, and 1 ore
                > player does not have to roll dice, discard, move robber, or steal
            -Discard Resource
                > player has a non-empty hand
                > a 7 was rolled on this turn
                > player's hand count at the start of this turn, x, is >= 8
                > player's current resource count is greater than ceil(x/2)
            -End Turn
                > it is player's turn
                > player does not have to roll dice, discard, move robber, or steal
            -Exchange Resource
                > it is player's turn
                > player has at least 1 type of resource that can be exchanged with the bank or at a port
                > player does not have to roll dice, discard, move robber, or steal
            -Move Robber
                > it is player's turn
                > a 7 was rolled on this turn
                > player does not have to roll dice or discard
            -Place Road
                > it is player's turn
                > player has at least 1 lumber and 1 brick
                > the set of available road spots is nonempty
                > player does not have to roll dice, discard, move robber, or steal
            -Place Settlement
                > it is player's turn
                > player has at least 1 lumber, 1 brick, 1 grain, and 1 wool
                > the set of available settlement spots is nonempty
                > the player has less than 5 settlements on the board
                > player does not have to roll dice, discard, move robber, or steal
            -Play Development Card
                > it is player's turn
                > player has bought x dev cards this turn and has > x dev cards
                > player does not have to roll dice, discard, move robber, or steal
            -Propose Trade
                > it is player's turn
                > player's resource count is nonzero
                > there have been < MAX_TRADE_PROPOSALS trades proposed this turn
                > player does not have to roll dice, discard, move robber, or steal
            -Respond To Trade
                > it is NOT player's turn
                > a trade was proposed to this player
            -Roll Dice
                > it is player's turn
                > the dice have not been rolled yet this turn
            -Steal Resource
                > it is player's turn
                > the robber was moved this turn
                > player has yet to steal this turn
            -Upgrade to City
                > it is player's turn
                > player has at least 1 settlement
                > player has at least 2 grain and 3 ore
        """
        mask = np.zeros(13)
        pass

    def city_mask(self):
        """
        Mask out all vertices that this player can't place a city on.
        """
        raise NotImplementedError()

    def dev_card_mask(self):
        """
        Mask out all dev cards that this player can't play.
        """
        raise NotImplementedError()

    def exchange_mask(self):
        """
        Mask out all resources that this player can't exchange with the bank for another.
        """
        raise NotImplementedError()

    def in_bank_mask(self):
        """
        Mask out all resources that aren't in the bank.
        """
        raise NotImplementedError()

    def in_hand_mask(self):
        """
        Mask out all resources that aren't in this player's hand.
        """
        raise NotImplementedError()

    def road_mask(self):
        """
        Mask out all edges that this player can't place a road on.
        """
        raise NotImplementedError()

    def robber_mask(self):
        """
        Mask out all tiles that this player can't place the robber on.
        """
        raise NotImplementedError()

    def settlement_mask(self):
        """
        Mask out all vertices that this player can't place a settlement on.
        """
        raise NotImplementedError()

    def steal_from_mask(self):
        """
        Mask out all players that this player can't steal from.
        """
        raise NotImplementedError()

    def trade_response_mask(self, proposed_trade):
        """
        Mask out 'yes' if this player is unable to accept the proposed trade.
        """
        raise NotImplementedError()


class Agent(ABC):
    """
    In lieu of human input via the GUI, the Agent class is an interface by which a computer player plays the game.
    """

    def __init__(self, player: Player, game: 'Game'):
        self.player = player
        self.game = game
        self.mask = Mask(player, game)

    @abstractmethod
    def take_turn(self, observation):
        ...


class RandomAgent(Agent):
    """
    An agent that can fully play the game, but makes every choice at random.
    """

    def take_turn(self, observation):
        raise NotImplementedError()


class VisualPlayer(Player):
    """
    Player class that interacts with tkinter Canvas to render building a settlement/city/road and moving the robber
    """

    def __init__(self, player_id: int, color: PLAYERCOLOR, gw: GameWindow, available_settlements: int = 5,
                 available_roads: int = 15, available_cities: int = 4):
        super().__init__(self, player_id, color, available_settlements, available_roads, available_cities)
        self.gw = gw

    def build_road(self, edge: Edge):
        super().build_road(edge)
        self.gw.draw_road(edge.canvas_pos)

    def build_settlement(self, vertex: Vertex):
        super().build_settlement(vertex)
        self.gw.draw_settlement(vertex.canvas_pos)

    def build_city(self, vertex: Vertex):
        super().build_city(vertex)
        self.gw.draw_city(vertex.canvas_pos)


class UserVisualPlayer(VisualPlayer):
    """
    The special VisualPlayer object associated with the human user. Updates the text and the buttons in the GUI.
    """
    pass
