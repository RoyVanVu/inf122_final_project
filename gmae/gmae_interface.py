from abc import ABC, abstractmethod

class MiniAdventure(ABC):
    @abstractmethod
    def initialize(self, p1, p2) -> None:   # ← remove ProfileFacade type hints here
        """Set up the map, entities, items, and starting state for both players."""
        ...

    @abstractmethod
    def accept_input(self, player_id: int, action: str) -> str:
        ...

    @abstractmethod
    def advance_turn(self) -> None:
        ...

    @abstractmethod
    def get_state(self) -> dict:
        ...

    @abstractmethod
    def check_completion(self) -> str:
        """Return one of: 'ONGOING', 'WIN', 'LOSS', 'DRAW'"""
        ...

    @abstractmethod
    def reset(self) -> None:
        ...

    @abstractmethod
    def get_description(self) -> str:
        ...