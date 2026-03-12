import random
from gmae.gmae_interface import MiniAdventure
from gmae.gmae_core.profile_manager import ProfileFacade
from gmae.shared.realm_adapter import RealmAdapter
from gmae.shared.inventory_adapter import InventoryAdapter
from gmae.shared.chiwei_guildquest import Item


class RelicHunt(MiniAdventure):
    """
    Competitive mini-adventure — two players race to collect
    the most relics scattered across the realm.

    Win:  Player with more relics when pool empties or turns run out.
    Draw: Equal relic counts at end.

    Reuses: RealmAdapter (Van's realm model) for the grid and movement.
            InventoryAdapter (Chi-Wei's inventory model) for relic storage.
    """

    MAP_WIDTH   = 8
    MAP_HEIGHT  = 8
    MAX_TURNS   = 25
    TOTAL_RELICS = 8

    def __init__(self):
        self._map: RealmAdapter = None
        self._p1: ProfileFacade = None
        self._p2: ProfileFacade = None
        self._p1_inv: InventoryAdapter = None
        self._p2_inv: InventoryAdapter = None
        self._scores: dict = {1: 0, 2: 0}
        self._turn: int = 0
        self._relics_remaining: int = self.TOTAL_RELICS
        self._relic_positions: list = []    # list of (x, y)
        self._messages: list = []

    def initialize(self, p1: ProfileFacade, p2: ProfileFacade) -> None:
        self._p1 = p1
        self._p2 = p2
        self._scores = {1: 0, 2: 0}
        self._turn = 0
        self._relics_remaining = self.TOTAL_RELICS
        self._messages = []

        self._map = RealmAdapter("RelicRealm", self.MAP_WIDTH, self.MAP_HEIGHT)

        self._map.place_entity("player1", 0, 0)
        self._map.place_entity("player2", self.MAP_WIDTH - 1, self.MAP_HEIGHT - 1)

        safe = {(0, 0), (self.MAP_WIDTH - 1, self.MAP_HEIGHT - 1)}
        self._relic_positions = []
        attempts = 0
        while len(self._relic_positions) < self.TOTAL_RELICS and attempts < 200:
            rx = random.randint(0, self.MAP_WIDTH - 1)
            ry = random.randint(0, self.MAP_HEIGHT - 1)
            if (rx, ry) not in safe and (rx, ry) not in self._relic_positions:
                self._relic_positions.append((rx, ry))
                self._map.set_terrain(rx, ry, "mountain")  # mountain = relic
            attempts += 1
        self._relics_remaining = len(self._relic_positions)

        self._p1_inv = InventoryAdapter(p1.get_name())
        self._p2_inv = InventoryAdapter(p2.get_name())

        self._messages.append(
            f"Relic Hunt begins! {self._relics_remaining} relics hidden. "
            "Move onto a relic tile to collect it automatically."
        )

    def accept_input(self, player_id: int, action: str) -> str:
        entity = f"player{player_id}"

        if action.startswith("move "):
            direction = action.split(" ", 1)[1]
            success, nx, ny, msg = self._map.move(entity, direction)

            if success:
                # Auto-collect relic if player lands on one
                if (nx, ny) in self._relic_positions:
                    self._collect_relic(player_id, nx, ny)
                    msg += f" — Relic collected! (Score: {self._scores[player_id]})"

            return msg

        elif action == "wait":
            px, py = self._map.get_position(entity)
            if (px, py) in self._relic_positions:
                self._collect_relic(player_id, px, py)
                return f"Player {player_id} collected a relic! (Score: {self._scores[player_id]})"
            return f"Player {player_id} waits."

        return f"Unknown action: {action}"

    def _collect_relic(self, player_id: int, x: int, y: int) -> None:
        self._relic_positions.remove((x, y))
        self._relics_remaining -= 1
        self._scores[player_id] += 1
        self._map.set_terrain(x, y, "plains")

        inv = self._p1_inv if player_id == 1 else self._p2_inv
        relic_id = f"relic_{x}_{y}"
        inv.add_item(Item(relic_id, f"Ancient Relic ({x},{y})", "Rare"))

        self._messages.append(
            f"Player {player_id} grabbed a relic at ({x},{y})!"
        )

    def advance_turn(self) -> None:
        self._turn += 1

    def get_state(self) -> dict:
        p1x, p1y = self._map.get_position("player1")
        p2x, p2y = self._map.get_position("player2")
        return {
            "map":              self._map.render_map(),
            "p1_score":         self._scores[1],
            "p2_score":         self._scores[2],
            "relics_remaining": self._relics_remaining,
            "turns_remaining":  self.MAX_TURNS - self._turn,
            "p1_position":      f"({p1x}, {p1y})",
            "p2_position":      f"({p2x}, {p2y})",
            "events":           " | ".join(self._messages) if self._messages else "—",
        }

    def check_completion(self) -> str:
        if self._relics_remaining <= 0:
            return self._determine_winner()

        if self._turn >= self.MAX_TURNS:
            return self._determine_winner()

        return "ONGOING"

    def _determine_winner(self) -> str:
        s1 = self._scores[1]
        s2 = self._scores[2]
        if s1 > s2:
            return "WIN"     
        elif s2 > s1:
            return "LOSS"   
        return "DRAW"

    def reset(self) -> None:
        if self._p1 and self._p2:
            self.initialize(self._p1, self._p2)

    def get_description(self) -> str:
        return (
            "Competitive: Race to collect the most relics "
            "before turns run out. Most relics wins!"
        )

def register(registry) -> None:
    registry.register("Relic Hunt", RelicHunt)