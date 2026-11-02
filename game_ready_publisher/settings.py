"""
Resolution rules and their storage.

Each rule maps keywords (matched against material, then mesh names) to a
target texture size. A size of 0 means the texture is removed.
Rules are checked in order and the first match wins.

Users can override the rules in rules.json, stored in their own profile
(%APPDATA%\\GameReadyPublisher) so nothing is written to Program Files.
"""

import json
import os

DEFAULT_RESOLUTION_RULES = [
    {"keywords": ["skin_head", "head"],                                       "resolution": 8192},
    {"keywords": ["skin_body", "body"],                                       "resolution": 512},
    {"keywords": ["skin_arm",  "arm"],                                        "resolution": 512},
    {"keywords": ["skin_leg",  "leg"],                                        "resolution": 512},
    {"keywords": ["tongue"],                                                  "resolution": 128},
    {"keywords": ["nail"],                                                    "resolution": 256},
    {"keywords": ["eyelash", "lash", "tearline"],                             "resolution": 0},
    {"keywords": ["eye"],                                                     "resolution": 256},
    {"keywords": ["teeth", "tooth"],                                          "resolution": 256},
    {"keywords": ["pant", "trouser"],                                         "resolution": 2048},
    {"keywords": ["shirt", "top", "coat", "jacket", "labcoat"],               "resolution": 2048},
    {"keywords": ["shoe", "slipper", "boot", "loafer", "sandal", "sneaker"],  "resolution": 512},
]

DEFAULTS = {
    "default_resolution": 2048,
    "resolution_rules":   DEFAULT_RESOLUTION_RULES,
}


def config_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "GameReadyPublisher")


def rules_path() -> str:
    return os.path.join(config_dir(), "rules.json")


def load_settings() -> dict:
    merged = json.loads(json.dumps(DEFAULTS))  # deep copy
    path = rules_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                merged.update(json.load(f))
        except Exception as e:
            print(f"[GameReadyPublisher] Could not read {path}: {e}. Using defaults.")
    return merged


def ensure_rules_file() -> str:
    """Write the default rules to rules.json if it doesn't exist yet. Returns its path."""
    path = rules_path()
    if not os.path.exists(path):
        os.makedirs(config_dir(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULTS, f, indent=4)
    return path


def resolve_resolution(material_name: str, mesh_name: str, settings: dict) -> int:
    """
    Target size for a material. 0 means remove the texture.

    The material name is checked on its own first, then the mesh name, so a
    material like "Ga_Eyelash" on the mesh "CC_Game_Body" matches the eyelash
    rule rather than the body rule.
    """
    rules = settings.get("resolution_rules", DEFAULT_RESOLUTION_RULES)
    for name in (material_name.lower(), mesh_name.lower()):
        for rule in rules:
            for kw in rule["keywords"]:
                if kw.lower() in name:
                    return rule["resolution"]
    return settings.get("default_resolution", 2048)
