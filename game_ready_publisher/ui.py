"""
Game Ready Publisher window:
  1. Scan the character and preview the texture resize plan
  2. Adjust any target size from its dropdown
  3. Resize All Textures, then run Merge Material UV in CC4
"""

import os
import subprocess

from PySide2 import QtWidgets, QtCore, QtGui

from . import __version__
from .settings import load_settings, ensure_rules_file, resolve_resolution
from . import textures as tt

STYLE = """
QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
    font-family: Segoe UI;
    font-size: 10pt;
}
QGroupBox {
    border: 1px solid #4a7800;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
    color: #78be00;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}
QPushButton {
    background-color: #3c3f41;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 6px 14px;
    color: #e0e0e0;
}
QPushButton:hover   { background-color: #3a3f35; border-color: #4a7800; }
QPushButton:pressed { background-color: #2d5a8e; }

QPushButton#resizeBtn {
    background-color: #1a2e00;
    font-weight: bold;
    font-size: 11pt;
    padding: 9px;
    border: 1px solid #78be00;
    color: #78be00;
}
QPushButton#resizeBtn:hover { background-color: #243d00; border-color: #8ad400; }
QPushButton#resizeBtn:pressed { background-color: #5f9900; color: #ffffff; }

QTableWidget {
    background-color: #1e1e1e;
    alternate-background-color: #262626;
    gridline-color: #3a3a3a;
    border: 1px solid #4a7800;
    font-size: 9pt;
}
QTableWidget::item { padding: 2px 4px; }
QTableWidget::item:selected {
    background-color: #2d5a8e;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #333;
    color: #aaa;
    border: none;
    padding: 3px 6px;
    font-size: 9pt;
    font-weight: bold;
}
QComboBox {
    background-color: #2a2a2a;
    border: 1px solid #555;
    border-radius: 2px;
    padding: 1px 4px;
    color: #e0e0e0;
    font-size: 9pt;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #2a2a2a;
    color: #e0e0e0;
    selection-background-color: #2d5a8e;
}
QLabel#statusLabel {
    background-color: #1a1a1a;
    border: 1px solid #444;
    border-radius: 3px;
    padding: 6px 8px;
    color: #90c890;
    font-size: 9pt;
}
QScrollArea { border: none; background-color: transparent; }
"""

SIZE_OPTIONS = ["DELETE", "128", "256", "512", "1024", "2048", "4096", "8192"]

RES_COLOURS = {
    0:    "#c86060",
    128:  "#c8960a",
    256:  "#a0a020",
    512:  "#408040",
    1024: "#308080",
    2048: "#4080b0",
    4096: "#6050c0",
    8192: "#9040c0",
}

def _res_colour(res):
    return RES_COLOURS.get(res, "#a0a0a0")


def _cc4_main_window():
    """CC4's main window, so this window stays in front of it. None if unavailable."""
    try:
        import RLPy
        from shiboken2 import wrapInstance
        return wrapInstance(int(RLPy.RUi.GetMainWindow()), QtWidgets.QMainWindow)
    except Exception:
        return None


class PublisherWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent or _cc4_main_window())
        self.settings  = load_settings()
        self._plan     = []   # current resize plan
        self.setWindowTitle(f"Game Ready Publisher v{__version__}")

        self.setMinimumWidth(520)
        self.setMinimumHeight(600)
        self.setStyleSheet(STYLE)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)
        self._build_ui()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        title = QtWidgets.QLabel("Game Ready Publisher")
        title.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #78be00; padding-bottom: 2px;"
        )
        root.addWidget(title)

        note = QtWidgets.QLabel(
            "Workflow:  1) Convert to Game Base in CC4  →  "
            "2) Scan & Resize here  →  "
            "3) Merge Material UV in CC4  →  4) Export FBX in CC4"
        )
        note.setStyleSheet("color: #888; font-size: 9pt;")
        note.setWordWrap(True)
        root.addWidget(note)

        # ── Texture Resize Plan ───────────────────────────────────────
        plan_grp = QtWidgets.QGroupBox("Texture Resize Plan")
        plan_layout = QtWidgets.QVBoxLayout(plan_grp)

        # Scan button
        scan_btn = QtWidgets.QPushButton("🔍  Scan Character Textures")
        scan_btn.setToolTip("Query CC4 materials and build the resize plan")
        scan_btn.clicked.connect(self._scan)
        plan_layout.addWidget(scan_btn)

        # Table — Material | Current | Target (editable dropdown)
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Material", "Current Size", "Target Size"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(280)
        plan_layout.addWidget(self.table)

        # Rule buttons
        rules_row = QtWidgets.QHBoxLayout()
        reset_btn = QtWidgets.QPushButton("↺  Reset to Rules")
        reset_btn.setToolTip("Restore all target sizes to the keyword-matched rules")
        reset_btn.clicked.connect(self._reset_to_defaults)
        rules_row.addWidget(reset_btn)
        edit_rules_btn = QtWidgets.QPushButton("📝  Edit Rules File…")
        edit_rules_btn.setToolTip(
            "Open rules.json to change which keywords map to which sizes.\n"
            "Save it, then click Scan or Reset to Rules."
        )
        edit_rules_btn.clicked.connect(self._open_rules_file)
        rules_row.addWidget(edit_rules_btn)
        plan_layout.addLayout(rules_row)

        root.addWidget(plan_grp)

        # ── Action buttons ────────────────────────────────────────────
        btn_layout = QtWidgets.QHBoxLayout()

        self.resize_btn = QtWidgets.QPushButton("⚡  Resize All Textures")
        self.resize_btn.setObjectName("resizeBtn")
        self.resize_btn.setToolTip(
            "Resize the Diffuse channel of each material to its target size.\n"
            "This drives UV atlas allocation in Merge Material UV.\n"
            "After resizing, run Merge Material UV manually in CC4."
        )
        self.resize_btn.clicked.connect(self._run_resize)
        btn_layout.addWidget(self.resize_btn)

        root.addLayout(btn_layout)

        # ── Status ────────────────────────────────────────────────────
        self.status_label = QtWidgets.QLabel(
            "Ready.  Load a Game Base character in CC4 then click Scan."
        )
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        if not tt.PILLOW_OK:
            self.resize_btn.setEnabled(False)
            self._set_status(
                "Pillow is not installed in CC4's Python, so textures can't be resized.\n"
                "See INSTALL.md for the one-line install command.", ok=False
            )

    # ---------------------------------------------------------------- status -

    def _set_status(self, msg, ok=True):
        c = "#90c890" if ok else "#d07070"
        self.status_label.setStyleSheet(
            f"background-color:#1a1a1a; border:1px solid #444; border-radius:3px;"
            f"padding:6px 8px; color:{c}; font-size:9pt;"
        )
        self.status_label.setText(msg)
        QtWidgets.QApplication.processEvents()

    # ------------------------------------------------------------------ scan -

    def _scan(self):
        avatar = tt.get_avatar()
        if not avatar:
            self._set_status("No avatar in scene — load a character first.", ok=False)
            return

        self.settings = load_settings()
        self._set_status("Scanning materials…")
        self._plan = tt.build_resize_plan(avatar, self.settings)

        self.table.setRowCount(0)
        for i, entry in enumerate(self._plan):
            self.table.insertRow(i)

            mat     = entry["material"]
            cur_w   = entry.get("current_w", 0)
            cur_h   = entry.get("current_h", 0)
            cur_str = f"{cur_w}×{cur_h}" if cur_w else "?"
            res     = entry["resolution"]
            colour  = _res_colour(res)

            mat_item = QtWidgets.QTableWidgetItem(mat)
            cur_item = QtWidgets.QTableWidgetItem(cur_str)
            cur_item.setTextAlignment(QtCore.Qt.AlignCenter)

            # Editable target size dropdown
            combo = QtWidgets.QComboBox()
            for opt in SIZE_OPTIONS:
                combo.addItem(opt)
            # Set current value
            target_str = "DELETE" if res == 0 else str(res)
            idx = combo.findText(target_str)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.setProperty("row", i)
            combo.currentTextChanged.connect(self._on_size_changed)

            # Colour the material name by target size
            mat_item.setForeground(QtGui.QColor(colour))

            self.table.setItem(i, 0, mat_item)
            self.table.setItem(i, 1, cur_item)
            self.table.setCellWidget(i, 2, combo)

        n = len(self._plan)
        r = len([e for e in self._plan if e["action"] == "resize"])
        d = len([e for e in self._plan if e["action"] == "delete"])
        s = len([e for e in self._plan if e["action"] == "skip"])
        self._set_status(
            f"Found {n} material(s) — {r} to resize, {d} to delete, {s} already correct.\n"
            f"Edit target sizes in the dropdown, then click Resize All Textures."
        )

    def _on_size_changed(self, text):
        """Update the plan entry when user changes a dropdown."""
        combo  = self.sender()
        row    = combo.property("row")
        if row is None or row >= len(self._plan):
            return
        entry  = self._plan[row]
        res    = 0 if text == "DELETE" else int(text)
        cur_w  = entry.get("current_w", 0)

        entry["resolution"] = res
        if res == 0:
            entry["action"] = "delete"
        elif cur_w == res:
            entry["action"] = "skip"
        else:
            entry["action"] = "resize"

        # Update material name colour
        colour   = _res_colour(res)
        mat_item = self.table.item(row, 0)
        if mat_item:
            mat_item.setForeground(QtGui.QColor(colour))

    def _reset_to_defaults(self):
        """Re-apply keyword rules to all rows."""
        self.settings = load_settings()
        for i, entry in enumerate(self._plan):
            res    = resolve_resolution(
                entry["material"], entry["mesh"], self.settings
            )
            entry["resolution"] = res
            combo  = self.table.cellWidget(i, 2)
            if combo:
                target_str = "DELETE" if res == 0 else str(res)
                idx = combo.findText(target_str)
                if idx >= 0:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(idx)
                    combo.blockSignals(False)
            colour   = _res_colour(res)
            mat_item = self.table.item(i, 0)
            if mat_item:
                mat_item.setForeground(QtGui.QColor(colour))
        self._set_status("Reset to defaults.")

    # --------------------------------------------------------------- resize --

    def _run_resize(self):
        if not self._plan:
            self._set_status("Run Scan first.", ok=False)
            return

        avatar = tt.get_avatar()
        if not avatar:
            self._set_status("No avatar in scene.", ok=False)
            return

        self._set_status("Resizing textures…")
        result = tt.execute_resize_plan(avatar, self._plan)
        n = len(result["resized"])
        d = len(result["deleted"])
        e = len(result["errors"])
        s = len(result["skipped"])

        if e:
            self._set_status(
                f"✘  Done with {e} error(s). {n} resized, {d} deleted, {s} skipped.\n"
                f"Check Script → Console Log for details.", ok=False
            )
        else:
            self._set_status(
                f"✔  Textures done — {n} resized, {d} deleted, {s} skipped.\n"
                f"Now run Merge Material UV in CC4 (Material List → dropdown)."
            )

    # ----------------------------------------------------------------- rules -

    def _open_rules_file(self):
        try:
            path = ensure_rules_file()
        except Exception as e:
            self._set_status(f"Could not create the rules file: {e}", ok=False)
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
            self._set_status(f"Opened {path}\nSave your changes, then click Scan.")
        except Exception:
            self._set_status(f"Rules file: {path}\nOpen it in any text editor.")
