from abc import ABC, abstractmethod

from constants import DEVELOPMENT
from game import Game


class DevelopmentCard(ABC):

    @staticmethod
    @abstractmethod
    def dev_type() -> DEVELOPMENT:
        ...

    @staticmethod
    @abstractmethod
    def apply_action(game: Game, player_id: int):
        ...


class Knight(DevelopmentCard):

    @staticmethod
    def dev_type() -> DEVELOPMENT:
        return DEVELOPMENT.KNIGHT

    @staticmethod
    def apply_action(game: Game, player_id: int):
        player = game.get_player(player_id)
        tile_location = player.select_tile_for_robber(game)
        tile = game.board.get_tile(tile_location)
        game.set_robber_tile(tile)
        player2 = player.select_player_to_steal_from(game, tile)
        resource = player2.get_random_available_resource()
        player2.take_resource(resource, 1)
        player.give_resource(resource, 1)


class Monopoly(DevelopmentCard):

    @staticmethod
    def dev_type() -> DEVELOPMENT:
        return DEVELOPMENT.MONOPOLY

    @staticmethod
    def apply_action(game: Game, player_id: int):
        player = game.get_player(player_id)
        r = player.select_monopoly_resource(game)
        for player2 in game.get_players():
            count = player2.get_resource_count(r)
            player.give_resource(r, count)
            player2.take_resource(r, count)


class RoadBuilding(DevelopmentCard):

    @staticmethod
    def dev_type() -> DEVELOPMENT:
        return DEVELOPMENT.ROAD_BUILDING

    @staticmethod
    def apply_action(game: Game, player_id: int):
        player = game.get_player(player_id)
        available_spots = game.get_available_road_spots(player_id)
        e1 = player.select_road_building_spot(game, available_spots)
        player.build_road(e1)
        available_spots.remove(e1)
        e2 = player.select_road_building_spot(game, available_spots)
        player.build_road(e2)


class VictoryPoint(DevelopmentCard):

    @staticmethod
    def dev_type() -> DEVELOPMENT:
        return DEVELOPMENT.VICTORY_POINT

    @staticmethod
    def apply_action(game: Game, player_id: int):
        player = game.get_player(player_id)
        player.give_victory_points(1)


class YearOfPlenty(DevelopmentCard):

    @staticmethod
    def dev_type() -> DEVELOPMENT:
        return DEVELOPMENT.YEAR_OF_PLENTY

    @staticmethod
    def apply_action(game: Game, player_id: int):
        player = game.get_player(player_id)
        r = player.select_year_of_plenty_resource(game)
        player.give_resource(r, 2)



