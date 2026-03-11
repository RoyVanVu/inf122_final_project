from gmae.gmae_core import PlayerProfile, ProfileFacade
from gmae import MiniAdventure
from gmae.gmae_core import AdventureRegistry
from gmae.gmae_core import InputProxy

# # Create and save
# p = PlayerProfile.load("khoa")       # new profile, file doesn't exist yet
# p.preferred_realm = "Stonepeak"
# p.achievements.append("First Login")
# p.save("khoa")

# # Reload and check
# p2 = PlayerProfile.load("khoa")
# print(p2)          # should show name, realm, 0 quests, 1 achievement
# print(p2.achievements)


# ── Phase 3 test (add at bottom of test_profile.py) ──────────────

# p3 = PlayerProfile.load("khoa")
# facade = ProfileFacade(p3)

# # Adventures can read
# print(facade.get_name())        # khoa
# print(facade.get_realm())       # Stonepeak
# print(facade.get_inventory())   # []

# # Adventures queue a result
# facade.update_history("Escort Across the Realm", "WIN")
# print(facade._pending_result)   # {"adventure": "Escort Across the Realm", "result": "WIN"}

# # Framework flushes and saves
# facade._save("khoa")

# # Reload and confirm quest_history was written
# p4 = PlayerProfile.load("khoa")
# print(p4.quest_history)         # [{"adventure": "Escort Across the Realm", "result": "WIN"}]


# ── Phase 4 test (add at bottom of test_profile.py) ──────────────
# Try to instantiate MiniAdventure directly — should raise TypeError
# because it's abstract and can't be used on its own
try:
    m = MiniAdventure()
    print("ERROR: should not reach here")
except TypeError as e:
    print(f"Good — MiniAdventure is abstract: {e}")

# Try a minimal concrete subclass to confirm the interface works
class DummyAdventure(MiniAdventure):
    def initialize(self, p1, p2):        pass
    def accept_input(self, pid, action): return "ok"
    def advance_turn(self):              pass
    def get_state(self):                 return {}
    def check_completion(self):          return "ONGOING"
    def reset(self):                     pass
    def get_description(self):           return "A dummy adventure for testing."

dummy = DummyAdventure()
print(dummy.get_description())    # A dummy adventure for testing.
print(dummy.check_completion())   # ONGOING
print(dummy.accept_input(1, "move north"))  # ok


# ── Phase 5 test (add at bottom of test_profile.py) ──────────────
registry = AdventureRegistry()

# Register the DummyAdventure we made in Phase 4 test
registry.register("Dummy Adventure", DummyAdventure)

# list_adventures() should show it in the menu
print(registry.list_adventures())       # ['Dummy Adventure']

# get_adventure() should return a fresh instance each time
a1 = registry.get_adventure("Dummy Adventure")
a2 = registry.get_adventure("Dummy Adventure")
print(type(a1).__name__)                # DummyAdventure
print(a1 is a2)                         # False — different instances

# Registering a non-MiniAdventure class should raise TypeError
try:
    registry.register("Bad", str)
    print("ERROR: should not reach here")
except TypeError as e:
    print(f"Good — caught bad registration: {e}")

# Getting an unregistered name should raise KeyError
try:
    registry.get_adventure("Nonexistent")
    print("ERROR: should not reach here")
except KeyError as e:
    print(f"Good — caught missing adventure: {e}")


# ── Phase 6 test (add at bottom of test_profile.py) ──────────────
proxy = InputProxy(dummy)   # reuse the DummyAdventure instance from Phase 4 test

# Valid input — should pass through to adventure
result = proxy.forward(1, "move north")
print(result)               # ok  (DummyAdventure.accept_input returns "ok")

# Invalid player_id — should be blocked
result = proxy.forward(3, "move north")
print(result)               # [BLOCKED] Invalid player ID '3'. Must be 1 or 2.

# Empty action — should be blocked
result = proxy.forward(1, "   ")
print(result)               # [BLOCKED] Action cannot be empty.

# Unknown action — should be blocked
result = proxy.forward(2, "fly away")
print(result)               # [BLOCKED] Unknown action 'fly away'. Valid actions: ...

# validate() directly — check return values
print(proxy.validate(1, "wait"))        # (True, '')
print(proxy.validate(2, ""))            # (False, 'Action cannot be empty...')
