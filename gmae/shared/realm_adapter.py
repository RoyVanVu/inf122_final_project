from gmae.shared.van_guildquest import Realm

class RealmAdapter:
    """
    Adapter pattern — wraps Van's Realm class and adds a grid layer
    so adventures can place entities at (x, y) coordinates and move
    them by direction string.

    Reused subsystem: realm/map model from Van's assignment.
    Van's Realm handles realm identity, neighbors, and local time rules.
    This adapter adds the spatial grid layer on top.
    """

    DIRECTIONS = {
        "north": (0, -1),
        "south": (0,  1),
        "east":  (1,  0),
        "west":  (-1, 0),
    }

    def __init__(self, realm_name: str, width: int, height: int):
        self._realm = Realm(name=realm_name, map_id=0)
        self._width = width
        self._height = height

        self._grid: dict = {
            (x, y): "plains"
            for x in range(width)
            for y in range(height)
        }

        self._entities: dict = {}

    def set_terrain(self, x: int, y: int, terrain: str) -> None:
        if self._in_bounds(x, y):
            self._grid[(x, y)] = terrain

    def get_tile(self, x: int, y: int) -> dict:
        if not self._in_bounds(x, y):
            return None
        entities_here = [
            eid for eid, pos in self._entities.items() if pos == (x, y)
        ]
        return {
            "x": x,
            "y": y,
            "terrain": self._grid.get((x, y), "plains"),
            "entities": entities_here,
        }

    def get_terrain(self, x: int, y: int) -> str:
        if not self._in_bounds(x, y):
            return "void"
        return self._grid.get((x, y), "plains")

    def place_entity(self, entity_id: str, x: int, y: int) -> bool:
        if not self._in_bounds(x, y):
            return False
        self._entities[entity_id] = (x, y)
        return True

    def move(self, entity_id: str, direction: str) -> tuple:
        if entity_id not in self._entities:
            return False, -1, -1, f"Entity '{entity_id}' not found on map."

        dx, dy = self.DIRECTIONS.get(direction.lower(), (0, 0))
        if dx == 0 and dy == 0:
            return False, -1, -1, f"Unknown direction '{direction}'."

        cx, cy = self._entities[entity_id]
        nx, ny = cx + dx, cy + dy

        if not self._in_bounds(nx, ny):
            return False, cx, cy, "Cannot move outside the realm boundaries."

        self._entities[entity_id] = (nx, ny)
        return True, nx, ny, f"{entity_id} moved {direction} to ({nx}, {ny})."

    def get_position(self, entity_id: str) -> tuple:
        return self._entities.get(entity_id, None)

    def get_realm_name(self) -> str:
        return self._realm.name

    def render_map(self) -> str:
        symbols = {"plains": ".", "wall": "#", "water": "~", "mountain": "^"}
        entity_positions = {pos: eid for eid, pos in self._entities.items()}

        rows = []
        for y in range(self._height):
            row = ""
            for x in range(self._width):
                pos = (x, y)
                if pos in entity_positions:
                    row += entity_positions[pos][0].upper()
                else:
                    terrain = self._grid.get(pos, "plains")
                    row += symbols.get(terrain, "?")
            rows.append(row)
        return "\n".join(rows)

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self._width and 0 <= y < self._height