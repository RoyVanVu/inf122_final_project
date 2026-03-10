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
        """Load profile from profiles/<filename>.json.
        Creates a brand-new profile if the file doesn't exist yet."""
        path = os.path.join(PROFILES_DIR, f"{filename}.json")
        if not os.path.exists(path):
            # First time this player logs in — create a fresh profile
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