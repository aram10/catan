from constants import RESOURCE, PLAYERCOLOR
from edge import Edge


class Player:

    def __init__(self, color: PLAYERCOLOR):
        self.resources = [0, 0, 0, 0, 0]  # resources (BRICK, GRAIN, LUMBER, ORE, WOOD)
        self.color = color
        self.victory_points = 0

    def get_resource_count(self, r: RESOURCE):
        return self.resources[r.value]

    def handle_roll(self, roll: int):
        """
        Invoked whenever the dice are rolled. Handles resource production for this player.
        :param roll: The dice roll.
        """
        raise NotImplementedError()

    def build_road(self, edge: Edge):
        raise NotImplementedError()

    def build_settlement(self, ):

