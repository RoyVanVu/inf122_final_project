import os
import sys
import re

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QTextEdit,
    QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsObject
)
from PyQt5.QtGui import QPixmap, QFont, QColor, QPainter
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPointF, QRectF

from gmae.gmae_core.profile_manager import PlayerProfile, ProfileFacade
from gmae.gmae_core.adventure_registry import AdventureRegistry
from gmae.gmae_core.input_proxy import InputProxy

TILE_SIZE = 48


class AnimatedSpriteNode(QGraphicsObject):

    def __init__(self, pixmap, col, row, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap.scaled(TILE_SIZE, TILE_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPos(col * TILE_SIZE, row * TILE_SIZE)
        self.grid_col = col
        self.grid_row = row

    def boundingRect(self):
        return QRectF(0, 0, TILE_SIZE, TILE_SIZE)

    def paint(self, painter, option, widget):
        painter.drawPixmap(0, 0, self.pixmap)

    def animate_to(self, col, row):
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(QPointF(col * TILE_SIZE, row * TILE_SIZE))
        self.anim.start()
        self.grid_col = col
        self.grid_row = row

    def shake(self):
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(200)
        start = self.pos()
        self.anim.setKeyValueAt(0, start)
        self.anim.setKeyValueAt(0.25, start + QPointF(6, 0))
        self.anim.setKeyValueAt(0.75, start + QPointF(-6, 0))
        self.anim.setKeyValueAt(1, start)
        self.anim.start()


class GMAEGUIQt(QMainWindow):


    def __init__(self):
        super().__init__()
        self.setWindowTitle("GuildQuest Fancy Edition")
        self.resize(1100, 750)

        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; }
            QLabel { color: #e0e0e0; font-family: 'Segoe UI', Arial; }
            QLineEdit {
                background-color: #16213e; color: #ffffff;
                border: 1px solid #0f3460; border-radius: 6px; padding: 6px;
            }
            QPushButton {
                background-color: #e94560; color: white; border: none;
                border-radius: 6px; padding: 10px 20px; font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #ff6b81; }
            QTextEdit, QListWidget {
                background-color: #16213e; color: #d4d4d4;
                border: 1px solid #0f3460; border-radius: 6px; padding: 6px;
            }
            QGraphicsView {
                background-color: #0a0a23; border: 2px solid #0f3460;
                border-radius: 6px;
            }
        """)

        # ── Engine ─────────────────────────────────────────────────────
        self.registry = AdventureRegistry()
        self._load_adventures()

        self.p1_facade = None
        self.p2_facade = None
        self.current_adventure = None
        self.proxy = None
        self.current_player_id = 1

        # ── Assets ─────────────────────────────────────────────────────
        self.assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        self.sprite_pixmaps = {}   # char -> QPixmap
        self._load_sprites()

        # Tracked animated nodes for smooth movement
        self.player_nodes = {}     # "p1" / "p2" -> AnimatedSpriteNode
        self.previous_map_str = None

        # ── Central widget ─────────────────────────────────────────────
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self._build_setup_screen()

    # ==================================================================
    # Asset loading
    # ==================================================================
    def _load_sprites(self):
        import glob

        def latest(prefix):
            files = glob.glob(os.path.join(self.assets_dir, f"{prefix}*.png"))
            return max(files, key=os.path.getmtime) if files else None

        def pix(prefix, fallback_color):
            path = latest(prefix)
            if path:
                return QPixmap(path)
            p = QPixmap(TILE_SIZE, TILE_SIZE)
            p.fill(QColor(fallback_color))
            return p

        grass  = pix("grass_tile",   "#3a7d44")
        wall   = pix("wall_tile",    "#555555")
        p1     = pix("player1_sprite", "#4488ff")
        p2     = pix("player2_sprite", "#ff4444")
        npc    = pix("npc_sprite",    "#ffcc00")
        hazard = pix("hazard_sprite", "#ff6600")
        relic  = pix("relic_sprite",  "#ffdd00")

        # Map  ACTUAL characters produced by render_map():
        #   P = player (both), N = npc, ~ = water/hazard, ^ = mountain/destination/relic
        #   . = plains, # = wall
        self.sprite_pixmaps = {
            ".": grass,
            " ": grass,
            "#": wall,
            "~": hazard,   # water terrain -> hazard
            "^": relic,    # mountain terrain -> destination/relic
            "P": p1,       # default;  override per-player below via position
            "N": npc,
        }
        self._p1_pix = p1
        self._p2_pix = p2

    # ==================================================================
    # Adventure loading
    # ==================================================================
    def _load_adventures(self):
        import pkgutil, importlib
        import gmae.adventures as adv_pkg
        from gmae.gmae_interface import MiniAdventure

        for _, name, _ in pkgutil.iter_modules(adv_pkg.__path__):
            try:
                mod = importlib.import_module(f"gmae.adventures.{name}")
                for attr in vars(mod).values():
                    if (isinstance(attr, type)
                            and issubclass(attr, MiniAdventure)
                            and attr is not MiniAdventure):
                        self.registry.register(attr.__name__, attr)
            except Exception as e:
                print(f"[WARNING] Failed to load adventure '{name}': {e}")

    # ==================================================================
    # Layout helpers
    # ==================================================================
    def _clear_layout(self):
        def _remove_items(layout):
            while layout.count():
                item = layout.takeAt(0)
                child_layout = item.layout()
                if child_layout:
                    _remove_items(child_layout)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
        _remove_items(self.main_layout)

    # ==================================================================
    # Screen 1: Setup
    # ==================================================================
    def _build_setup_screen(self):
        self._clear_layout()

        title = QLabel("⚔  GuildQuest Mini-Adventure  ⚔")
        title.setFont(QFont("Arial", 26, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #e94560;")
        self.main_layout.addWidget(title)

        subtitle = QLabel("Two players · One machine · Infinite glory")
        subtitle.setFont(QFont("Arial", 13))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #a0a0c0;")
        self.main_layout.addWidget(subtitle)
        self.main_layout.addSpacing(40)

        form = QHBoxLayout()
        for label_text, attr_name in [("Player 1 Name:", "entry_p1"),
                                       ("Player 2 Name:", "entry_p2")]:
            col = QVBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Arial", 14))
            entry = QLineEdit()
            entry.setFont(QFont("Arial", 14))
            entry.setMinimumWidth(220)
            col.addWidget(lbl)
            col.addWidget(entry)
            form.addLayout(col)
            form.addSpacing(20)
            setattr(self, attr_name, entry)

        self.main_layout.addLayout(form)
        self.main_layout.addSpacing(30)

        btn = QPushButton("Load Profiles")
        btn.setFont(QFont("Arial", 14))
        btn.clicked.connect(self._on_load_profiles)
        self.main_layout.addWidget(btn, alignment=Qt.AlignCenter)
        self.main_layout.addStretch()

    def _on_load_profiles(self):
        n1 = self.entry_p1.text().strip()
        n2 = self.entry_p2.text().strip()
        if not n1 or not n2:
            QMessageBox.critical(self, "Error", "Both player names must be provided.")
            return
        self.p1_facade = ProfileFacade(PlayerProfile.load(n1))
        self.p2_facade = ProfileFacade(PlayerProfile.load(n2))
        self._build_adventure_selection_screen()

    # ==================================================================
    # Screen 2: Adventure Selection
    # ==================================================================
    def _build_adventure_selection_screen(self):
        self._clear_layout()

        title = QLabel("Select an Adventure")
        title.setFont(QFont("Arial", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #e94560;")
        self.main_layout.addWidget(title)
        self.main_layout.addSpacing(20)

        self.adventures = self.registry.list_adventures()
        if not self.adventures:
            self.main_layout.addWidget(QLabel("No adventures loaded."))
            return

        self.listbox = QListWidget()
        self.listbox.setFont(QFont("Arial", 14))
        for adv in self.adventures:
            obj = self.registry.get_adventure(adv)
            self.listbox.addItem(f"{adv}  —  {obj.get_description()}")
        self.main_layout.addWidget(self.listbox)
        self.main_layout.addSpacing(10)

        btn = QPushButton("Start Adventure")
        btn.setFont(QFont("Arial", 14))
        btn.clicked.connect(self._on_start_adventure)
        self.main_layout.addWidget(btn, alignment=Qt.AlignCenter)

    def _on_start_adventure(self):
        sel = self.listbox.selectedIndexes()
        if not sel:
            QMessageBox.critical(self, "Error", "Please select an adventure.")
            return
        idx = sel[0].row()
        self.current_adventure = self.registry.get_adventure(self.adventures[idx])
        self.current_adventure.initialize(self.p1_facade, self.p2_facade)
        self.proxy = InputProxy(self.current_adventure)
        self.current_player_id = 1
        self.previous_map_str = None
        self.player_nodes.clear()
        self._build_main_game_screen()

    # ==================================================================
    # Screen 3: Main Game
    # ==================================================================
    def _build_main_game_screen(self):
        self._clear_layout()

        game_h = QHBoxLayout()

        # ── Left: map view ──
        left_v = QVBoxLayout()
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setMinimumSize(420, 420)
        left_v.addWidget(self.view, stretch=1)
        game_h.addLayout(left_v, stretch=2)

        # ── Right: stats + log + input ──
        right_v = QVBoxLayout()

        self.stats_label = QLabel("Stats:")
        self.stats_label.setFont(QFont("Courier", 11))
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet(
            "background-color: #16213e; border: 1px solid #0f3460;"
            "border-radius: 6px; padding: 8px; color: #a0d0ff;"
        )
        right_v.addWidget(self.stats_label)

        self.log_display = QTextEdit()
        self.log_display.setFont(QFont("Courier", 11))
        self.log_display.setReadOnly(True)
        right_v.addWidget(self.log_display, stretch=1)

        self.lbl_turn = QLabel("")
        self.lbl_turn.setFont(QFont("Arial", 15, QFont.Bold))
        self.lbl_turn.setStyleSheet("color: #ffaa00; padding: 4px;")
        right_v.addWidget(self.lbl_turn)

        input_h = QHBoxLayout()
        self.entry_action = QLineEdit()
        self.entry_action.setFont(QFont("Arial", 14))
        self.entry_action.setPlaceholderText("e.g. move north, use item, wait")
        self.entry_action.returnPressed.connect(self._on_submit_action)
        input_h.addWidget(self.entry_action)

        btn = QPushButton("Submit")
        btn.clicked.connect(self._on_submit_action)
        input_h.addWidget(btn)
        right_v.addLayout(input_h)

        game_h.addLayout(right_v, stretch=1)
        self.main_layout.addLayout(game_h)

        self._full_map_render()
        self._update_stats_and_turn()
        self._append_log("Adventure started! Type your actions below.")
        self._append_log("Valid: move north/south/east/west, use item, wait, quit")
        self.entry_action.setFocus()

    # ==================================================================
    # Map rendering
    # ==================================================================
    def _get_player_positions(self, state):
      
        p1_pos = None
        p2_pos = None

        # Try to extract from state values (formats like "(x, y)")
        for key, val in state.items():
            val_str = str(val)
            if key.lower().replace(" ", "_") in ("p1_position", "player_1_position"):
                m = re.search(r'\((\d+),\s*(\d+)\)', val_str)
                if m:
                    p1_pos = (int(m.group(1)), int(m.group(2)))
            elif key.lower().replace(" ", "_") in ("p2_position", "player_2_position"):
                m = re.search(r'\((\d+),\s*(\d+)\)', val_str)
                if m:
                    p2_pos = (int(m.group(1)), int(m.group(2)))

        # If positions not in state (e.g. escort adventure), scan map for 'P' chars.
        # Both players are 'P', so just collect all P positions in order.
        if p1_pos is None or p2_pos is None:
            map_str = state.get("map", "")
            p_positions = []
            for row_idx, row in enumerate(map_str.strip().split("\n")):
                for col_idx, ch in enumerate(row):
                    if ch == "P":
                        p_positions.append((col_idx, row_idx))
            if len(p_positions) >= 2:
                p1_pos = p_positions[0]
                p2_pos = p_positions[1]
            elif len(p_positions) == 1:
                p1_pos = p_positions[0]

        return p1_pos, p2_pos

    def _full_map_render(self):
        state = self.current_adventure.get_state()
        map_str = state.get("map", "")
        if not map_str:
            return

        self.scene.clear()
        self.player_nodes.clear()

        p1_pos, p2_pos = self._get_player_positions(state)
        grid = [row for row in map_str.strip().split("\n") if row]

        for row_idx, row in enumerate(grid):
            for col_idx, ch in enumerate(row):
                # Always paint background grass first (unless wall)
                if ch != "#":
                    bg = AnimatedSpriteNode(self.sprite_pixmaps["."], col_idx, row_idx)
                    bg.setZValue(-1)
                    self.scene.addItem(bg)

                if ch == "P":
                    # Determine which player this is
                    if p1_pos and (col_idx, row_idx) == p1_pos:
                        node = AnimatedSpriteNode(self._p1_pix, col_idx, row_idx)
                        node.setZValue(2)
                        self.player_nodes["p1"] = node
                    elif p2_pos and (col_idx, row_idx) == p2_pos:
                        node = AnimatedSpriteNode(self._p2_pix, col_idx, row_idx)
                        node.setZValue(2)
                        self.player_nodes["p2"] = node
                    else:
                        # Fallback: generic P sprite
                        node = AnimatedSpriteNode(self.sprite_pixmaps.get("P", self._p1_pix), col_idx, row_idx)
                        node.setZValue(2)
                    self.scene.addItem(node)
                else:
                    pix = self.sprite_pixmaps.get(ch, self.sprite_pixmaps["."])
                    node = AnimatedSpriteNode(pix, col_idx, row_idx)
                    node.setZValue(0 if ch in (".", " ", "#") else 1)
                    self.scene.addItem(node)

        self.previous_map_str = map_str

    def _update_map(self, old_state, new_state):
        """Try to animate player movement; fall back to full re-render."""
        old_map = old_state.get("map", "")
        new_map = new_state.get("map", "")

        old_p1, old_p2 = self._get_player_positions(old_state)
        new_p1, new_p2 = self._get_player_positions(new_state)

        # Animate P1
        if "p1" in self.player_nodes and new_p1:
            if old_p1 != new_p1:
                self.player_nodes["p1"].animate_to(new_p1[0], new_p1[1])
            elif self.current_player_id == 2:
                # P1 just moved but position is same -> blocked -> shake
                self.player_nodes["p1"].shake()

        # Animate P2
        if "p2" in self.player_nodes and new_p2:
            if old_p2 != new_p2:
                self.player_nodes["p2"].animate_to(new_p2[0], new_p2[1])
            elif self.current_player_id == 1:
                self.player_nodes["p2"].shake()

        # Full re-render of non-player tiles (NPCs, hazards, relics can move)
        self._full_map_render()

    # ==================================================================
    # Stats / Turn label
    # ==================================================================
    def _update_stats_and_turn(self):
        state = self.current_adventure.get_state()
        lines = []
        for k, v in state.items():
            if k != "map":
                label = k.replace("_", " ").title()
                lines.append(f"{label}: {v}")
        self.stats_label.setText("\n".join(lines))

        name = self.p1_facade.get_name() if self.current_player_id == 1 else self.p2_facade.get_name()
        self.lbl_turn.setText(f"➤  {name}'s Turn  (Player {self.current_player_id})")

    # ==================================================================
    # Log
    # ==================================================================
    def _append_log(self, text):
        self.log_display.append(text)

    # ==================================================================
    # Action handler (event-driven turn loop)
    # ==================================================================
    def _on_submit_action(self):
        action = self.entry_action.text().strip()
        if not action:
            return
        self.entry_action.clear()

        if action.lower() == "quit":
            self._append_log("> Adventure abandoned.")
            self._handle_game_over("LOSS")
            return

        old_state = self.current_adventure.get_state()
        self._append_log(f"> {action}")

        result_msg = self.proxy.forward(self.current_player_id, action)
        self._append_log(result_msg)

        if result_msg.startswith("[BLOCKED]"):
            key = "p1" if self.current_player_id == 1 else "p2"
            if key in self.player_nodes:
                self.player_nodes[key].shake()
        else:
            self.current_adventure.advance_turn()
            self.current_player_id = 2 if self.current_player_id == 1 else 1

            new_state = self.current_adventure.get_state()
            self._update_map(old_state, new_state)
            self._update_stats_and_turn()

            status = self.current_adventure.check_completion()
            if status != "ONGOING":
                self._handle_game_over(status)

    # ==================================================================
    # Game over
    # ==================================================================
    def _handle_game_over(self, status):
        adv_name = type(self.current_adventure).__name__

        p1_result = "WIN" if status == "WIN_P1" else ("LOSS" if status == "WIN_P2" else status)
        p2_result = "WIN" if status == "WIN_P2" else ("LOSS" if status == "WIN_P1" else status)

        self.p1_facade.update_history(adv_name, p1_result)
        self.p2_facade.update_history(adv_name, p2_result)
        self.p1_facade._save(self.p1_facade.get_name())
        self.p2_facade._save(self.p2_facade.get_name())

        messages = {
            "WIN":    "VICTORY! Well played, adventurers!",
            "WIN_P1": f"{self.p1_facade.get_name()} WINS! 🏆",
            "WIN_P2": f"{self.p2_facade.get_name()} WINS! 🏆",
            "LOSS":   "DEFEAT. Better luck next time.",
            "DRAW":   "DRAW. An honorable outcome!",
        }
        QMessageBox.information(self, "Game Over",
                                messages.get(status, f"Adventure ended: {status}"))
        self._build_adventure_selection_screen()


def run_gui():
    app = QApplication(sys.argv)
    window = GMAEGUIQt()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_gui()
