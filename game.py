from collections import defaultdict
import random
from typing import List, Optional, Tuple, Set

from networkx import Graph

from board import Board
from constants import PlayerColor, Development, Resource
from edge import Edge
from game_window import GameWindow
from player import Player, Agent
from tile import Tile
from vertex import Vertex
from exceptions import FailedBuildError


class Game:

    def __init__(self, six_players=False):
        self.players = [Player(i, PlayerColor(i)) for i in range(4)]
        if six_players:
            self.board = Board(4)
            for i in range(4, 6):
                self.players.append(Player(i, PlayerColor(i)))
        else:
            self.board = Board(3)
        self.agents = {}
        for player in self.players[1:]:
            self.agents[player.id] = Agent(player, self)
        self.num_players = len(self.players)

        self.robber_tile = random.choice(list(self.board.get_desert_tiles()))
        self.player_buildings = defaultdict(set)
        self.player_roads = defaultdict(set)
        self.resource_cards = [19] * 5
        self.development_cards = [Development.KNIGHT] * 14 + [Development.ROAD_BUILDING] * 2 + [
            Development.YEAR_OF_PLENTY] * 2 + [Development.MONOPOLY] * 2 + [Development.VICTORY_POINT] * 5
        random.shuffle(self.development_cards)
        self.dev_card_idx = 0

        # turn logic
        # the user of the GUI is always player 0
        self.current_turn_idx = 0
        self.turn_order = list(range(self.num_players))
        random.shuffle(self.turn_order)
        self.dice_rolled_this_turn = False
        self.robber_moved_this_turn = False
        self.stole_this_turn = False
        self.seven_rolled_this_turn = False
        self.dev_card_played_this_turn = False
        self.num_dev_cards_bought_this_turn = [0] * 5
        self.trades_proposed_this_turn = 0
        # (from, to)
        self.current_trade_on_table: Optional[Tuple[int, int]] = None

        # setup turn logic (only for beginning phase)
        self.current_setup_turn_idx = 0
        self.setup_turn_order = self.turn_order + self.turn_order[::-1]
        self.is_game_start = True

    @property
    def current_turn(self):
        return self.turn_order[self.current_turn_idx] if not self.is_game_start else self.setup_turn_order[
            self.current_setup_turn_idx]

    @property
    def remaining_dev_cards(self):
        return 25 - self.dev_card_idx

    def remaining_resource(self, resource: Resource):
        return self.resource_cards[resource]

    def dispense_resource(self, resource: Resource, amt: int):
        assert amt <= self.resource_cards[resource], f"Withdrawing too much {resource}"
        self.resource_cards[resource] -= amt

    def roll(self, player: Player):
        """
        Rolls both dice, and notifies all Player objects of the outcome.
        """
        roll = random.randrange(1, 7) + random.randrange(1, 7)
        if roll == 7:
            # TODO: Allow player to choose robber spot and player to rob
            tile = self.board.fetch_random_tile()
            self.robber_tile.robber = False
            tile.robber = True
            self.robber_tile = tile
            player2 = random.choice(self.get_players_on_tile(tile))
            player2_resource = random.choice(player2.get_available_resources())
            player2.take_resource(player2_resource, 1)
            player.give_resource(player2_resource, 1)
        else:
            producing_tiles = self.board.get_tiles_with_chit(roll)
            self.pay_out_resources(producing_tiles)

        # TODO: Need to allow player to actually take turn

    def pay_out_resources(self, producing_tiles: List[Tile]):
        """
        This method causes every tile not occupied by the robber to produce resources for the players with properties on
        its vertices. The bank may not have enough of a particular resource to pay out what is owed. Suppose there is
        not enough of resource R to pay out all players. If only 1 player is due to collect resource R this turn, that
        player receives the remainder of resource R in the bank. Otherwise, nobody receives any of resource R.
        """
        resource_count = [0]*5
        resource_payout = [[0]*5 for _ in range(self.num_players)]
        player_receiving_resource = [False]*5
        for tile in producing_tiles:
            if tile.robber:
                continue
            for vertex in tile.vertices:
                if vertex.player_id == -1:
                    continue
                player_receiving_resource[vertex.player_id] = True
                payout = 2 if vertex.is_city else 1
                resource_payout[vertex.player_id][tile.resource] += payout
                resource_count[tile.resource] += payout
        for resource in [Resource.BRICK, Resource.GRAIN, Resource.LUMBER, Resource.ORE, Resource.WOOL]:
            if resource_count[resource] > (remaining := self.remaining_resource(resource)):
                if sum(player_receiving_resource) == 1:
                    # the one player gets whatever amount of the resource is left
                    resource_payout[player_receiving_resource.index(True)][resource] = remaining
                else:
                    # nobody gets any of the resource
                    for player_id in range(self.players):
                        resource_payout[player_id][resource] = 0
        # actually pay out resources to players
        for player_id in range(self.players):
            for resource in [Resource.BRICK, Resource.GRAIN, Resource.LUMBER, Resource.ORE, Resource.WOOL]:
                self.dispense_resource(resource, resource_payout[player_id][resource])
                self.get_player(player_id).give_resource(resource, resource_payout[player_id][resource])

    def build_settlement(self, player_id: int, vertex: Vertex):
        """
        Builds a settlement for a player.
        :param player_id: ID of player building settlement
        :param vertex: Vertex upon which to build settlement
        """
        if vertex.player_id != -1:
            raise FailedBuildError(
                f"Player {str(player_id)} may not build on a spot that Player {str(vertex.player_id)} has already built on.")
        player = self.players[player_id]
        if self.is_game_start:
            player.place_settlement(vertex)
            self.player_buildings[player_id].add(vertex)
            if player.first_settlement_played:
                # the player's second settlement in the setup phase should award resources
                # get tiles from vertex
                # for each tile, pay out the tile's resource to the player

                pass
            else:
                player.first_settlement_played = True

        elif not player.can_build_settlement():
            raise FailedBuildError(f"Player {str(player_id)} cannot build a settlement.")
        else:
            player.build_settlement(vertex)
            self.player_buildings[player_id].add(vertex)

    def build_road(self, player_id: int, edge: Edge):
        """
        Builds a road for a player.
        :param player_id: ID of player building road
        :param edge: Edge upon which to build road
        """
        if edge.player_road_id != -1:
            raise FailedBuildError(
                f"Player {str(player_id)} may not build on a spot that Player {str(edge.player_road_id)} has already built on.")
        player = self.players[player_id]
        if self.is_game_start:
            player.place_road(edge)
            self.player_roads[player_id].add(edge)
        elif not player.can_build_road():
            raise FailedBuildError(f"Player {str(player_id)} cannot build a road.")
        else:
            player.build_road(edge)
            self.player_roads[player_id].add(edge)

    def build_city(self, player_id: int, vertex: Vertex):
        """
        Attempts to build a city for a certain player.
        :param player_id: ID of player building city
        :param vertex: Vertex upon which to build city
        """
        player = self.players[player_id]
        if not player.can_build_city():
            raise FailedBuildError("Player " + player_id + " cannot build a city.")
        if vertex.player_id != player_id:
            raise FailedBuildError("Player " + player_id + " cannot build a city without first building a settlement.")
        if vertex.is_city():
            raise FailedBuildError("A city already exists at this spot.")
        player.build_city(vertex)

    def get_players_on_tile(self, tile: Tile) -> Set[Player]:
        """
        Get all players that have a building on this tile.
        :param tile: Tiles to check
        :return: Players on the tile
        """
        players = set()
        vertices = tile.vertices
        for vertex in vertices:
            if (i := vertex.player_id) != -1:
                players.add(self.players[i])
        return players

    def get_player_subgraph(self, player: Player) -> Graph:
        """
        Returns the smallest subgraph of the board's vertex subgraph that includes
        all vertices and edges that this player has built on. The subgraph has at most 2 components.
        """
        return self.board.vertex_graph.subgraph(
            [x.vertex_id for x in self.player_buildings[player.player_id]])

    def get_available_road_spots(self, player_id: int) -> List[Edge]:
        """
        Given a player, return all edges that this player can build a road on.
        """
        res = []
        for edge in self.board.vertex_graph.edges:
            edge_obj = self.board.get_edge_from_graph_edge(edge)
            if edge_obj.player_road_id != -1:
                continue
            v1, v2 = self.board.vertex_objects[edge[0]], self.board.vertex_objects[edge[1]]
            if v1.player_id == player_id or v2.player_id == player_id:
                res.append(edge_obj)
                continue
        return res

    def get_available_settlement_spots(self, player_id: int) -> List[Vertex]:
        """
        Given a player, return all vertices that this player can build a settlement on.
        When is_setup_phase is True, the player is only bound by the "must not be adjacent to another settlement" build
        rule, and not the "must be adjacent to one of your roads" build rule.
        """
        res = []
        for vertex in self.board.vertex_graph.nodes:
            vertex_obj = self.board.vertex_objects[vertex]
            if vertex_obj.player_id != -1:
                continue
            for neighbor in self.board.vertex_graph.neighbors(vertex):
                neighbor_obj = self.board.vertex_objects[neighbor]
                if neighbor_obj.player_id != -1:
                    break
            else:
                if self.is_game_start:
                    res.append(vertex_obj)
                else:
                    for edge_obj in self.board.get_edges_from_vertex(vertex_obj):
                        if edge_obj.player_road_id == player_id:
                            res.append(vertex_obj)
                            break
        return res

    def advance_turn(self) -> int:
        return self.advance_turn_setup() if self.is_game_start else self.advance_turn_non_setup()

    def advance_turn_non_setup(self) -> int:
        """
        Start the turn of the next player, and return that player ID.
        """
        self.current_turn_idx = (self.current_turn_idx + 1) % self.num_players
        return self.turn_order[self.current_turn_idx]

    def advance_turn_setup(self) -> int:
        """
        Start the setup turn of the next player, and return that player ID.
        """
        if self.current_setup_turn_idx + 1 == len(self.setup_turn_order):
            # end the setup phase
            self.is_game_start = False
            return self.current_turn_idx
        self.current_setup_turn_idx += 1
        return self.setup_turn_order[self.current_setup_turn_idx]

    def get_player(self, player_id: int) -> Player:
        return self.players[player_id]

    def get_agent(self, player_id: int) -> Agent:
        assert player_id != 0
        return self.agents[player_id]

    def get_players(self) -> List[Player]:
        return self.players

    def set_robber_tile(self, tile: Tile):
        self.robber_tile = tile


if __name__ == "__main__":
    game = Game()
    gw = GameWindow(game)
    gw.draw()
