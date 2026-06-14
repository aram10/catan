class FailedBuildError(Exception):
    """
    Raised when an instruction to build a road, settlement, or city fails.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class IllegalActionError(Exception):
    """
    Raised when a player attempts an action that is not legal in the current game state.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

