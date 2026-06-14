from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class ActionType(IntEnum):
    """All possible action types in a game of Catan."""
    ROLL_DICE = 0
    BUILD_SETTLEMENT = 1
    BUILD_ROAD = 2
    BUILD_CITY = 3
    BUY_DEV_CARD = 4
    PLAY_DEV_CARD = 5
    PROPOSE_TRADE = 6
    RESPOND_TO_TRADE = 7
    EXCHANGE_RESOURCE = 8
    MOVE_ROBBER = 9
    STEAL = 10
    DISCARD = 11
    END_TURN = 12


@dataclass
class Action:
    """
    A single game action. The `target` field varies by action type:
      ROLL_DICE/BUY_DEV_CARD/PROPOSE_TRADE/END_TURN: None
      BUILD_SETTLEMENT/BUILD_CITY: Vertex
      BUILD_ROAD: Edge
      PLAY_DEV_CARD: Development enum
      RESPOND_TO_TRADE: bool (accept/reject)
      EXCHANGE_RESOURCE: (Resource given, Resource received)
      MOVE_ROBBER: Tile
      STEAL: player ID (int)
      DISCARD: Resource enum
    """
    action_type: ActionType
    target: Any = None

    def __repr__(self):
        return f"Action({self.action_type.name}, target={self.target})"
