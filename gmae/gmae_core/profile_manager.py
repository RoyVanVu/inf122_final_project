import json 
import os 

PROFILES_DIR = os.path.join(os.path.dirname(__file__), "..", "profiles")

class PlayerProfile:
    def __init__(self, character_name: str, preferred_realm: str = "Verdania"):
        self.character_name = character_name
        self.preferred_realm = preferred_realm
        self.inventory_snapshot: list = []
        self.quest_history: list = []   # e.g. [{"adventure": "Escort", "result": "WIN"}]
        self.achievements: list = []    # e.g. ["First Blood", "Relic Master"]

    def save(self, filename: str) -> None:
        """Save profile to profiles/<filename>.json"""
        os.makedirs(PROFILES_DIR, exist_ok=True)
        path = os.path.join(PROFILES_DIR, f"{filename}.json")
        data = {
            "character_name":    self.character_name,
            "preferred_realm":   self.preferred_realm,
            "inventory_snapshot": self.inventory_snapshot,
            "quest_history":     self.quest_history,
            "achievements":      self.achievements,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filename: str) -> "PlayerProfile":
        path = os.path.join(PROFILES_DIR, f"{filename}.json")
        if not os.path.exists(path):
            return cls(character_name=filename)

        with open(path, "r") as f:
            data = json.load(f)

        profile = cls(
            character_name=data.get("character_name", filename),
            preferred_realm=data.get("preferred_realm", "Verdania"),
        )
        profile.inventory_snapshot = data.get("inventory_snapshot", [])
        profile.quest_history      = data.get("quest_history", [])
        profile.achievements       = data.get("achievements", [])
        return profile
    
    def __repr__(self) -> str:
        return (
            f"PlayerProfile(name={self.character_name!r}, "
            f"realm={self.preferred_realm!r}, "
            f"quests={len(self.quest_history)}, "
            f"achievements={len(self.achievements)})"
        )
    
class ProfileFacade:
    def __init__(self, profile: PlayerProfile):
        self._profile = profile          
        self._pending_result = None 

    def get_name(self) -> str:
        return self._profile.character_name
    
    def get_realm(self) -> str:
        return self._profile.preferred_realm
    
    def get_inventory(self) -> list:
        return list(self._profile.inventory_snapshot)
    
    def get_quest_history(self) -> list:
        return list(self._profile.quest_history)
    
    def get_achievements(self) -> list:
        return list(self._profile.achievements)
    
    def update_history(self, adventure_name: str, result: str) -> None:
        self._pending_result = {"adventure": adventure_name, "result": result}

    def _flush(self) -> None:
        if self._pending_result:
            self._profile.quest_history.append(self._pending_result)
            self._pending_result = None

    def _save(self, filename: str) -> None:
        self._flush()
        self._profile.save(filename)

    def __repr__(self) -> str:
        return f"ProfileFacade(player={self.get_name()!r})"