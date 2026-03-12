from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
from abc import ABC, abstractmethod

# 1. ENUMERATIONS
class Rarity(Enum):
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    LEGENDARY = "Legendary"

class ItemType(Enum):
    CONSUMABLE = "Consumable"
    WEAPON = "Weapon"
    ARMOR = "Armor"
    COSMETIC = "Cosmetic"

class CharacterClass(Enum):
    KNIGHT = "Knight"
    MAGE = "Mage"
    SHIELD = "Shield"
    ROGUE = "Rogue"
    CLERIC = "Cleric"
    DEMON = "Demon"

class Permission(Enum):
    VIEW_ONLY = "View-only"
    COLLABORATIVE = "Collaborative"

class Visibility(Enum):
    PUBLIC = "Public"
    PRIVATE = "Private"

class TimeDisplay(Enum):
    WORLD = "World"
    REALM = "Realm"
    BOTH = "Both"

class Theme(Enum):
    CLASSIC = "Classic"
    MODERN = "Modern"

@dataclass
class Item:
    # Represents a in-game item
    name: str
    rarity: Rarity
    type: ItemType
    description: str

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Item name cannot be empty")
        if not self.description.strip():
            raise ValueError("Item description cannot be empty")
        
    def __str__(self):
        return f"[{self.rarity.value}] {self.name}: {self.description} ({self.type.value})"
    
    def __repr__(self):
        return f"Item(name='{self.name}', rarity={self.rarity}, type={self.type})"
    
# =============================================================
# [REFACTORING: Introduce Parameter Object - AI Assist]
# Bundles the 4 loose add_quest_event() arguments into one object.
# Validation that was scattered across Campaign and QuestEvent is
# now centralized here, fixing the Long Parameter List smell.
# =============================================================
@dataclass
class EventSpec:
    """Value object that bundles all parameters needed to create a QuestEvent."""
    name: str
    start_time: 'WorldClock'
    location: 'Realm'
    end_time: Optional['WorldClock'] = None

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Event name cannot be empty")
        if self.start_time is None:
            raise ValueError("start_time cannot be None")
        if self.location is None:
            raise ValueError("location cannot be None")
        if self.end_time and self.end_time < self.start_time:
            raise ValueError("end_time cannot be before start_time")
# =============================================================

# =============================================================
# [PATTERN: Observer] [SMELL: Divergent Change — fixed - AI Assist]
# SMELL: QuestEvent was changing for multiple unrelated reasons:
#   - Business logic (adding participants, granting items)
#   - Logging (who records what happened?)
#   - Notifications (who gets alerted?)
# Every new "reaction" required editing QuestEvent itself.
#
# FIX: QuestEvent (Subject) now just calls self._notify().
# Concrete Observers handle their own reactions independently,
# so QuestEvent never needs to change when new reactions are added.
# =============================================================
class QuestEventObserver(ABC):
    """Abstract base for anything that reacts to QuestEvent mutations."""
    @abstractmethod
    def on_event(self, quest_event: 'QuestEvent', action: str, detail: str) -> None:
        pass


class CampaignLog(QuestEventObserver):
    """Concrete Observer — records an ordered history of all event changes."""
    def __init__(self):
        self.entries: List[str] = []

    def on_event(self, quest_event: 'QuestEvent', action: str, detail: str) -> None:
        entry = f"[LOG] {quest_event.name} | {action}: {detail}"
        self.entries.append(entry)

    def print_log(self) -> None:
        if not self.entries:
            print("  (campaign log is empty)")
            return
        for entry in self.entries:
            print(f"  {entry}")

    def __str__(self):
        return f"CampaignLog({len(self.entries)} entries)"


class EventNotifier(QuestEventObserver):
    """Concrete Observer — prints a live alert whenever a QuestEvent changes."""
    def __init__(self, owner_username: str):
        self.owner_username = owner_username

    def on_event(self, quest_event: 'QuestEvent', action: str, detail: str) -> None:
        print(f"  [NOTIFY → {self.owner_username}] '{quest_event.name}' updated: {detail}")

    def __str__(self):
        return f"EventNotifier(owner='{self.owner_username}')"
# =============================================================
    
# === DESIGN PATTERN 1: FACTORY METHOD (CHARACTER CREATION) ===
# Rationale: Decouples User from concrete Character subclasses.
class Character(ABC): 
    def __init__(self, name: str, level: int = 1):
        if not name.strip():
            raise ValueError("Character name cannot be empty")
        if level < 1:
            raise ValueError("Character level must be at least 1")
        self.name = name
        self.level = level
        self.inventory: List[Item] = []
        self.starting_gear() 

    @abstractmethod
    def starting_gear(self):
        pass

    @property
    @abstractmethod
    def char_class_name(self) -> str:  
        pass

    def add_item(self, item: Item):
        self.inventory.append(item)
    
    def remove_item(self, item: Item):
        if item in self.inventory: self.inventory.remove(item)
        else: raise ValueError(f"Item '{item.name}' not found")
    
    def update_item(self, old_item: Item, new_item: Item):
        if old_item in self.inventory:
            index = self.inventory.index(old_item)
            self.inventory[index] = new_item
        else:
            raise ValueError(f"Item '{old_item.name}' not found in inventory")

    def level_up(self):
        self.level += 1

    def __str__(self):
        return f"{self.name}, the Level {self.level} {self.char_class_name} ({len(self.inventory)} items)"
    
    def __repr__(self):
        return f"Character(name='{self.name}', class={self.char_class_name}, level={self.level}, items={len(self.inventory)})"

class KnightCharacter(Character):
    @property
    def char_class_name(self): return "Knight" 
    def starting_gear(self):
        self.add_item(Item("Basic Shield", Rarity.COMMON, ItemType.ARMOR, "Wooden shield"))

class MageCharacter(Character):
    @property
    def char_class_name(self): return "Mage"  
    def starting_gear(self):
        self.add_item(Item("Wand", Rarity.COMMON, ItemType.WEAPON, "Wooden wand"))

class RogueCharacter(Character): 
    @property
    def char_class_name(self): return "Rogue"  
    def starting_gear(self):
        self.add_item(Item("Rusty Dagger", Rarity.COMMON, ItemType.WEAPON, "A simple blade"))

class CharacterCreator(ABC):
    @abstractmethod
    def create_character(self, name: str, level: int) -> Character: pass

class KnightCreator(CharacterCreator):
    def create_character(self, name: str, level: int) -> Character:
        return KnightCharacter(name, level)

class MageCreator(CharacterCreator):
    def create_character(self, name: str, level: int) -> Character:
        return MageCharacter(name, level)

class RogueCreator(CharacterCreator): # Added for run_demo()
    def create_character(self, name: str, level: int) -> Character:
        return RogueCharacter(name, level)
# ===================================================

# 2. WORLDCLOCK
@dataclass
class WorldClock:
    # Represents in-game time with automatic normalization
    days: int = 0
    hours: int = 0
    minutes: int = 0

    def __post_init__(self):
        if self.days < 0 or self.hours < 0 or self.minutes < 0:
            raise ValueError("Times values cannot be negative")
        self._normalize()

    def _normalize(self):
        extra_hours, self.minutes = divmod(self.minutes, 60)
        self.hours += extra_hours
        extra_days, self.hours = divmod(self.hours, 24)
        self.days += extra_days
    
    def total_minutes(self) -> int:
        return (self.days * 24 * 60) + (self.hours * 60) + self.minutes
    
    def addMinutes(self, minutes: int) -> 'WorldClock':
        return WorldClock(self.days, self.hours, self.minutes + minutes)
    
    def addHours(self, hours: int) -> 'WorldClock':
        return WorldClock(self.days, self.hours + hours, self.minutes)
    
    def addDays(self, days: int) -> 'WorldClock':
        return WorldClock(self.days + days, self.hours, self.minutes)
    
    def __lt__(self, other):
        return self.total_minutes() < other.total_minutes()
    
    def __le__(self, other):
        return self.total_minutes() <= other.total_minutes()
    
    def __eq__(self, other):
        return self.total_minutes() == other.total_minutes()
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __gt__(self, other):
        return self.total_minutes() > other.total_minutes()
    
    def __ge__(self, other):
        return self.total_minutes() >= other.total_minutes()
    
    def __add__(self, other):
        return WorldClock(
            self.days + other.days,
            self.hours + other.hours,
            self.minutes + other.minutes
        )

    def __str__(self):
        return f"Day {self.days}, {self.hours:02d}:{self.minutes:02d}"
    
    def __repr__(self):
        return f"WorldClock(days={self.days}, hours={self.hours}, minutes={self.minutes})"

class Realm:
    """Represents a game world location with local time rules."""
    def __init__(self, name: str, map_id: int, description: str = "", 
                 offset: int = 0, multiplier: int = 1):
        if not name.strip():
            raise ValueError("Realm name cannot be empty")
        if map_id < 0:
            raise ValueError("map_id must be non-negative")
        if multiplier <= 0:
            raise ValueError("time multiplier must be positive")
        
        self.name: str = name
        self.map_id: int = map_id
        self.description: str = description
        self.local_time_offset: int = offset  
        self.local_time_multiplier: int = multiplier 
        self.map_neighbors: List['Realm'] = []  
    
    def add_neighbor(self, neighbor: 'Realm'):
        if neighbor not in self.map_neighbors:
            self.map_neighbors.append(neighbor)
            neighbor.add_neighbor(self) 
    
    def remove_neighbor(self, neighbor: 'Realm'):
        if neighbor in self.map_neighbors:
            self.map_neighbors.remove(neighbor)
            if self in neighbor.map_neighbors:
                neighbor.map_neighbors.remove(self)
    
    def convert_to_local_time(self, world_time: WorldClock) -> WorldClock:
        total_minutes = world_time.total_minutes()
        local_minutes = (total_minutes * self.local_time_multiplier) + self.local_time_offset
        return WorldClock(minutes=local_minutes)
    
    def __str__(self):
        neighbor_names = [n.name for n in self.map_neighbors]
        return f"Realm: {self.name} (ID: {self.map_id}, Neighbors: {neighbor_names})"
    
    def __repr__(self):
        return f"Realm(name='{self.name}', map_id={self.map_id}, neighbors={len(self.map_neighbors)})"
    
class Settings:  
    """User preferences for app display and current location."""  
    def __init__(self, current_realm: Realm, 
                 app_theme: Theme = Theme.CLASSIC,
                 time_display: TimeDisplay = TimeDisplay.WORLD):
        if current_realm is None:
            raise ValueError("current_realm cannot be None")
        
        self.current_realm: Realm = current_realm
        self.app_theme: Theme = app_theme
        self.time_display: TimeDisplay = time_display
    
    def set_realm(self, realm: Realm):
        if realm is None:
            raise ValueError("Realm cannot be None")
        self.current_realm = realm
    
    def set_theme(self, theme: Theme):
        self.app_theme = theme
    
    def set_time_display(self, display_mode: TimeDisplay):
        self.time_display = display_mode
    
    def __str__(self):
        return f"Settings(Realm: {self.current_realm.name}, Theme: {self.app_theme.value}, Display: {self.time_display.value})"
    
    def __repr__(self):
        return f"Settings(current_realm={self.current_realm.name}, theme={self.app_theme}, display={self.time_display})"

# class Character:
#     """Represents a playable character with inventory."""
#     def __init__(self, name: str, char_class: CharacterClass, level: int = 1):
#         if not name.strip():
#             raise ValueError("Character name cannot be empty")
#         if level < 1:
#             raise ValueError("Character level must be at least 1")
        
#         self.name: str = name
#         self.char_class: CharacterClass = char_class
#         self.level: int = level
#         self.inventory: List[Item] = []
    
#     def add_item(self, item: Item):
#         self.inventory.append(item)
    
#     def remove_item(self, item: Item):
#         if item in self.inventory:
#             self.inventory.remove(item)
#         else:
#             raise ValueError(f"Item '{item.name}' not found in inventory")
    
#     def update_item(self, old_item: Item, new_item: Item):
#         if old_item in self.inventory:
#             index = self.inventory.index(old_item)
#             self.inventory[index] = new_item
#         else:
#             raise ValueError(f"Item '{old_item.name}' not found in inventory")
    
#     def level_up(self):
#         self.level += 1
    
#     def __str__(self):
#         return f"{self.name}, the Level {self.level} {self.char_class.value} ({len(self.inventory)} items)"
    
#     def __repr__(self):
#         return f"Character(name='{self.name}', class={self.char_class}, level={self.level}, items={len(self.inventory)})"
    
class QuestEvent:
    """Represents a scheduled in-game event."""
    def __init__(self, name: str, start_time: WorldClock, location: Realm, 
                 end_time: Optional[WorldClock] = None):
        if not name.strip():
            raise ValueError("QuestEvent name cannot be empty")
        if start_time is None:
            raise ValueError("start_time cannot be None")
        if location is None:
            raise ValueError("location cannot be None")
        if end_time and end_time < start_time:
            raise ValueError("end_time cannot be before start_time")
        
        self.name: str = name
        self.start_time: WorldClock = start_time
        self.end_time: Optional[WorldClock] = end_time
        self.location: Realm = location
        self.characters: List[Character] = []
        self._observers: List[QuestEventObserver] = []   # Observer registry - AI Assist

    # =============================================================
    # [PATTERN: Observer - AI Assist] — Subject interface
    # =============================================================
    def attach(self, observer: QuestEventObserver) -> None:
        """Register an observer to receive notifications."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: QuestEventObserver) -> None:
        """Remove a previously registered observer."""
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify(self, action: str, detail: str) -> None:
        """Broadcast a change to all registered observers."""
        for observer in self._observers:
            observer.on_event(self, action, detail)
    # =============================================================
    
    def display_global_time(self) -> str:
        result = str(self.start_time)
        if self.end_time:
            result += f" to {self.end_time}"
        return result
    
    def display_local_time(self) -> str:
        local_start = self.location.convert_to_local_time(self.start_time)
        result = f"{local_start} (Local: {self.location.name})"
        
        if self.end_time:
            local_end = self.location.convert_to_local_time(self.end_time)
            result += f" to {local_end}"
        
        return result
    
    # In add_participant — add the notify call after appending - AI Assist
    def add_participant(self, character: Character):
        if character not in self.characters:
            self.characters.append(character)
            self._notify("participant_added", f"{character.name} joined the event")  # ADD
    
    # In remove_participant — add the notify call after removing - AI Assist
    def remove_participant(self, character: Character):
        if character in self.characters:
            self.characters.remove(character)
            self._notify("participant_removed", f"{character.name} left the event")  # ADD
        else:
            raise ValueError(f"{character.name} is not part of this event")
    
    # In grant_item — add the notify call after add_item - AI Assist
    def grant_item(self, character: Character, item: Item):
        if character in self.characters:
            character.add_item(item)
            self._notify("item_granted", f"{item.name} granted to {character.name}")  # ADD
        else:
            raise ValueError(f"{character.name} is not part of this event")
    
    # In remove_item — add the notify call after remove_item - AI Assist
    def remove_item(self, character: Character, item: Item):
        if character in self.characters:
            character.remove_item(item)
            self._notify("item_removed", f"{item.name} removed from {character.name}")  # ADD
        else:
            raise ValueError(f"{character.name} is not part of this event")
    
    def __str__(self):
        participant_count = len(self.characters)
        return f"Event: {self.name} at {self.location.name} (Global: {self.start_time}, {participant_count} participants)"
    
    def __repr__(self):
        return f"QuestEvent(name='{self.name}', location={self.location.name}, participants={len(self.characters)})"
    
class Campaign:
    """Container for quest events with visibility settings."""
    def __init__(self, name: str, visibility: Visibility = Visibility.PRIVATE):
        if not name.strip():
            raise ValueError("Campaign name cannot be empty")
        
        self.name: str = name
        self.visibility: Visibility = visibility
        self.events: List[QuestEvent] = []
    
    # =============================================================
    # [REFACTORING: Introduce Parameter Object - AI Assist]
    # =============================================================
    # def add_quest_event(self, name: str, start_time: WorldClock, location: Realm,
    #                    end_time: Optional[WorldClock] = None) -> QuestEvent:
    #     new_event = QuestEvent(name, start_time, location, end_time)
    #     self.events.append(new_event)
    #     return new_event

    def add_quest_event(self, spec: EventSpec) -> QuestEvent:          # [REFACTORING]
        new_event = QuestEvent(spec.name, spec.start_time, spec.location, spec.end_time)
        self.events.append(new_event)
        return new_event
    # =============================================================
    
    def remove_quest_event(self, event: QuestEvent):
        if event in self.events:
            self.events.remove(event)
        else:
            raise ValueError(f"Event '{event.name}' not found in campaign")
    
    def update_quest_event(self, event: QuestEvent):
        if event not in self.events:
            raise ValueError(f"Event '{event.name}' not found in campaign")
    
    def share_quest_event(self, event: QuestEvent):
        if event not in self.events:
            raise ValueError(f"Event '{event.name}' not found in campaign")
        raise NotImplementedError("Sharing will be implemented in Phase 4")
    
    def __str__(self):
        return f"Campaign: {self.name} [{self.visibility.value}] ({len(self.events)} events)"
    
    def __repr__(self):
        return f"Campaign(name='{self.name}', visibility={self.visibility}, events={len(self.events)})"

class SharedCampaign:
    """Links a user to a campaign they do not own with specific permissions."""
    def __init__(self, user: 'User', campaign: 'Campaign', permission: Permission):
        if user is None:
            raise ValueError("User cannot be None")
        if campaign is None:
            raise ValueError("Campaign cannot be None")
        if permission is None:
            raise ValueError("Permission cannot be None")
        
        self.user: User = user
        self.campaign: Campaign = campaign
        self.permission: Permission = permission
    
    def __str__(self):
        return f"Shared: {self.campaign.name} → {self.user.username} ({self.permission.value})"
    
    def __repr__(self):
        return f"SharedCampaign(user='{self.user.username}', campaign='{self.campaign.name}', permission={self.permission})"
    
class SharedEvent:
    """Links a user to a specific event with specific permissions."""  
    def __init__(self, user: 'User', event: 'QuestEvent', permission: Permission):
        if user is None:
            raise ValueError("User cannot be None")
        if event is None:
            raise ValueError("QuestEvent cannot be None")
        if permission is None:
            raise ValueError("Permission cannot be None")
        
        self.user: User = user
        self.event: QuestEvent = event
        self.permission: Permission = permission
    
    def __str__(self):
        return f"Shared: {self.event.name} → {self.user.username} ({self.permission.value})"
    
    def __repr__(self):
        return f"SharedEvent(user='{self.user.username}', event='{self.event.name}', permission={self.permission})"

class User:
    """Top-level class managing campaigns and characters."""
    def __init__(self, username: str):
        if not username.strip():
            raise ValueError("Username cannot be empty")
        
        self.username: str = username
        self.campaigns: List[Campaign] = []
        self.characters: List[Character] = []
        self.settings: Optional[Settings] = None
        self.shared_campaigns_received: List[SharedCampaign] = []
        self.shared_events_received: List[SharedEvent] = []
    
    def add_campaign(self, name: str, visibility: Visibility = Visibility.PRIVATE) -> Campaign:
        new_campaign = Campaign(name, visibility)
        self.campaigns.append(new_campaign)
        return new_campaign
    
    def remove_campaign(self, campaign: Campaign):
        if campaign in self.campaigns:
            self.campaigns.remove(campaign)
        else:
            raise ValueError(f"Campaign '{campaign.name}' not found")
    
    def update_campaign(self, campaign: Campaign):
        if campaign not in self.campaigns:
            raise ValueError(f"Campaign '{campaign.name}' not found")
    
    def share_campaign(self, target_user: 'User', campaign: Campaign, permission: Permission):
        if campaign not in self.campaigns:
            raise ValueError("You can only share campaigns you own")
        
        if target_user == self:
            raise ValueError("Cannot share with yourself")
        
        for sc in target_user.shared_campaigns_received:
            if sc.campaign == campaign:
                raise ValueError(f"Campaign '{campaign.name}' is already shared with {target_user.username}")
        
        new_share = SharedCampaign(target_user, campaign, permission)
        target_user.shared_campaigns_received.append(new_share)

    def unshare_campaign(self, target_user: 'User', campaign: Campaign):
        if campaign not in self.campaigns:
            raise ValueError("You can only unshare campaigns you own")
        
        for sc in target_user.shared_campaigns_received:
            if sc.campaign == campaign:
                target_user.shared_campaigns_received.remove(sc)
                return
        
        raise ValueError(f"Campaign '{campaign.name}' is not shared with {target_user.username}")
    
    def share_quest_event(self, target_user: 'User', event: QuestEvent, permission: Permission):
        owns_event = any(event in c.events for c in self.campaigns)
        if not owns_event:
            raise ValueError("You can only share events from campaigns you own")
        
        if target_user == self:
            raise ValueError("Cannot share with yourself")
        
        for se in target_user.shared_events_received:
            if se.event == event:
                raise ValueError(f"Event '{event.name}' is already shared with {target_user.username}")
        
        new_share = SharedEvent(target_user, event, permission)
        target_user.shared_events_received.append(new_share)

    def unshare_quest_event(self, target_user: 'User', event: QuestEvent):
        owns_event = any(event in c.events for c in self.campaigns)
        if not owns_event:
            raise ValueError("You can only unshare events from campaigns you own")
        
        for se in target_user.shared_events_received:
            if se.event == event:
                target_user.shared_events_received.remove(se)
                return
        
        raise ValueError(f"Event '{event.name}' is not shared with {target_user.username}")
    
    def get_all_campaigns(self) -> List[Campaign]:
        owned = self.campaigns.copy()
        shared = [sc.campaign for sc in self.shared_campaigns_received]
        return owned + shared
    
    def get_all_events(self) -> List[QuestEvent]:
        events = []
        
        for campaign in self.campaigns:
            events.extend(campaign.events)
        
        for se in self.shared_events_received:
            events.append(se.event)
        
        return events
    
    def can_edit_campaign(self, campaign: Campaign) -> bool:
        if campaign in self.campaigns:
            return True
        
        for sc in self.shared_campaigns_received:
            if sc.campaign == campaign and sc.permission == Permission.COLLABORATIVE:
                return True
        
        return False

# === DESIGN PATTERN 1: FACTORY METHOD (USAGE) ===
    # def add_character(self, name: str, char_class: CharacterClass, level: int = 1) -> Character:
    #     new_char = Character(name, char_class, level)
    #     self.characters.append(new_char)
    #     return new_char

    def add_character(self, creator: CharacterCreator, name: str, level: int = 1) -> Character:
        new_char = creator.create_character(name, level) 
        self.characters.append(new_char)
        return new_char
# =========================================
    
    def remove_character(self, character: Character):
        if character in self.characters:
            self.characters.remove(character)
        else:
            raise ValueError(f"Character '{character.name}' not found")
    
    # =============================================================
    # [REFACTORING: Introduce Parameter Object - AI Assist]
    # =============================================================
    def add_quest_event(self, campaign_name: str, spec: EventSpec) -> QuestEvent:
        campaign = None
        for c in self.campaigns:
            if c.name == campaign_name:
                campaign = c
                break
        
        if campaign is None:
            raise ValueError(f"Campaign '{campaign_name}' not found")
        
        return campaign.add_quest_event(spec)   # passes the whole spec down
    # =============================================================
    
    def __str__(self):
        return f"User: {self.username} ({len(self.campaigns)} campaigns, {len(self.characters)} characters)"
    
    def __repr__(self):
        return f"User(username='{self.username}', campaigns={len(self.campaigns)}, characters={len(self.characters)})"

# === DESIGN PATTERN 2 & REFACTORING: TEMPLATE METHOD & POLYMORPHISM ===
# Rationale: Eliminates repeated switch statements and duplicated sorting/looping logic.
class TimeFormatter(ABC):
    @abstractmethod
    def format(self, event: 'QuestEvent') -> str:
        pass

class WorldTimeFormatter(TimeFormatter):
    def format(self, event: 'QuestEvent') -> str:
        return event.display_global_time()

class RealmTimeFormatter(TimeFormatter):
    def format(self, event: 'QuestEvent') -> str:
        return event.display_local_time()

class CombinedTimeFormatter(TimeFormatter):
    def format(self, event: 'QuestEvent') -> str:
        return f"{event.display_global_time()} | {event.display_local_time()}"

class TimelineRenderer(ABC):
    def render(self, campaign: 'Campaign', date: 'WorldClock', formatter: TimeFormatter) -> str:
        events = self._filter_events(campaign, date) 
        if not events:
            return self._empty_message(date)
        
        events.sort(key=lambda e: e.start_time.total_minutes())
        
        result = self._get_header(date)
        for e in events:
            result += f"  • {e.name}: {formatter.format(e)}\n" 
        return result

    @abstractmethod
    def _filter_events(self, campaign, date): pass
    @abstractmethod
    def _get_header(self, date): pass
    @abstractmethod
    def _empty_message(self, date): pass

class DayRenderer(TimelineRenderer):
    def _filter_events(self, campaign, date):
        return [e for e in campaign.events if e.start_time.days == date.days]
    def _get_header(self, date): 
        return f"=== Events on Day {date.days} ===\n"
    def _empty_message(self, date): 
        return f"No events on Day {date.days}"

class WeekRenderer(TimelineRenderer):
    def _filter_events(self, campaign, date):
        end_day = date.days + 7
        return [e for e in campaign.events if date.days <= e.start_time.days < end_day]
    def _get_header(self, date): 
        return f"=== Events for Week (Days {date.days}-{date.days+6}) ===\n"
    def _empty_message(self, date): 
        return f"No events in week starting Day {date.days}"

_FORMATTER_MAP = {
    TimeDisplay.WORLD: WorldTimeFormatter(),
    TimeDisplay.REALM: RealmTimeFormatter(),
    TimeDisplay.BOTH:  CombinedTimeFormatter(),
}

class TimelineView:
    """Displays events in different time views."""    
    def __init__(self, events: List['QuestEvent'], settings: 'Settings'):
        if settings is None:
            raise ValueError("Settings cannot be None")
        self.events: List['QuestEvent'] = events if events else []
        self.settings: Settings = settings
    
    def _get_formatter(self) -> TimeFormatter:
        return _FORMATTER_MAP[self.settings.time_display]
    
    def displayDay(self, campaign: 'Campaign', date: 'WorldClock') -> str:
        # REFACTORED: Now uses Template Method (DayRenderer) and Polymorphism
        return DayRenderer().render(campaign, date, self._get_formatter())
    
    def displayWeek(self, campaign: 'Campaign', start_date: 'WorldClock') -> str:
        # REFACTORED: Now uses Template Method (WeekRenderer) and Polymorphism
        return WeekRenderer().render(campaign, start_date, self._get_formatter())
    
    def __str__(self):
        return f"TimelineView with {len(self.events)} events (Theme: {self.settings.app_theme.value})"
    
    def __repr__(self):
        return f"TimelineView(events={len(self.events)}, settings={self.settings.time_display})"
# ==========================================================