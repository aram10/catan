"""
Main entry point for the Catan game with GUI.
This keeps game logic (game.py) separate from presentation (game_window.py).
"""
from game import Game
from game_window import GameWindow


def main():
    game = Game()
    gw = GameWindow(game)
    gw.draw()


if __name__ == "__main__":
    main()
