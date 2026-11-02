"""
Game Ready Publisher - Character Creator 4 plugin entry point.

CC4 loads OpenPlugin/<folder>/main.py at startup and calls initialize_plugin(),
which adds  Plugins > Game Ready Publisher > Open  to the menu bar.
Running this file from Script > Load Python calls run_script() instead, which
reloads the plugin modules and opens the window (handy while editing the code).
"""

import importlib
import os
import sys

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

import RLPy
from PySide2 import QtWidgets
from shiboken2 import wrapInstance

import game_ready_publisher
from game_ready_publisher import settings, textures, ui

MENU_NAME = "Game Ready Publisher"

_window = None


def _plugin_menu():
    rl_menu = RLPy.RUi.FindMenu(MENU_NAME)
    if not rl_menu:
        rl_menu = RLPy.RUi.AddMenu(MENU_NAME, RLPy.EMenu_Plugins)
    return wrapInstance(int(rl_menu), QtWidgets.QMenu)


def show_window():
    global _window
    if _window is not None:
        _window.close()
    _window = ui.PublisherWindow()
    _window.show()
    _window.raise_()
    _window.activateWindow()


def initialize_plugin():
    menu = _plugin_menu()
    menu.clear()
    action = menu.addAction("Open")
    action.triggered.connect(show_window)
    print(f"[GameReadyPublisher] v{game_ready_publisher.__version__} loaded.")


def uninitialize_plugin():
    global _window
    if _window is not None:
        _window.close()
        _window = None
    print("[GameReadyPublisher] Unloaded.")


def run_script():
    """Called by CC4 when this file is run via Script > Load Python."""
    for module in (settings, textures, ui):
        importlib.reload(module)
    initialize_plugin()
    show_window()
