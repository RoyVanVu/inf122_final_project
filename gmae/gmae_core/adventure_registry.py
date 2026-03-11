class AdventureRegistry:
    def __init__(self):
        self._adventures: dict = {}

    def register(self, name: str, cls: type) -> None:
        from gmae.gmae_interface import MiniAdventure  
        if not issubclass(cls, MiniAdventure):
            raise TypeError(f"{cls.__name__} must extend MiniAdventure")
        if name in self._adventures:
            raise ValueError(f"Adventure '{name}' is already registered")
        self._adventures[name] = cls

    def get_adventure(self, name: str):
        if name not in self._adventures:
            raise KeyError(f"No adventure named '{name}' is registered")
        return self._adventures[name]()

    def list_adventures(self) -> list:
        return sorted(self._adventures.keys())

    def __len__(self) -> int:
        return len(self._adventures)