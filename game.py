from enum import Enum
from random import shuffle, sample
import random
import warnings
from typing import List

from board import Board
from constants import RESOURCE, PLAYERCOLOR
from draw import draw
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
        self.robber_tile = random.choice(self.board.get_desert_tiles())

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

    def build_settlement(self, player_id: int, vertex: Vertex):
        """
        Attempts to build a settlement for a certain player.
        :param player_id: ID of player building settlement
        :param vertex: Vertex upon which to build settlement
        """
        player = self.players[player_id]
        if not player.can_build_settlement():
            raise FailedBuildError("Player " + player_id + " cannot build a settlement.")
        if vertex.get_player_id() != -1:
            raise FailedBuildError(
                "Player " + player_id + " may not build on a spot that Player " + vertex.get_player_id() + " has already built on.")
        player.build_settlement(vertex)

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


if __name__ == "__main__":
    game = Game()
    draw(game.board)
