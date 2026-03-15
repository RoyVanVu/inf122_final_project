from gmae.gmae_interface import MiniAdventure


class InputProxy:
    BASE_VALID_ACTIONS = {
        "move north", "move south", "move east", "move west",
        "use item", "wait", "quit"
    }

    def __init__(self, adventure: MiniAdventure):
        self._adventure = adventure
        extra = getattr(adventure, "VALID_ACTIONS", set())
        self._valid_actions = self.BASE_VALID_ACTIONS | set(extra)

    def validate(self, player_id: int, action: str) -> tuple[bool, str]:
        if player_id not in (1, 2):
            return False, f"Invalid player ID '{player_id}'. Must be 1 or 2."

        if not isinstance(action, str) or not action.strip():
            return False, "Action cannot be empty. Please enter a command."

        normalized = action.strip().lower()

        if normalized not in self._valid_actions:
            valid_list = ", ".join(sorted(self._valid_actions))
            return False, f"Unknown action '{action}'. Valid actions: {valid_list}"

        return True, ""

    def forward(self, player_id: int, action: str) -> str:
        normalized = action.strip().lower()
        is_valid, error_msg = self.validate(player_id, normalized)

        if not is_valid:
            return f"[BLOCKED] {error_msg}"

        return self._adventure.accept_input(player_id, normalized)
