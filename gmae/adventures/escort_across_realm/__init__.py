import random
from gmae.gmae_interface import MiniAdventure
from gmae.gmae_core.profile_manager import ProfileFacade
from gmae.shared.realm_adapter import RealmAdapter
from gmae.shared.inventory_adapter import InventoryAdapter
from gmae.shared.chiwei_guildquest import Item


class EscortAcrossRealm(MiniAdventure):
    """
    Co-op mini-adventure — both players work together to escort
    an NPC from the start tile to the destination tile.

    Win:  NPC reaches destination (bottom-right corner).
    Loss: NPC health drops to 0, or turn limit runs out.

    Reuses: RealmAdapter (Van's realm model) for the grid and movement.
            InventoryAdapter (Chi-Wei's inventory model) for player items.
    """

    MAP_WIDTH  = 8
    MAP_HEIGHT = 8
    MAX_TURNS  = 30
    NPC_MAX_HP = 10
    HAZARD_DAMAGE = 2

    def __init__(self):
        self._map: RealmAdapter = None
        self._p1: ProfileFacade = None
        self._p2: ProfileFacade = None
        self._p1_inv: InventoryAdapter = None
        self._p2_inv: InventoryAdapter = None
        self._npc_health: int = self.NPC_MAX_HP
        self._turn: int = 0
        self._hazards: list = []        
        self._destination: tuple = (self.MAP_WIDTH - 1, self.MAP_HEIGHT - 1)
        self._messages: list = []      

    def initialize(self, p1: ProfileFacade, p2: ProfileFacade) -> None:
        self._p1 = p1
        self._p2 = p2
        self._npc_health = self.NPC_MAX_HP
        self._turn = 0
        self._messages = []

        self._map = RealmAdapter("EscortRealm", self.MAP_WIDTH, self.MAP_HEIGHT)

        self._map.place_entity("player1", 0, 0)
        self._map.place_entity("player2", 1, 0)
        self._map.place_entity("npc",     0, 1)

        self._map.set_terrain(
            self._destination[0], self._destination[1], "mountain"
        )

        self._hazards = []
        safe = {(0, 0), (1, 0), (0, 1), self._destination}
        attempts = 0
        while len(self._hazards) < 5 and attempts < 100:
            hx = random.randint(0, self.MAP_WIDTH - 1)
            hy = random.randint(1, self.MAP_HEIGHT - 1)
            if (hx, hy) not in safe and (hx, hy) not in self._hazards:
                self._hazards.append((hx, hy))
                self._map.set_terrain(hx, hy, "water")  # water = hazard
            attempts += 1

        self._p1_inv = InventoryAdapter(p1.get_name())
        self._p2_inv = InventoryAdapter(p2.get_name())
        self._p1_inv.add_item(Item("potion_p1", "Health Potion", "Common"))
        self._p2_inv.add_item(Item("potion_p2", "Health Potion", "Common"))

        self._messages.append(
            "Escort begins! Guide the NPC to the mountain (bottom-right).\n"
            "  TIP: Move onto the NPC's tile to push (nudge) it in that direction.\n"
            "  Map legend: P=Player  N=NPC  ^=Destination  ~=Hazard  .=Empty"
        )

    def accept_input(self, player_id: int, action: str) -> str:
        entity = f"player{player_id}"
        inv = self._p1_inv if player_id == 1 else self._p2_inv

        if action.startswith("move "):
            direction = action.split(" ", 1)[1]
            success, _, _, msg = self._map.move(entity, direction)

            if success:
                px, py = self._map.get_position(entity)
                nx, ny = self._map.get_position("npc")
                if (px, py) == (nx, ny):
                    # Try to push NPC in the same direction
                    push_ok, _, _, _ = self._map.move("npc", direction)
                    if push_ok:
                        msg += f" (NPC nudged {direction}!)"
                    else:
                        # NPC blocked (border/wall) — swap positions so
                        #  player  approach from the other side
                        old_px, old_py = px, py  # player's current (= NPC's) pos
                        # Player goes back to where they came from
                        opposite = {"north": "south", "south": "north",
                                     "east": "west", "west": "east"}
                        self._map.move(entity, opposite[direction])
                        # Swap: move NPC to player's old spot, player to NPC's old spot
                        ppx, ppy = self._map.get_position(entity)
                        self._map.place_entity("npc", ppx, ppy)
                        self._map.place_entity(entity, old_px, old_py)
                        msg += f" (Swapped past NPC — push from the other side!)"
            return msg

        elif action == "use item":
            result = inv.use_item(
                "potion_p1" if player_id == 1 else "potion_p2"
            )
            if result["success"]:
                heal = 3
                self._npc_health = min(
                    self.NPC_MAX_HP, self._npc_health + heal
                )
                return (f"{result['message']} "
                        f"NPC healed +{heal} HP "
                        f"(now {self._npc_health}/{self.NPC_MAX_HP}).")
            return result["message"]

        elif action == "wait":
            return f"Player {player_id} waits."

        return f"Unknown action: {action}"

    def advance_turn(self) -> None:
        self._turn += 1
        self._messages = []

        nx, ny = self._map.get_position("npc")
        if (nx, ny) in self._hazards:
            self._npc_health -= self.HAZARD_DAMAGE
            self._npc_health = max(0, self._npc_health)
            self._messages.append(
                f"NPC is on a hazard! -{self.HAZARD_DAMAGE} HP "
                f"(now {self._npc_health}/{self.NPC_MAX_HP})."
            )

        new_hazards = []
        for hx, hy in self._hazards:
            new_hy = hy + 1

            # Restore old tile — mountain if destination, else plains
            if (hx, hy) == self._destination:
                self._map.set_terrain(hx, hy, "mountain")
            else:
                self._map.set_terrain(hx, hy, "plains")

            if new_hy < self.MAP_HEIGHT:
                # Don't overwrite the destination mountain with water
                if (hx, new_hy) != self._destination:
                    self._map.set_terrain(hx, new_hy, "water")
                new_hazards.append((hx, new_hy))
            else:
                # Hazard fell off bottom — spawn a new one at the top
                new_x = random.randint(0, self.MAP_WIDTH - 1)
                # Avoid spawning on the destination
                while (new_x, 0) == self._destination:
                    new_x = random.randint(0, self.MAP_WIDTH - 1)
                self._map.set_terrain(new_x, 0, "water")
                new_hazards.append((new_x, 0))
        self._hazards = new_hazards

    def get_state(self) -> dict:
        nx, ny = self._map.get_position("npc")
        dx, dy = self._destination
        return {
            "map":            self._map.render_map(),
            "npc_health":     f"{self._npc_health}/{self.NPC_MAX_HP}",
            "npc_position":   f"({nx}, {ny})",
            "destination":    f"({dx}, {dy})",
            "turns_remaining": self.MAX_TURNS - self._turn,
            "p1_items":       len(self._p1_inv.get_items()) if self._p1_inv else 0,
            "p2_items":       len(self._p2_inv.get_items()) if self._p2_inv else 0,
            "events":         " | ".join(self._messages) if self._messages else "—",
        }

    def check_completion(self) -> str:
        nx, ny = self._map.get_position("npc")
        if (nx, ny) == self._destination:
            return "WIN"

        if self._npc_health <= 0:
            return "LOSS"

        if self._turn >= self.MAX_TURNS:
            return "LOSS"

        return "ONGOING"

    def reset(self) -> None:
        if self._p1 and self._p2:
            self.initialize(self._p1, self._p2)

    def get_description(self) -> str:
        return (
            "Co-op: Escort the NPC safely to the mountain "
            "before hazards destroy it."
        )
