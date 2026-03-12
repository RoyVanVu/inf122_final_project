from gmae.gmae_core.profile_manager import PlayerProfile, ProfileFacade
from gmae.gmae_core.adventure_registry import AdventureRegistry
from gmae.gmae_core.input_proxy import InputProxy

class GMAECore:
    """
    Main framework class that ties everything together.
    Handles the welcome screen, player profiles, adventure menu,
    turn loop, and profile saving after each adventure ends.
    """

    def __init__(self):
        self.registry = AdventureRegistry()
        self._load_adventures()

    def _load_adventures(self) -> None:
        try:
            from gmae.adventures.escort_across_realm import EscortAcrossRealm
            self.registry.register("Escort Across the Realm", EscortAcrossRealm)
        except Exception as e:
            print(f"[WARNING] Escort failed: {type(e).__name__}: {e}")

        try:
            from gmae.adventures.relic_hunt import RelicHunt
            self.registry.register("Relic Hunt", RelicHunt)
        except Exception as e:
            print(f"[WARNING] Relic Hunt failed: {type(e).__name__}: {e}")

    def _load_player(self, player_number: int) -> ProfileFacade:
        print(f"\n--- Player {player_number} ---")
        while True:
            name = input("Enter your character name: ").strip()
            if name:
                break
            print("Name cannot be empty. Please try again.")

        profile = PlayerProfile.load(name)

        if profile.quest_history:
            print(f"Welcome back, {profile.character_name}! "
                  f"({len(profile.quest_history)} quests completed)")
        else:
            print(f"Welcome, {profile.character_name}! A new adventure awaits.")

        return ProfileFacade(profile)

    def _show_welcome(self) -> None:
        print("\n" + "=" * 50)
        print("   GUILDQUEST MINI-ADVENTURE ENVIRONMENT")
        print("=" * 50)
        print("  Two players. One machine. Infinite glory.")
        print("=" * 50)

    def _show_menu(self) -> None:
        print("\n--- Available Adventures ---")
        adventures = self.registry.list_adventures()
        if not adventures:
            print("  (No adventures loaded)")
            return
        for i, name in enumerate(adventures, 1):
            adventure = self.registry.get_adventure(name)
            print(f"  {i}. {name} — {adventure.get_description()}")

    def _pick_adventure(self):
        adventures = self.registry.list_adventures()
        if not adventures:
            return None

        self._show_menu()
        print()

        while True:
            choice = input("Select an adventure (enter number): ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(adventures):
                    return self.registry.get_adventure(adventures[idx])
            print(f"Please enter a number between 1 and {len(adventures)}.")

    def _display_state(self, state: dict) -> None:
        print("\n" + "-" * 40)
        if "map" in state:
            print(state["map"])
            print("-" * 40)
        for key, value in state.items():
            if key != "map":
                label = key.replace("_", " ").title()
                print(f"  {label}: {value}")

    def _run_turn_loop(self, adventure, proxy: InputProxy,
                       p1: ProfileFacade, p2: ProfileFacade) -> str:
        players = [
            (1, p1.get_name()),
            (2, p2.get_name()),
        ]

        while True:
            for player_id, player_name in players:

                state = adventure.get_state()
                self._display_state(state)

                print(f"\n>>> {player_name}'s turn (Player {player_id})")

                while True:
                    raw = input("Action: ").strip()

                    if raw.lower() == "quit":
                        print("Adventure abandoned.")
                        return "LOSS"

                    result_msg = proxy.forward(player_id, raw)

                    if result_msg.startswith("[BLOCKED]"):
                        print(result_msg)
                    else:
                        print(result_msg)
                        break

                adventure.advance_turn()

                status = adventure.check_completion()
                if status != "ONGOING":
                    final_state = adventure.get_state()
                    self._display_state(final_state)
                    return status

    def _show_result(self, result: str,
                     p1: ProfileFacade, p2: ProfileFacade) -> None:
        print("\n" + "=" * 50)
        if result == "WIN":
            print("  *** VICTORY! Well played, adventurers! ***")
        elif result == "LOSS":
            print("  *** DEFEAT. Better luck next time. ***")
        elif result == "DRAW":
            print("  *** DRAW. An honorable outcome! ***")
        else:
            print(f"  Adventure ended: {result}")
        print(f"  Player 1 ({p1.get_name()}) and "
              f"Player 2 ({p2.get_name()}) — thanks for playing!")
        print("=" * 50)

    def run(self) -> None:
        self._show_welcome()

        p1 = self._load_player(1)
        p2 = self._load_player(2)

        while True:
            print(f"\n\nPlayers: {p1.get_name()} vs {p2.get_name()}")

            adventure = self._pick_adventure()
            if adventure is None:
                print("No adventures available. Exiting.")
                break

            adventure_name = type(adventure).__name__

            adventure.initialize(p1, p2)
            print(f"\nStarting: {adventure_name}...")
            print("Type 'quit' at any time to abandon the adventure.")
            print("Valid actions: move north, move south, move east, "
                  "move west, pick up, use item, wait")

            proxy = InputProxy(adventure)

            result = self._run_turn_loop(adventure, proxy, p1, p2)

            self._show_result(result, p1, p2)

            p1.update_history(adventure_name, result)
            p2.update_history(adventure_name, result)

            p1._save(p1.get_name())
            p2._save(p2.get_name())
            print("Profiles saved.")

            print("\n--- Main Menu ---")
            again = input("Play another adventure? (y/n): ").strip().lower()
            if again != "y":
                print("\nThanks for playing GuildQuest! Farewell, adventurers.")
                break

def main():
    GMAECore().run()


if __name__ == "__main__":
    main()