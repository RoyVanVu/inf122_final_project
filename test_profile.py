from gmae.gmae_core import PlayerProfile

# Create and save
p = PlayerProfile.load("khoa")       # new profile, file doesn't exist yet
p.preferred_realm = "Stonepeak"
p.achievements.append("First Login")
p.save("khoa")

# Reload and check
p2 = PlayerProfile.load("khoa")
print(p2)          # should show name, realm, 0 quests, 1 achievement
print(p2.achievements)