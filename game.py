from enum import Enum
from random import shuffle, sample
import random

from board import Board
from constants import RESOURCE, PLAYERCOLOR
from draw import draw
from player import Player
from tile import Tile


class Game:

    def __init__(self, six_players=False):
        self.players = [Player(PLAYERCOLOR(i) for i in range(4))]
        if six_players:
            self.board = Board(7, 4)
            for i in range(4, 6):
                self.players.append(Player(PLAYERCOLOR(i)))
        else:
            self.board = Board(5, 3)

    def roll(self):
        """
        Rolls both dice, and notifies all Player objects of the outcome.
        """
        roll = random.randrange(1, 7) + random.randrange(1, 7)
        for player in self.players:
            player.handle_roll(roll)


if __name__ == "__main__":
    game = Game()
    draw(game.board)
