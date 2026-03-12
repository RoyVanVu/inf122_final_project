import math
from enum import Enum, auto
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any

# ==========================================
# 1. ENUMS & CONSTANTS
# ==========================================

class VisibilityType(Enum):
    PUBLIC = auto()
    PRIVATE = auto()

class Permission(Enum):
    OWNER = auto()        
    COLLABORATOR = auto() 
    VIEWER = auto()       

class TimeDisplayPreference(Enum):
    WORLD_CLOCK = auto()
    REALM_LOCAL = auto()
    BOTH = auto()

# ==========================================
# 2. ABSTRACT BASE CLASSES & INTERFACES
# ==========================================

class GuildEntity(ABC):
    """Abstract Base Class for all major entities to ensure DRY principle."""
    def __init__(self, entity_id: str, name: str, description: str = ""):
        self.id = entity_id
        self.name = name
        self.description = description

    def get_id(self) -> str:
        return self.id

    def get_name(self) -> str:
        return self.name

class Shareable(ABC):
    """Interface for items that can be shared via AccessControl."""
    @abstractmethod
    def can_user_access(self, user: 'User') -> bool:
        pass

    @abstractmethod
    def can_user_edit(self, user: 'User') -> bool:
        pass
    
    @abstractmethod
    def grant_access(self, user: 'User', permission: Permission):
        pass

class LocalTimeRule(ABC):
    """Strategy interface for calculating local time."""
    @abstractmethod
    def convert_to_local(self, world_time: int) -> int:
        pass

    @abstractmethod
    def convert_to_world(self, local_time: int) -> int:
        pass

# ==========================================
# 3. STRATEGY PATTERN (Time Ranges)
# ==========================================
# REFACTORING: Replaces the rigid TimeRange Enum and switch statements

class TimeRangeStrategy(ABC):
    """Strategy interface for calculating time range durations."""
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_duration_minutes(self) -> int:
        pass

class DayRange(TimeRangeStrategy):
    @property
    def name(self) -> str: return "DAY"
    def get_duration_minutes(self) -> int: return 1440

class WeekRange(TimeRangeStrategy):
    @property
    def name(self) -> str: return "WEEK"
    def get_duration_minutes(self) -> int: return 10080

class MonthRange(TimeRangeStrategy):
    @property
    def name(self) -> str: return "MONTH"
    def get_duration_minutes(self) -> int: return 43200

# ==========================================
# 4. REFACTORING: INTRODUCE PARAMETER OBJECT
# ==========================================

class TimeInterval:
    """Encapsulates start and end times to fix the Data Clumps smell."""
    def __init__(self, start_time: int, end_time: int):
        if end_time < start_time:
            raise ValueError("End time cannot be before start time.")
        self.start_time = start_time
        self.end_time = end_time

    def get_duration(self) -> int:
        return self.end_time - self.start_time

    def overlaps_with_range(self, range_start: int, range_end: int) -> bool:
        """Centralized logic for timeline filtering."""
        return self.start_time < range_end and self.end_time > range_start


# ==========================================
# 5. TIME CORE
# ==========================================

class WorldClock:
    """Singleton for tracking global time in minutes."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WorldClock, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.current_world_time = 0 
        self._initialized = True

    @staticmethod
    def get_instance() -> 'WorldClock':
        return WorldClock()

    def get_current_time(self) -> int:
        return self.current_world_time
    
    def advance_time(self, minutes: int) -> None:
        if minutes > 0:
            self.current_world_time += minutes

    def format_time(self, minutes: int) -> str:
        days = minutes // 1440
        remaining_minutes = minutes % 1440
        hours = remaining_minutes // 60
        mins = remaining_minutes % 60
        return f"Day {days}, {hours:02d}:{mins:02d}"

class FixedOffsetRule(LocalTimeRule):
    def __init__(self, offset_minutes: int):
        self.offset = offset_minutes

    def convert_to_local(self, world_time: int) -> int:
        return world_time + self.offset

    def convert_to_world(self, local_time: int) -> int:
        return local_time - self.offset

class MultiplierRule(LocalTimeRule):
    def __init__(self, multiplier: float, base_offset: int = 0):
        self.multiplier = multiplier
        self.base_offset = base_offset

    def convert_to_local(self, world_time: int) -> int:
        return int((world_time * self.multiplier) + self.base_offset)

    def convert_to_world(self, local_time: int) -> int:
        return int((local_time - self.base_offset) / self.multiplier)

# ==========================================
# 6. REALM & SETTINGS
# ==========================================

class Realm(GuildEntity):
    def __init__(self, entity_id: str, name: str, x: int, y: int, time_rule: LocalTimeRule):
        super().__init__(entity_id, name)
        self.coordinates = (x, y)
        self.time_rule = time_rule
        self.adjacent_realms: List[str] = [] 

    def get_local_time(self, world_time: int) -> int:
        return self.time_rule.convert_to_local(world_time)

    def add_connection(self, realm_id: str) -> None:
        if realm_id not in self.adjacent_realms:
            self.adjacent_realms.append(realm_id)

    def is_connected_to(self, realm_id: str) -> bool:
        return realm_id in self.adjacent_realms

class UserSettings:
    def __init__(self):
        self.current_realm: Optional[Realm] = None
        self.time_pref: TimeDisplayPreference = TimeDisplayPreference.WORLD_CLOCK

class TimeManager:
    """Helper Singleton for display logic."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TimeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self._initialized = True
    
    @staticmethod
    def get_instance():
        return TimeManager()

    def display_time(self, minutes: int, context: Any = None) -> str:
        clock = WorldClock.get_instance()
        
        if isinstance(context, User):
            if context.settings.time_pref == TimeDisplayPreference.REALM_LOCAL and context.settings.current_realm:
                local_time = context.settings.current_realm.get_local_time(minutes)
                return f"{clock.format_time(local_time)} (Local)"
            elif context.settings.time_pref == TimeDisplayPreference.BOTH and context.settings.current_realm:
                local_time = context.settings.current_realm.get_local_time(minutes)
                return f"{clock.format_time(minutes)} (World) | {clock.format_time(local_time)} (Local)"
        
        return clock.format_time(minutes)

# ==========================================
# 7. DOMAIN: ACCESS CONTROL & USERS
# ==========================================

class AccessControl:
    def __init__(self, user: 'User', permission: Permission, resource: Shareable):
        self.user = user
        self.permission = permission
        self.resource = resource

    def allows_edit(self) -> bool:
        return self.permission in (Permission.COLLABORATOR, Permission.OWNER)

class User:
    def __init__(self, user_id: str, username: str):
        self.id = user_id
        self.username = username
        self.settings = UserSettings()
        self.owned_campaigns: List['Campaign'] = []
        self.shared_access_list: List[AccessControl] = []
        self.characters: List['Character'] = []

    def create_campaign(self, name: str, is_public: bool) -> 'Campaign':
        # PATTERN: Delegate to Factory Method
        camp = CampaignFactory.create_campaign(name, self, is_public)
        self.owned_campaigns.append(camp)
        return camp

    def share_resource(self, resource: Shareable, target_user: 'User', perm_level: Permission):
        acl = AccessControl(target_user, perm_level, resource)
        target_user.shared_access_list.append(acl)
        resource.grant_access(target_user, perm_level)

# ==========================================
# 8. DOMAIN: RPG MECHANICS
# ==========================================

class Item(GuildEntity):
    def __init__(self, item_id: str, name: str, rarity: str):
        super().__init__(item_id, name)
        self.rarity = rarity

class Inventory:
    def __init__(self):
        self.items: Dict[str, Item] = {} 

    def add(self, item: Item):
        self.items[item.id] = item

    def remove(self, item_id: str):
        if item_id in self.items:
            del self.items[item_id]

class Character(GuildEntity):
    def __init__(self, char_id: str, name: str, char_class: str, level: int, owner: User):
        super().__init__(char_id, name)
        self.char_class = char_class
        self.level = level
        self.owner = owner
        self.inventory = Inventory()

# PATTERN: Template Method
class InventoryEffect(ABC):
    def __init__(self, items: List[Item]):
        self.items = items
        self.executed = False

    def apply(self, characters: List[Character]):
        # Template method skeleton
        if self.executed:
            return
        
        for char in characters:
            for item in self.items:
                self._apply_item_effect(char, item)
        
        self.executed = True

    @abstractmethod
    def _apply_item_effect(self, character: Character, item: Item):
        pass

# REFACTORING: Replace Conditional with Polymorphism
class AddInventoryEffect(InventoryEffect):
    def _apply_item_effect(self, character: Character, item: Item):
        character.inventory.add(item)
        print(f"Added {item.name} to {character.name}'s inventory.")

class RemoveInventoryEffect(InventoryEffect):
    def _apply_item_effect(self, character: Character, item: Item):
        character.inventory.remove(item.id)
        print(f"Removed {item.name} from {character.name}'s inventory.")

# ==========================================
# 9. DOMAIN: CAMPAIGNS & EVENTS
# ==========================================

class CampaignFactory:
    """PATTERN: Factory Method - Centralizes Campaign creation rules."""
    @staticmethod
    def create_campaign(name: str, owner: User, is_public: bool) -> 'Campaign':
        vis = VisibilityType.PUBLIC if is_public else VisibilityType.PRIVATE
        camp_id = f"camp_{name.replace(' ', '_')}_{owner.id}"
        return Campaign(camp_id, name, owner, vis)

class Campaign(GuildEntity, Shareable):
    def __init__(self, camp_id: str, name: str, owner: User, visibility: VisibilityType):
        super().__init__(camp_id, name)
        self.owner = owner
        self.visibility = visibility
        self.events: List['QuestEvent'] = []
        self.access_list: Dict[str, AccessControl] = {} 
        # REFACTORING: Removed Speculative Generality (Empty stub methods deleted)

    def add_event(self, event: 'QuestEvent'):
        self.events.append(event)

    def grant_access(self, user: User, permission: Permission):
        acl = AccessControl(user, permission, self)
        self.access_list[user.id] = acl

    def can_user_access(self, user: User) -> bool:
        if user == self.owner: return True
        if self.visibility == VisibilityType.PUBLIC: return True
        return user.id in self.access_list

    def can_user_edit(self, user: User) -> bool:
        if user == self.owner: return True
        if user.id in self.access_list:
            return self.access_list[user.id].allows_edit()
        return False

class QuestEvent(GuildEntity, Shareable):
    # Notice the TimeInterval parameter object is used here
    def __init__(self, event_id: str, name: str, time_interval: TimeInterval, location: Realm, parent: Campaign):
        super().__init__(event_id, name)
        self.interval = time_interval
        self.location = location
        self.parent_campaign = parent
        self.inventory_effects: List[InventoryEffect] = []
        self.participants: List[Character] = []
        self.completed = False
        self.access_list: Dict[str, AccessControl] = {}

    def add_inventory_effect(self, effect: InventoryEffect):
        self.inventory_effects.append(effect)
        
    def mark_complete(self):
        self.completed = True

    def update_details(self, new_name: str, new_start: int, new_end: int, user: User):
        if not self.can_user_edit(user):
            raise PermissionError(f"User {user.username} cannot edit event {self.name}")
        self.name = new_name
        self.interval = TimeInterval(new_start, new_end)
        print(f"Event updated by {user.username}")

    def grant_access(self, user: User, permission: Permission):
        acl = AccessControl(user, permission, self)
        self.access_list[user.id] = acl

    def can_user_access(self, user: User) -> bool:
        if user.id in self.access_list: return True
        return self.parent_campaign.can_user_access(user)

    def can_user_edit(self, user: User) -> bool:
        if user.id in self.access_list:
            return self.access_list[user.id].allows_edit()
        return self.parent_campaign.can_user_edit(user)

# ==========================================
# 10. CONTROLLERS & FACADE
# ==========================================

class TimelineGenerator:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TimelineGenerator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self._initialized = True

    @staticmethod
    def get_instance():
        return TimelineGenerator()

    def generate(self, campaign: Campaign, start_time: int, time_strategy: TimeRangeStrategy) -> List[QuestEvent]:
        end_time = start_time + time_strategy.get_duration_minutes()
        
        # Leverages the TimeInterval Parameter Object
        result_list = [
            e for e in campaign.events 
            if e.interval.overlaps_with_range(start_time, end_time)
        ]
        
        result_list.sort(key=lambda x: x.interval.start_time)
        return result_list

class GameController:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GameController, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized: return
        self._initialized = True

    @staticmethod
    def get_instance():
        return GameController()

    def complete_quest(self, event: QuestEvent):
        if event.completed:
            print(f"Quest {event.name} is already complete.")
            return

        event.mark_complete()
        print(f"Quest '{event.name}' marked as complete.")
        for effect in event.inventory_effects:
            effect.apply(event.participants)


class GuildQuestFacade:
    """PATTERN: Facade - Provides a simplified UI boundary to the complex backend domain."""
    def __init__(self):
        self.clock = WorldClock.get_instance()
        self.time_manager = TimeManager.get_instance()
        self.timeline_gen = TimelineGenerator.get_instance()
        self.users_db = {}
        self.all_realms = {}
        self.current_user: Optional[User] = None

    def initialize_demo_world(self):
        self.clock.current_world_time = 1000  
        
        earth = Realm("r_earth", "Earth", 0, 0, FixedOffsetRule(0))
        mars = Realm("r_mars", "Mars", 10, 10, MultiplierRule(1.03))
        earth.add_connection(mars.id)
        self.all_realms = {earth.id: earth, mars.id: mars}

        alice = User("u1", "Alice")
        alice.settings.current_realm = earth
        
        bob = User("u2", "Bob")
        bob.settings.current_realm = mars
        bob.settings.time_pref = TimeDisplayPreference.REALM_LOCAL

        self.users_db = {alice.id: alice, bob.id: bob}
        self.current_user = alice
        self.current_user.create_campaign("Starter Campaign", is_public=True)

    def switch_user(self, uid: str) -> bool:
        if uid in self.users_db:
            self.current_user = self.users_db[uid]
            return True
        return False

    def create_campaign(self, name: str, is_public: bool) -> Campaign:
        return self.current_user.create_campaign(name, is_public)

    def get_accessible_campaign(self, camp_id: str) -> Optional[Campaign]:
        for c in self.current_user.owned_campaigns:
            if c.id == camp_id: return c
        for acl in self.current_user.shared_access_list:
            if isinstance(acl.resource, Campaign) and acl.resource.id == camp_id:
                return acl.resource
        return None

    def advance_time(self, minutes: int) -> str:
        self.clock.advance_time(minutes)
        return self.clock.format_time(self.clock.get_current_time())


# ==========================================
# 11. UI ROUTING (Extracted Methods Refactoring)
# ==========================================

def print_separator():
    print("-" * 50)

def _handle_switch_user(app: GuildQuestFacade):
    print("\nAvailable Users:")
    for u_id, u in app.users_db.items():
        print(f"- {u.username} (ID: {u_id})")
    uid = input("Enter User ID to switch to: ").strip()
    if app.switch_user(uid):
        print(f"Switched to {app.current_user.username}")
    else:
        print("User not found.")

def _handle_create_campaign(app: GuildQuestFacade):
    name = input("Campaign Name: ").strip()
    vis_input = input("Public? (y/n): ").lower()
    camp = app.create_campaign(name, vis_input == 'y')
    print(f"Campaign '{camp.name}' created.")

def _handle_list_campaigns(app: GuildQuestFacade):
    print("\n--- Owned Campaigns ---")
    if not app.current_user.owned_campaigns:
        print("No owned campaigns.")
    for c in app.current_user.owned_campaigns:
        vis = "PUBLIC" if c.visibility == VisibilityType.PUBLIC else "PRIVATE"
        print(f"ID: {c.id} | Name: {c.name} | Vis: {vis}")
    
    print("\n--- Shared With Me ---")
    if not app.current_user.shared_access_list:
        print("No shared campaigns.")
    for acl in app.current_user.shared_access_list:
        if isinstance(acl.resource, Campaign):
            c = acl.resource
            print(f"ID: {c.id} | Name: {c.name} | Owner: {c.owner.username} | Perm: {acl.permission.name}")

def _handle_add_event(app: GuildQuestFacade):
    camp_id = input("Enter Campaign ID to add event to: ").strip()
    target_camp = app.get_accessible_campaign(camp_id)
    
    if target_camp and target_camp.can_user_edit(app.current_user):
        e_name = input("Event Name: ").strip()
        try:
            start_offset = int(input("Start Time (minutes from NOW): "))
            duration = int(input("Duration (minutes): "))
            
            start_time = app.clock.get_current_time() + start_offset
            end_time = start_time + duration
            
            # Utilizing the Parameter Object
            interval = TimeInterval(start_time, end_time)
            loc = app.current_user.settings.current_realm
            
            event = QuestEvent(f"evt_{start_time}", e_name, interval, loc, target_camp)
            target_camp.add_event(event)
            print("Event added successfully.")
        except ValueError as e:
            print(f"Error creating event: {e}")
    else:
        print("Campaign not found or you lack edit permission.")

def _handle_view_timeline(app: GuildQuestFacade):
    camp_id = input("Enter Campaign ID to view: ").strip()
    target_camp = app.get_accessible_campaign(camp_id)

    if target_camp and target_camp.can_user_access(app.current_user):
        print("Range: [1] Day, [2] Week, [3] Month")
        r_choice = input("Select Range: ")
        
        # Instantiating the appropriate Strategy
        strategy: TimeRangeStrategy = WeekRange() 
        if r_choice == '1': strategy = DayRange()
        elif r_choice == '3': strategy = MonthRange()
        
        timeline = app.timeline_gen.generate(target_camp, app.clock.get_current_time(), strategy)
        
        print(f"\n--- Timeline ({strategy.name}) ---")
        if not timeline:
            print("No events in this range.")
        for evt in timeline:
            time_str = app.time_manager.display_time(evt.interval.start_time, app.current_user)
            print(f"[{time_str}] {evt.name} (@ {evt.location.name})")
    else:
        print("Campaign not found or access denied.")

def _handle_advance_time(app: GuildQuestFacade):
    try:
        mins = int(input("Minutes to advance: "))
        new_time = app.advance_time(mins)
        print(f"Time advanced. New time: {new_time}")
    except ValueError:
        print("Invalid number.")

def _handle_change_settings(app: GuildQuestFacade):
    print("Select Realm:")
    for rid, r in app.all_realms.items():
        print(f"- {r.name} (ID: {rid})")
    rid = input("Enter Realm ID: ").strip()
    if rid in app.all_realms:
        app.current_user.settings.current_realm = app.all_realms[rid]
        print(f"Moved to {app.all_realms[rid].name}")
    
    print("Time Display: [1] World, [2] Local, [3] Both")
    kp = input("Choice: ")
    if kp == '1': app.current_user.settings.time_pref = TimeDisplayPreference.WORLD_CLOCK
    elif kp == '2': app.current_user.settings.time_pref = TimeDisplayPreference.REALM_LOCAL
    elif kp == '3': app.current_user.settings.time_pref = TimeDisplayPreference.BOTH

def _handle_share_campaign(app: GuildQuestFacade):
    camp_id = input("Enter Campaign ID to share: ").strip()
    target_camp = next((c for c in app.current_user.owned_campaigns if c.id == camp_id), None)
    
    if target_camp:
        target_uid = input("Enter User ID to share with: ").strip()
        if target_uid in app.users_db:
            target_u = app.users_db[target_uid]
            print("Permission: [1] Viewer, [2] Collaborator")
            p_choice = input("Choice: ")
            perm = Permission.COLLABORATOR if p_choice == '2' else Permission.VIEWER
            
            app.current_user.share_resource(target_camp, target_u, perm)
            print(f"Shared {target_camp.name} with {target_u.username}")
        else:
            print("Target user not found.")
    else:
        print("You don't own a campaign with that ID.")

def main():
    app = GuildQuestFacade()
    app.initialize_demo_world()
    
    print("=== GuildQuest Interactive CLI ===\n")

    while True:
        print_separator()
        print(f"Current User: {app.current_user.username} (ID: {app.current_user.id})")
        print(f"World Time: {app.clock.format_time(app.clock.get_current_time())}")
        loc_name = app.current_user.settings.current_realm.name if app.current_user.settings.current_realm else 'Unknown'
        print(f"Location: {loc_name}")
        print_separator()
        
        print("1. Switch User")
        print("2. Create Campaign")
        print("3. List Campaigns (Owned & Shared)")
        print("4. Add Event to Campaign")
        print("5. View Timeline")
        print("6. Advance World Time")
        print("7. Change Settings (Realm/Time Pref)")
        print("8. Share Campaign")
        print("0. Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == '0':
            print("Exiting The APP. Goodbye!")
            break
        elif choice == '1':
            _handle_switch_user(app)
        elif choice == '2':
            _handle_create_campaign(app)
        elif choice == '3':
            _handle_list_campaigns(app)
        elif choice == '4':
            _handle_add_event(app)
        elif choice == '5':
            _handle_view_timeline(app)
        elif choice == '6':
            _handle_advance_time(app)
        elif choice == '7':
            _handle_change_settings(app)
        elif choice == '8':
            _handle_share_campaign(app)
        else:
            print("Invalid command.")

if __name__ == "__main__":
    main()