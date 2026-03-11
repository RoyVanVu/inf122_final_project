from abc import ABC, abstractmethod
from gmae.gmae_core.profile_manager import ProfileFacade


class MiniAdventure(ABC):
    @abstractmethod
    def initialize(self, p1: ProfileFacade, p2: ProfileFacade) -> None:
        """Set up the map, entities, items, and starting state for both players."""
        ...

    @abstractmethod
    def accept_input(self, player_id: int, action: str) -> str:
        """
        Handle a single player action for their turn.
        Returns a message string describing what happened
        (e.g. 'Player 1 moved north.', 'Invalid move.')
        """
        ...

    @abstractmethod
    def advance_turn(self) -> None:
        """
        Advance the game world by one step —
        move NPCs, trigger hazards, update timers, etc.
        Called by the framework after each player's input.
        """
        ...

    @abstractmethod
    def get_state(self) -> dict:
        """
        Return the current game state as a dict for display.
        Example keys: 'map', 'npc_health', 'scores', 'turns_remaining'
        The framework uses this to render the game to both players.
        """
        ...

    @abstractmethod
    def check_completion(self) -> str:
        """
        Return one of: 'ONGOING', 'WIN', 'LOSS', 'DRAW'
        Called by the framework after every turn to detect end conditions.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Restart the adventure from scratch with the same two players."""
        ...

    @abstractmethod
    def get_description(self) -> str:
        """
        Short one-line description shown in the adventure selection menu.
        Example: 'Co-op: Escort an NPC safely across the realm.'
        """
        ...