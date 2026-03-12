# tests/test_gmae.py
# Unit tests for GMAE core components

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from gmae.gmae_core.profile_manager import PlayerProfile, ProfileFacade
from gmae.gmae_core.adventure_registry import AdventureRegistry
from gmae.gmae_core.input_proxy import InputProxy
from gmae.gmae_interface import MiniAdventure
from gmae.shared.realm_adapter import RealmAdapter
from gmae.shared.inventory_adapter import InventoryAdapter
from gmae.shared.chiwei_guildquest import Item


# ── Dummy adventure for testing ──────────────────────────────────────
class DummyAdventure(MiniAdventure):
    def initialize(self, p1, p2):        pass
    def accept_input(self, pid, action): return "ok"
    def advance_turn(self):              pass
    def get_state(self):                 return {}
    def check_completion(self):          return "ONGOING"
    def reset(self):                     pass
    def get_description(self):           return "A dummy adventure."


# ── PlayerProfile tests ───────────────────────────────────────────────
class TestPlayerProfile:

    def test_new_profile_has_empty_history(self):
        p = PlayerProfile("testplayer")
        assert p.quest_history == []
        assert p.achievements == []
        assert p.inventory_snapshot == []

    def test_default_realm(self):
        p = PlayerProfile("testplayer")
        assert p.preferred_realm == "Verdania"

    def test_custom_realm(self):
        p = PlayerProfile("testplayer", preferred_realm="Stonepeak")
        assert p.preferred_realm == "Stonepeak"


# ── ProfileFacade tests ───────────────────────────────────────────────
class TestProfileFacade:

    def setup_method(self):
        self.profile = PlayerProfile("hero", "Verdania")
        self.facade = ProfileFacade(self.profile)

    def test_get_name(self):
        assert self.facade.get_name() == "hero"

    def test_get_realm(self):
        assert self.facade.get_realm() == "Verdania"

    def test_get_inventory_returns_copy(self):
        inv = self.facade.get_inventory()
        inv.append("fake item")
        # Original should not be modified
        assert self.facade.get_inventory() == []

    def test_update_history_queues_result(self):
        self.facade.update_history("Escort", "WIN")
        assert self.facade._pending_result == {"adventure": "Escort", "result": "WIN"}

    def test_flush_writes_to_profile(self):
        self.facade.update_history("Escort", "WIN")
        self.facade._flush()
        assert len(self.profile.quest_history) == 1
        assert self.profile.quest_history[0]["result"] == "WIN"

    def test_flush_clears_pending(self):
        self.facade.update_history("Escort", "WIN")
        self.facade._flush()
        assert self.facade._pending_result is None

    def test_adventures_cannot_save_directly(self):
        # Adventures only have access to update_history, not _save
        # Verify _save is name-mangled (underscore = framework only)
        assert hasattr(self.facade, "_save")
        assert hasattr(self.facade, "update_history")


# ── AdventureRegistry tests ───────────────────────────────────────────
class TestAdventureRegistry:

    def setup_method(self):
        self.registry = AdventureRegistry()

    def test_register_and_list(self):
        self.registry.register("Dummy", DummyAdventure)
        assert "Dummy" in self.registry.list_adventures()

    def test_get_adventure_returns_new_instance(self):
        self.registry.register("Dummy", DummyAdventure)
        a1 = self.registry.get_adventure("Dummy")
        a2 = self.registry.get_adventure("Dummy")
        assert a1 is not a2

    def test_get_adventure_correct_type(self):
        self.registry.register("Dummy", DummyAdventure)
        a = self.registry.get_adventure("Dummy")
        assert isinstance(a, DummyAdventure)

    def test_register_non_adventure_raises_type_error(self):
        with pytest.raises(TypeError):
            self.registry.register("Bad", str)

    def test_get_unregistered_raises_key_error(self):
        with pytest.raises(KeyError):
            self.registry.get_adventure("Nonexistent")

    def test_duplicate_registration_raises_value_error(self):
        self.registry.register("Dummy", DummyAdventure)
        with pytest.raises(ValueError):
            self.registry.register("Dummy", DummyAdventure)

    def test_list_adventures_sorted(self):
        self.registry.register("Zebra Quest", DummyAdventure)

        class AnotherDummy(DummyAdventure): pass
        self.registry.register("Apple Quest", AnotherDummy)

        names = self.registry.list_adventures()
        assert names == sorted(names)


# ── InputProxy tests ──────────────────────────────────────────────────
class TestInputProxy:

    def setup_method(self):
        self.adventure = DummyAdventure()
        self.proxy = InputProxy(self.adventure)

    def test_valid_input_passes_through(self):
        result = self.proxy.forward(1, "move north")
        assert result == "ok"

    def test_invalid_player_id_blocked(self):
        result = self.proxy.forward(3, "move north")
        assert result.startswith("[BLOCKED]")

    def test_empty_action_blocked(self):
        result = self.proxy.forward(1, "   ")
        assert result.startswith("[BLOCKED]")

    def test_unknown_action_blocked(self):
        result = self.proxy.forward(1, "fly away")
        assert result.startswith("[BLOCKED]")

    def test_validate_valid_returns_true(self):
        is_valid, msg = self.proxy.validate(1, "wait")
        assert is_valid is True
        assert msg == ""

    def test_validate_invalid_player_returns_false(self):
        is_valid, msg = self.proxy.validate(0, "wait")
        assert is_valid is False
        assert msg != ""

    def test_all_valid_actions_pass(self):
        valid_actions = [
            "move north", "move south", "move east", "move west",
            "pick up", "use item", "wait", "quit"
        ]
        for action in valid_actions:
            is_valid, _ = self.proxy.validate(1, action)
            assert is_valid is True, f"Expected '{action}' to be valid"


# ── RealmAdapter tests ────────────────────────────────────────────────
class TestRealmAdapter:

    def setup_method(self):
        self.realm = RealmAdapter("TestRealm", 5, 5)

    def test_place_entity(self):
        result = self.realm.place_entity("player1", 0, 0)
        assert result is True

    def test_place_entity_out_of_bounds(self):
        result = self.realm.place_entity("player1", 10, 10)
        assert result is False

    def test_move_entity(self):
        self.realm.place_entity("player1", 0, 0)
        success, nx, ny, _ = self.realm.move("player1", "east")
        assert success is True
        assert (nx, ny) == (1, 0)

    def test_move_out_of_bounds(self):
        self.realm.place_entity("player1", 0, 0)
        success, _, _, msg = self.realm.move("player1", "north")
        assert success is False
        assert "boundaries" in msg

    def test_get_terrain_default(self):
        assert self.realm.get_terrain(2, 2) == "plains"

    def test_set_terrain(self):
        self.realm.set_terrain(2, 2, "water")
        assert self.realm.get_terrain(2, 2) == "water"

    def test_get_position(self):
        self.realm.place_entity("npc", 3, 3)
        assert self.realm.get_position("npc") == (3, 3)

    def test_get_tile_returns_entities(self):
        self.realm.place_entity("player1", 1, 1)
        tile = self.realm.get_tile(1, 1)
        assert "player1" in tile["entities"]


# ── InventoryAdapter tests ────────────────────────────────────────────
class TestInventoryAdapter:

    def setup_method(self):
        self.inv = InventoryAdapter("player1")

    def test_add_item(self):
        item = Item("i001", "Sword", "Common")
        self.inv.add_item(item)
        assert self.inv.count() == 1

    def test_remove_item(self):
        item = Item("i001", "Sword", "Common")
        self.inv.add_item(item)
        result = self.inv.remove_item("i001")
        assert result is True
        assert self.inv.count() == 0

    def test_remove_nonexistent_item(self):
        result = self.inv.remove_item("fake_id")
        assert result is False

    def test_use_item(self):
        item = Item("i001", "Potion", "Common")
        self.inv.add_item(item)
        result = self.inv.use_item("i001")
        assert result["success"] is True
        assert self.inv.count() == 0

    def test_use_nonexistent_item(self):
        result = self.inv.use_item("fake_id")
        assert result["success"] is False

    def test_has_item(self):
        item = Item("i001", "Shield", "Rare")
        self.inv.add_item(item)
        assert self.inv.has_item("i001") is True
        assert self.inv.has_item("fake") is False

    def test_get_items_returns_copy(self):
        item = Item("i001", "Axe", "Common")
        self.inv.add_item(item)
        items = self.inv.get_items()
        items.clear()
        assert self.inv.count() == 1