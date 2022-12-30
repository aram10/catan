from enum import Enum
from random import shuffle, sample
import random
import warnings

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

    def roll(self):
        """
        Rolls both dice, and notifies all Player objects of the outcome.
        """
        roll = random.randrange(1, 7) + random.randrange(1, 7)
        producing_tiles = self.board.get_tiles_with_chit(roll)
        for tile in producing_tiles:
            tile.
        for player in self.players:
            player.handle_roll(roll)

    def build_settlement(self, player_id: int, vertex: Vertex):
        """
        Attempts to build a settlement for a certain player.
        :param player_id: ID of player building settlement
        :param vertex: Vertex upon which to build settlement.
        """
        player = self.players[player_id]
        if not player.can_build_settlement():
            raise FailedBuildError("Player " + player_id + " does not have sufficient resources to build a settlement")
        if vertex.get_player_id() != -1:
            raise FailedBuildError("Player " + player_id + " may not build on a spot that Player " + vertex.get_player_id() + " has already built on.")



    def build_city(self, player_id: int, vertex: Vertex) -> bool:
        """
        Attempts to build a city for a certain player
        :param player_id:
        :param vertex:
        :return:
        """


if __name__ == "__main__":
    game = Game()
    draw(game.board)
