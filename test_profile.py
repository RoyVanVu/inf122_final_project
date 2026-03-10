from gmae.gmae_core import PlayerProfile, ProfileFacade

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

p3 = PlayerProfile.load("khoa")
facade = ProfileFacade(p3)

# Adventures can read
print(facade.get_name())        # khoa
print(facade.get_realm())       # Stonepeak
print(facade.get_inventory())   # []

# Adventures queue a result
facade.update_history("Escort Across the Realm", "WIN")
print(facade._pending_result)   # {"adventure": "Escort Across the Realm", "result": "WIN"}

# Framework flushes and saves
facade._save("khoa")

# Reload and confirm quest_history was written
p4 = PlayerProfile.load("khoa")
print(p4.quest_history)         # [{"adventure": "Escort Across the Realm", "result": "WIN"}]