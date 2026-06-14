from typing import List

from constants import Resource


class TradeProposal:
    def __init__(self, game: "Game",
                 proposer: "Player",
                 target: "Player",
                 resources_given: List[int],
                 resources_received: List[int]):
        self.proposer = proposer
        self.target = target
        if not all(x >= 0 for x in resources_given + resources_received):
            raise ValueError("All resources must be non-negative.")
        if sum(resources_given) == 0 or sum(resources_received) == 0:
            raise ValueError("A trade must involve giving and receiving at least one resource.")
        self.resources_given = resources_given
        self.resources_received = resources_received

        self.turn_idx = game.current_turn
        self.is_accepted = False

    @property
    def is_trade_possible(self):
        return all(x >= y for x, y in zip(self.proposer.resources, self.resources_given)) and \
            all(x >= y for x, y in zip(self.target.resources, self.resources_received))

    def accept_trade(self):
        if not self.is_trade_possible:
            raise ValueError("Trade is not possible.")
        if self.is_accepted:
            raise ValueError("Trade has already executed.")
        self.is_accepted = True
        for i, amt in enumerate(self.resources_given):
            self.target.give_resource(Resource(i), amt)
            self.proposer.take_resource(Resource(i), amt)
        for i, amt in enumerate(self.resources_received):
            self.target.take_resource(Resource(i), amt)
            self.proposer.give_resource(Resource(i), amt)
