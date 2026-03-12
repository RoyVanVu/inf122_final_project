from gmae.shared.chiwei_guildquest import Inventory, Item

class InventoryAdapter:
    """
    Adapter pattern — wraps Chi-Wei's Inventory class into a consistent
    interface for adventures. Adventures call add_item(), remove_item(),
    use_item(), and get_items() without needing to know Chi-Wei's internals.

    Reused subsystem: item/inventory model from Chi-Wei's assignment.
    Chi-Wei's Inventory handles item storage with a dict keyed by item_id.
    This adapter adds use_item() and a friendlier name-based interface.
    """

    def __init__(self, owner_id: str):
        self._owner_id = owner_id
        self._inventory = Inventory()


    def add_item(self, item: Item) -> None:
        if not isinstance(item, Item):
            raise TypeError("Only Item instances can be added to inventory.")
        self._inventory.add(item)

    def remove_item(self, item_id: str) -> bool:
        if item_id in self._inventory.items:
            self._inventory.remove(item_id)
            return True
        return False

    def use_item(self, item_id: str) -> dict:
        if item_id not in self._inventory.items:
            return {
                "success": False,
                "message": f"Item '{item_id}' not found in inventory.",
                "item": None,
            }
        item = self._inventory.items[item_id]
        self._inventory.remove(item_id)
        return {
            "success": True,
            "message": f"{self._owner_id} used '{item.name}' ({item.rarity}).",
            "item": item,
        }

    def get_items(self) -> list:
        return list(self._inventory.items.values())

    def has_item(self, item_id: str) -> bool:
        return item_id in self._inventory.items

    def count(self) -> int:
        return len(self._inventory.items)

    def __repr__(self) -> str:
        return f"InventoryAdapter(owner={self._owner_id!r}, items={self.count()})"