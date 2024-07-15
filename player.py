import random
import uuid
from collections import defaultdict
from typing import List, Optional, Dict, Set
from abc import ABC, abstractmethod

import numpy as np

from constants import RESOURCE, PLAYERCOLOR, MAX_TRADE_PROPOSALS
from edge import Edge
from game_window import GameWindow
from port import Port
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
        # resources [BRICK, GRAIN, LUMBER, ORE, WOOL]
        self.resources = [0] * 5
        # development cards [Knight, Monopoly, RoadBuilding, VictoryPoint, YearOfPlenty]
        self.dev_cards = [0] * 6
        self.victory_points = 0
        self.settlements = 0
        self.roads = 0
        self.cities = 0
        self.buildings = set()
        self.has_largest_army = False
        self.has_longest_road = False
        self.first_settlement = None
        self.second_settlement = None
        self.available_exchange_resources: Dict[RESOURCE, bool] = {
            RESOURCE.BRICK: False,
            RESOURCE.GRAIN: False,
            RESOURCE.LUMBER: False,
            RESOURCE.ORE: False,
            RESOURCE.WOOL: False,
            RESOURCE.ANY: False
        }
        # computer agents do discards sequentially, so need to know when to stop discarding
        self.start_of_turn_hand_count = 0
        self.start_of_turn_dev_card_count = 0

    def resource_count(self, r: RESOURCE):
        return self.resources[r.value]

    def total_resource_count(self):
        return sum(self.resources)

    def total_dev_card_count(self):
        return sum(self.dev_cards)

    def get_random_available_resource(self) -> Optional[RESOURCE]:
        """
        Returns a random resource type that this player has for the purposes of stealing.
        """
        if sum(self.resources) == 0:
            return None
        return random.choice([RESOURCE(i) for i in range(5) if self.resources[i] > 0])

    def available_exchanges(self) -> List[bool]:
        # [brick, grain, lumber, ore, wool]
        res = [False] * 5
        res[0] = self.resources[RESOURCE.BRICK] >= 4 \
                 or (self.resources[RESOURCE.BRICK] >= 3 and self.available_exchange_resources[RESOURCE.ANY]) \
                 or (self.available_exchange_resources[RESOURCE.BRICK] and self.resources[RESOURCE.BRICK] >= 2)
        res[1] = self.resources[RESOURCE.GRAIN] >= 4 \
                 or (self.resources[RESOURCE.GRAIN] >= 3 and self.available_exchange_resources[RESOURCE.ANY]) \
                 or (self.available_exchange_resources[RESOURCE.GRAIN] and self.resources[RESOURCE.GRAIN] >= 2)
        res[2] = self.resources[RESOURCE.LUMBER] >= 4 \
                 or (self.resources[RESOURCE.LUMBER] >= 3 and self.available_exchange_resources[RESOURCE.ANY]) \
                 or (self.available_exchange_resources[RESOURCE.LUMBER] and self.resources[RESOURCE.LUMBER] >= 2)
        res[3] = self.resources[RESOURCE.ORE] >= 4 \
                 or (self.resources[RESOURCE.ORE] >= 3 and self.available_exchange_resources[RESOURCE.ANY]) \
                 or (self.available_exchange_resources[RESOURCE.ORE] and self.resources[RESOURCE.ORE] >= 2)
        res[4] = self.resources[RESOURCE.WOOL] >= 4 \
                 or (self.resources[RESOURCE.WOOL] >= 3 and self.available_exchange_resources[RESOURCE.ANY]) \
                 or (self.available_exchange_resources[RESOURCE.WOOL] and self.resources[RESOURCE.WOOl] >= 2)

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

    def can_buy_dev_card(self) -> bool:
        return self.resources[RESOURCE.GRAIN] >= 1 and self.resources[RESOURCE.WOOL] >= 1 and self.resources[
            RESOURCE.ORE] >= 1

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
        if isinstance(vertex, Port):
            self.available_exchange_resources[vertex.resource] = True

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
        Returns a mask where the ith position is true if the agent is capable of taking the associated actions. They are:
            -(1) Buy Development Card
            -(2) Discard Resource
            -(3) End Turn
            -(4) Exchange Resource
            -(5) Move Robber
            -(6) Place Road
            -(7) Place Settlement
            -(8) Play Development Card
            -(9) Propose Trade
            -(10) Respond To Trade
            -(11) Roll Dice
            -(12) Steal Resource
            -(13) Upgrade to City
        """
        mask = np.zeros(13)

        # has_to_discard
        mask[1] = self.game.seven_rolled_this_turn \
                  and (y := self.player.start_of_turn_hand_count) > 7 \
                  and self.player.total_resource_count() > y - y // 2

        if self.game.current_turn_idx == self.player.id:
            # roll dice
            mask[10] = not self.game.dice_rolled_this_turn

            # move robber
            mask[4] = self.game.seven_rolled_this_turn \
                      and not self.game.robber_moved_this_turn

            # steal
            mask[11] = self.game.robber_moved_this_turn \
                       and not self.game.stole_this_turn

            if not mask[10] and not mask[5] and not mask[11]:
                # end turn
                mask[2] = True

                # buy dev card
                mask[0] = self.player.can_buy_dev_card()

                # exchange resource
                mask[3] = len(self.game.get_available_road_spots(self.player.id)) > 0

                # build road
                mask[5] = self.player.can_build_road() \
                          and len(self.game.get_available_road_spots(self.player.id)) > 0

                # build settlement
                mask[6] = self.player.can_build_settlement() \
                          and len(self.game.get_available_settlement_spots(self.player.id)) > 0

                # play dev card
                mask[7] = self.player.total_dev_card_count() > self.player.start_of_turn_dev_card_count

                # propose trade
                mask[8] = self.game.trades_proposed_this_turn < MAX_TRADE_PROPOSALS

                # upgrade to city
                mask[12] = self.player.can_build_settlement()
        else:
            # respond to trade
            mask[9] = self.game.current_trade_on_table is not None \
                      and self.game.current_trade_on_table[1] == self.player.id

        return mask

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
