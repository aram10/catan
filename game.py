from collections import defaultdict, deque
from enum import Enum
from random import shuffle, sample
import random
import warnings
from typing import List, Tuple, Set

from networkx import Graph

from board import Board
from constants import RESOURCE, PLAYERCOLOR
from custom_types import GraphVertex, GraphEdge
from draw import draw
from edge import Edge
from player import Player
from tile import Tile
from vertex import Vertex
from exceptions import FailedBuildError


class Game:

    def __init__(self, six_players=False):
        self.players = [Player(i, PLAYERCOLOR(i)) for i in range(4)]
        if six_players:
            self.board = Board(4)
            for i in range(4, 6):
                self.players.append(Player(PLAYERCOLOR(i)))
        else:
            self.board = Board(3)
        self.robber_tile = random.choice(list(self.board.get_desert_tiles()))
        self.player_buildings = defaultdict(set)
        self.player_roads = defaultdict(set)

    def roll(self, player: Player):
        """
        Rolls both dice, and notifies all Player objects of the outcome.
        """
        roll = random.randrange(1, 7) + random.randrange(1, 7)
        if roll == 7:
            # TODO: Allow player to choose robber spot and player to rob
            tile = self.board.fetch_random_tile()
            self.robber_tile.remove_robber()
            tile.place_robber()
            self.robber_tile = tile
            player2 = random.choice(self.get_players_on_tile(tile))
            player2_resource = random.choice(player2.get_available_resources())
            player2.take_resource(player2_resource, 1)
            player.give_resource(player2_resource, 1)
        else:
            producing_tiles = self.board.get_tiles_with_chit(roll)
            for tile in producing_tiles:
                resource = tile.get_resource()
                for vertex in tile.vertices:
                    player_id = vertex.get_player_id()
                    if player_id == -1:
                        continue
                    player = self.players[player_id]
                    if vertex.is_city():
                        player.give_resource(resource, 2)
                    else:
                        player.give_resource(resource, 1)

        # TODO: Need to allow player to actually take turn

    def build_settlement(self, player_id: int, vertex: Vertex, is_game_start: bool = False):
        """
        Builds a settlement for a player.
        :param player_id: ID of player building settlement
        :param vertex: Vertex upon which to build settlement
        :param is_game_start: True if player is placing free settlement(s) at game start
        """
        if vertex.get_player_id() != -1:
            raise FailedBuildError(
                f"Player {str(player_id)} may not build on a spot that Player {str(vertex.get_player_id())} has already built on.")
        player = self.players[player_id]
        if is_game_start:
            player.place_settlement(vertex)
            self.player_buildings[player_id].add(vertex)
        elif not player.can_build_settlement():
            raise FailedBuildError(f"Player {str(player_id)} cannot build a settlement.")
        else:
            player.build_settlement(vertex)
            self.player_buildings[player_id].add(vertex)

    def build_road(self, player_id: int, edge: Edge, is_game_start: bool = False):
        """
        Builds a road for a player.
        :param player_id: ID of player building road
        :param edge: Edge upon which to build road
        :param is_game_start: True if player is placing free road(s) at game start
        """
        if edge.get_player_road_id() != -1:
            raise FailedBuildError(
                f"Player {str(player_id)} may not build on a spot that Player {str(edge.get_player_road_id())} has already built on.")
        player = self.players[player_id]
        if is_game_start:
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
        if vertex.get_player_id() != player_id:
            raise FailedBuildError("Player " + player_id + " cannot build a city without first building a settlement.")
        if vertex.is_city():
            raise FailedBuildError("A city already exists at this spot.")
        player.build_city(vertex)

    def get_players_on_tile(self, tile: Tile) -> List[Player]:
        """
        Get all players that have a building on this tile.
        :param tile: Tiles to check
        :return: Players on the tile
        """
        players = set()
        vertices = tile.get_vertices()
        for vertex in vertices:
            if (i := vertex.get_player_id()) != -1:
                players.add(self.players[i])
        return players

    def get_player_subgraph(self, player: Player) -> Graph:
        """
        Returns the smallest subgraph of the board's vertex subgraph that includes
        all vertices and edges that this player has built on. The subgraph has at most 2 components.
        """
        return self.board.vertex_graph.subgraph(
            [x.get_vertex_id() for x in self.player_buildings[player.get_player_id()]])

    def get_available_road_spots(self, player_id: int) -> List[Edge]:
        """
        Given a player, return all edges that this player can build a road on.
        """
        res = []
        for edge in self.board.vertex_graph.edges:
            edge_obj = self.board.get_edge_from_graph_edge(edge)
            if edge_obj.get_player_road_id() != -1:
                continue
            v1, v2 = self.board.vertex_objects[edge[0]], self.board.vertex_objects[edge[1]]
            if v1.get_player_id() == player_id or v2.get_player_id() == player_id:
                res.append(edge_obj)
                continue
            for e2 in self.board.get_edges_from_vertex(v1):
                if e2.get_player_road_id() == player_id:
                    res.append(edge_obj)
                    continue
            for e2 in self.board.get_edges_from_vertex(v2):
                if e2.get_player_road_id() == player_id:
                    res.append(edge_obj)
                    continue
        return res

    def get_available_settlement_spots(self, player_id: int) -> List[Vertex]:
        """
        Given a player, return all vertices that this player can build a settlement on.
        """
        res = []
        for vertex in self.board.vertex_graph.nodes:
            vertex_obj = self.board.vertex_objects[vertex]
            if vertex_obj.get_player_id() != -1:
                continue
            for neighbor in self.board.vertex_graph.neighbors(vertex):
                neighbor_obj = self.board.vertex_objects[neighbor]
                if neighbor_obj.get_player_id() not in [-1, player_id]:
                    break
            else:
                for edge_obj in self.board.get_edges_from_vertex(vertex_obj):
                    if edge_obj.get_player_road_id() == player_id:
                        res.append(vertex_obj)
                        break
        return res

    def get_player(self, player_id: int) -> Player:
        return self.players[player_id]

    def get_players(self) -> List[Player]:
        return self.players

    def set_robber_tile(self, tile: Tile):
        self.robber_tile = tile


if __name__ == "__main__":
    game = Game()
    draw(game.board)
