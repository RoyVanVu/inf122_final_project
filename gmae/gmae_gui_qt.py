import os
import sys
import re

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QTextEdit,
    QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsObject
)
from PyQt5.QtGui import QPixmap, QFont, QColor, QPainter
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPointF, QRectF, QTimer

from gmae.gmae_core.profile_manager import PlayerProfile, ProfileFacade
from gmae.gmae_core.adventure_registry import AdventureRegistry
from gmae.gmae_core.input_proxy import InputProxy

TILE_SIZE = 48

# Tick interval in ms for the game loop
TICK_INTERVAL_MS = 100
# How many ticks between each advance_turn() call (~1 second)
TURN_TICK_INTERVAL = 10


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


# ======================================================================
# Key binding maps
# ======================================================================
P1_KEY_MAP = {
    Qt.Key_W: "move north",
    Qt.Key_S: "move south",
    Qt.Key_A: "move west",
    Qt.Key_D: "move east",
    Qt.Key_Q: "use item",
    Qt.Key_E: "wait",
}

P2_KEY_MAP = {
    Qt.Key_Up:    "move north",
    Qt.Key_Down:  "move south",
    Qt.Key_Left:  "move west",
    Qt.Key_Right: "move east",
    Qt.Key_Slash: "use item",
    Qt.Key_Period: "wait",
}


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

        # ── Assets ─────────────────────────────────────────────────────
        self.assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        self.sprite_pixmaps = {}   # char -> QPixmap
        self._load_sprites()

        # Tracked animated nodes for smooth movement
        self.player_nodes = {}     # "p1" / "p2" -> AnimatedSpriteNode
        self.previous_map_str = None

        # ── Game loop state ────────────────────────────────────────────
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self._game_tick)
        self._tick_count = 0
        self._game_running = False

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

        self.sprite_pixmaps = {
            ".": grass,
            " ": grass,
            "#": wall,
            "~": hazard,
            "^": relic,
            "P": p1,
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

        title = QLabel("\u2694  GuildQuest Mini-Adventure  \u2694")
        title.setFont(QFont("Arial", 26, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #e94560;")
        self.main_layout.addWidget(title)

        subtitle = QLabel("Two players \u00b7 One machine \u00b7 Infinite glory")
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
            self.listbox.addItem(f"{adv}  \u2014  {obj.get_description()}")
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
        self.previous_map_str = None
        self.player_nodes.clear()
        self._tick_count = 0
        self._build_main_game_screen()

    # ==================================================================
    # Screen 3: Main Game  (real-time, keyboard-driven)
    # ==================================================================

    # ------------------------------------------------------------------
    # Compass + Controls widget builders
    # ------------------------------------------------------------------
    def _build_controls_widget(self):
        """Return a styled QLabel showing key bindings for both players."""
        html = (
            "<div align='center'>"
            "<table cellspacing='0' cellpadding='2' "
            "style='color:#56d8ff; font-family:Consolas,Courier; font-size:16px; font-weight:bold;'>"
            "<tr><td width='50'></td><td align='center' width='60'>N</td><td width='50'></td></tr>"
            "<tr><td></td><td align='center'>\u25b2</td><td></td></tr>"
            "<tr>"
            "  <td align='right'>W \u25c4</td>"
            "  <td align='center'>\u2500\u25cf\u2500</td>"
            "  <td align='left'>\u25ba E</td>"
            "</tr>"
            "<tr><td></td><td align='center'>\u25bc</td><td></td></tr>"
            "<tr><td></td><td align='center'>S</td><td></td></tr>"
            "</table>"
            "<br>"
            "<table style='font-size:12px; margin-top:2px;'>"
            "<tr>"
            "  <td style='color:#4488ff; font-weight:bold;'>P1 (WASD)</td>"
            "  <td width='20'></td>"
            "  <td style='color:#ff4444; font-weight:bold;'>P2 (Arrows)</td>"
            "</tr>"
            "<tr style='color:#c8c8e0;'>"
            "  <td>Q = Item</td><td></td><td>/ = Item</td>"
            "</tr>"
            "<tr style='color:#c8c8e0;'>"
            "  <td>E = Wait</td><td></td><td>. = Wait</td>"
            "</tr>"
            "</table>"
            "</div>"
        )
        lbl = QLabel(html)
        lbl.setTextFormat(Qt.RichText)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            "background-color: #16213e; border: 1px solid #0f3460;"
            "border-radius: 6px; padding: 14px; color: #56d8ff;"
        )
        lbl.setMinimumHeight(180)
        return lbl

    def _build_legend_widget(self):
        """Return a styled QLabel with the map legend."""
        html = (
            "<b style='color:#e94560; font-size:13px;'>\U0001f5fa Map Legend</b>"
            "<table style='color:#c8c8e0; font-size:12px; margin-top:6px;'>"
            "<tr>"
            "  <td><span style='color:#4488ff;'>\u25a0</span> Player 1</td>"
            "  <td width='16'></td>"
            "  <td><span style='color:#ff4444;'>\u25a0</span> Player 2</td>"
            "</tr>"
            "<tr>"
            "  <td><span style='color:#ffcc00;'>\u25a0</span> NPC</td>"
            "  <td></td>"
            "  <td><span style='color:#3a7d44;'>\u25a0</span> Grass</td>"
            "</tr>"
            "<tr>"
            "  <td><span style='color:#555;'>\u25a0</span> Wall</td>"
            "  <td></td>"
            "  <td><span style='color:#ff6600;'>\u25a0</span> Hazard</td>"
            "</tr>"
            "<tr>"
            "  <td colspan='3'><span style='color:#ffdd00;'>\u25a0</span> Relic / Goal</td>"
            "</tr>"
            "</table>"
            "<br>"
            "<span style='color:#c8c8e0; font-size:12px;'>Press <b style='color:#e94560;'>Esc</b> to quit</span>"
        )
        lbl = QLabel(html)
        lbl.setFont(QFont("Segoe UI", 11))
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.RichText)
        lbl.setStyleSheet(
            "background-color: #16213e; border: 1px solid #0f3460;"
            "border-radius: 6px; padding: 10px; color: #d4d4d4;"
        )
        return lbl

    # ------------------------------------------------------------------
    # Build the game screen
    # ------------------------------------------------------------------
    def _build_main_game_screen(self):
        self._clear_layout()

        game_h = QHBoxLayout()

        # ── Left: map view + controls + legend ──
        left_v = QVBoxLayout()
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setMinimumSize(420, 420)
        left_v.addWidget(self.view, stretch=1)

        # Controls and legend side-by-side below the map
        bottom_h = QHBoxLayout()
        bottom_h.addWidget(self._build_controls_widget())
        bottom_h.addWidget(self._build_legend_widget())
        left_v.addLayout(bottom_h)

        game_h.addLayout(left_v, stretch=2)

        # ── Right: player labels + stats + log ──
        right_v = QVBoxLayout()

        # Player status bar (both players, color-coded)
        self.player_bar = QLabel("")
        self.player_bar.setFont(QFont("Arial", 14, QFont.Bold))
        self.player_bar.setTextFormat(Qt.RichText)
        self.player_bar.setAlignment(Qt.AlignCenter)
        self.player_bar.setStyleSheet(
            "background-color: #16213e; border: 1px solid #0f3460;"
            "border-radius: 6px; padding: 8px;"
        )
        right_v.addWidget(self.player_bar)

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

        game_h.addLayout(right_v, stretch=1)
        self.main_layout.addLayout(game_h)

        self._full_map_render()
        self._update_stats()
        self._update_player_bar()
        self._append_log("Adventure started! Use keyboard controls.")
        self._append_log("P1: WASD to move, Q=item, E=wait")
        self._append_log("P2: Arrow keys to move, /=item, .=wait")
        self._append_log("Press Esc to quit.")

        # Start the r-time game loop
        self._game_running = True
        self.game_timer.start(TICK_INTERVAL_MS)
        self.setFocus()

    # ==================================================================
    # Keyboard input
    # ==================================================================
    def keyPressEvent(self, event):
        if not self._game_running:
            super().keyPressEvent(event)
            return

        key = event.key()

        # Escape to quit
        if key == Qt.Key_Escape:
            self._stop_game()
            self._append_log("> Adventure abandoned.")
            self._handle_game_over("LOSS")
            return

        # Player 1 keys
        if key in P1_KEY_MAP:
            action = P1_KEY_MAP[key]
            self._process_action(1, action)
            return

        # Player 2 keys
        if key in P2_KEY_MAP:
            action = P2_KEY_MAP[key]
            self._process_action(2, action)
            return

        super().keyPressEvent(event)

    def _process_action(self, player_id, action):
        """Immediately send  action  given player."""
        if not self._game_running:
            return

        old_state = self.current_adventure.get_state()

        result_msg = self.proxy.forward(player_id, action)

        # Only log non-trivial messages (skip wait spam)
        tag = "P1" if player_id == 1 else "P2"
        if action != "wait":
            self._append_log(f"[{tag}] {action}: {result_msg}")

        if result_msg.startswith("[BLOCKED]"):
            key = "p1" if player_id == 1 else "p2"
            if key in self.player_nodes:
                self.player_nodes[key].shake()
        else:
            # Re-render successful action
            self._full_map_render()
            self._update_stats()

            # Check completion immediately after each action
            status = self.current_adventure.check_completion()
            if status != "ONGOING":
                self._stop_game()
                self._handle_game_over(status)

    # ==================================================================
    # Game timer tick  (~100ms)
    # ==================================================================
    def _game_tick(self):
        """Called QTimer every TICK_INTERVAL_MS."""
        if not self._game_running:
            return

        self._tick_count += 1

        # Advance the adventure turn every TURN_TICK_INTERVAL ticks
        if self._tick_count % TURN_TICK_INTERVAL == 0:
            self.current_adventure.advance_turn()
            self._full_map_render()
            self._update_stats()

            status = self.current_adventure.check_completion()
            if status != "ONGOING":
                self._stop_game()
                self._handle_game_over(status)

    def _stop_game(self):
        self._game_running = False
        self.game_timer.stop()

    # ==================================================================
    # Map rendering
    # ==================================================================
    def _get_player_positions(self, state):
        p1_pos = None
        p2_pos = None

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
                if ch != "#":
                    bg = AnimatedSpriteNode(self.sprite_pixmaps["."], col_idx, row_idx)
                    bg.setZValue(-1)
                    self.scene.addItem(bg)

                if ch == "P":
                    if p1_pos and (col_idx, row_idx) == p1_pos:
                        node = AnimatedSpriteNode(self._p1_pix, col_idx, row_idx)
                        node.setZValue(2)
                        self.player_nodes["p1"] = node
                    elif p2_pos and (col_idx, row_idx) == p2_pos:
                        node = AnimatedSpriteNode(self._p2_pix, col_idx, row_idx)
                        node.setZValue(2)
                        self.player_nodes["p2"] = node
                    else:
                        node = AnimatedSpriteNode(self.sprite_pixmaps.get("P", self._p1_pix), col_idx, row_idx)
                        node.setZValue(2)
                    self.scene.addItem(node)
                else:
                    pix = self.sprite_pixmaps.get(ch, self.sprite_pixmaps["."])
                    node = AnimatedSpriteNode(pix, col_idx, row_idx)
                    node.setZValue(0 if ch in (".", " ", "#") else 1)
                    self.scene.addItem(node)

        self.previous_map_str = map_str

    # ==================================================================
    # Stats + Player bar
    # ==================================================================
    def _update_stats(self):
        state = self.current_adventure.get_state()
        lines = []
        skip_keys = {"map", "map_legend", "map legend"}
        for k, v in state.items():
            if k.lower() not in skip_keys:
                val_str = str(v)
                val_str = re.sub(r'\s*Map legend:.*$', '', val_str, flags=re.IGNORECASE).strip()
                if not val_str:
                    continue
                label = k.replace("_", " ").title()
                lines.append(f"{label}: {val_str}")
        self.stats_label.setText("\n".join(lines))

    def _update_player_bar(self):
        p1_name = self.p1_facade.get_name()
        p2_name = self.p2_facade.get_name()
        self.player_bar.setText(
            f"<span style='color:#4488ff; font-size:15px;'>\u25a0 {p1_name} (WASD)</span>"
            f"&nbsp;&nbsp;&nbsp;\u2694&nbsp;&nbsp;&nbsp;"
            f"<span style='color:#ff4444; font-size:15px;'>\u25a0 {p2_name} (Arrows)</span>"
        )

    # ==================================================================
    # Log
    # ==================================================================
    def _append_log(self, text):
        self.log_display.append(text)

    # ==================================================================
    # Game over
    # ==================================================================
    def _handle_game_over(self, status):
        self._stop_game()
        adv_name = type(self.current_adventure).__name__

        p1_result = "WIN" if status == "WIN_P1" else ("LOSS" if status == "WIN_P2" else status)
        p2_result = "WIN" if status == "WIN_P2" else ("LOSS" if status == "WIN_P1" else status)

        self.p1_facade.update_history(adv_name, p1_result)
        self.p2_facade.update_history(adv_name, p2_result)
        self.p1_facade._save(self.p1_facade.get_name())
        self.p2_facade._save(self.p2_facade.get_name())

        messages = {
            "WIN":    "VICTORY! Well played, adventurers!",
            "WIN_P1": f"{self.p1_facade.get_name()} WINS! \U0001f3c6",
            "WIN_P2": f"{self.p2_facade.get_name()} WINS! \U0001f3c6",
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
