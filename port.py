from constants import RESOURCE

class Port:
    """
    This class represents a port that is situated on a vertex that is on the edge of the board. Ports have an accepted
    resource type and a granted resource type, with associated amounts. Players who have a building on the port may,
    on their turn, surrender the specified amount of accepted resource and in return gain the granted resource. This
    action may be performed as many times as the player has sufficient resources to trade.
    """

    def __init__(self, resource_type: RESOURCE, exchange_rate: tuple, ):