"""
Texture resize workflow (tested in CC4 4.0):

  1. MaterialComponent.GetImage(mesh, mat, channel)  -> current image and size
  2. image.SaveFile(temp_path)                        -> export to a temp PNG
  3. Pillow resize, keeping the ICC colour profile
  4. MaterialComponent.LoadImageToTexture(...)        -> reimport
  5. GetImage again to confirm the new size

Removal uses MaterialComponent.RemoveMaterialTexture(mesh, mat, channel).

Only the Diffuse channel is processed. In CC4 4.0 resizing other channels
(Roughness, Bump, ...) failed silently or corrupted the texture, and the
Diffuse size is what drives UV atlas allocation in Merge Material UV.
"""

import os
import tempfile

from .settings import resolve_resolution

try:
    from PIL import Image
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False
    print("[GameReadyPublisher] Pillow is not installed - see INSTALL.md.")

try:
    import RLPy
    RLPY_OK = True
except ImportError:
    RLPY_OK = False

# CC4 fills empty or procedural slots with small placeholder images
# (e.g. 616x616). Anything under this size is left alone.
MIN_SOURCE_SIZE = 1024


def get_avatar():
    if not RLPY_OK:
        return None
    avatars = RLPy.RScene.GetAvatars()
    return avatars[0] if avatars else None


def _working_dir():
    d = os.path.join(tempfile.gettempdir(), "GameReadyPublisher")
    os.makedirs(d, exist_ok=True)
    return d


def _action_for(target_res, w, h):
    if target_res == 0:
        return "delete"
    if w == target_res and h == target_res:
        return "skip"
    return "resize"


def build_resize_plan(avatar, settings):
    """List every Diffuse texture on the avatar with its current and target size."""
    if not RLPY_OK:
        return []

    mc = avatar.GetMaterialComponent()
    diffuse = getattr(RLPy, "EMaterialTextureChannel_Diffuse", None)
    if not mc or diffuse is None:
        print("[GameReadyPublisher] Could not access the avatar's materials.")
        return []

    plan = []
    for mesh_name in avatar.GetMeshNames():
        try:
            mat_names = mc.GetMaterialNames(mesh_name)
        except Exception as e:
            print(f"[GameReadyPublisher] GetMaterialNames failed for {mesh_name}: {e}")
            continue

        for mat_name in mat_names:
            try:
                img = mc.GetImage(mesh_name, mat_name, diffuse)
                if not img:
                    continue
                w, h = img.GetWidth(), img.GetHeight()
            except Exception as e:
                print(f"[GameReadyPublisher] Could not read {mat_name}: {e}")
                continue

            if w < MIN_SOURCE_SIZE and h < MIN_SOURCE_SIZE:
                continue

            target = resolve_resolution(mat_name, mesh_name, settings)
            plan.append({
                "mesh":         mesh_name,
                "material":     mat_name,
                "channel":      diffuse,
                "channel_name": "Diffuse",
                "resolution":   target,
                "action":       _action_for(target, w, h),
                "current_w":    w,
                "current_h":    h,
            })

    order = {"delete": 0, "resize": 1, "skip": 2}
    plan.sort(key=lambda e: (order[e["action"]], e["mesh"], e["material"]))
    return plan


def execute_resize_plan(avatar, plan):
    result = {"resized": [], "deleted": [], "skipped": [], "errors": []}

    if not RLPY_OK:
        result["errors"].append("RLPy not available.")
        return result
    if not PILLOW_OK:
        result["errors"].append("Pillow is not installed - see INSTALL.md.")
        return result

    mc = avatar.GetMaterialComponent()
    if not mc:
        result["errors"].append("Could not access the avatar's materials.")
        return result

    work_dir = _working_dir()

    for entry in plan:
        mesh, mat = entry["mesh"], entry["material"]
        channel, res = entry["channel"], entry["resolution"]
        label = f"{mat} / {entry['channel_name']}"

        if entry["action"] == "skip":
            result["skipped"].append(label)
            continue

        if entry["action"] == "delete":
            try:
                mc.RemoveMaterialTexture(mesh, mat, channel)
                print(f"[GameReadyPublisher] Removed: {label}")
                result["deleted"].append(label)
            except Exception as e:
                result["errors"].append(f"Remove {label}: {e}")
            continue

        try:
            safe_mat = mat.replace(" ", "_").replace("/", "_")
            temp_path = os.path.join(work_dir, f"{safe_mat}_{entry['channel_name']}.png")

            # Fetch the image fresh: an earlier reimport can make a cached handle stale.
            img = mc.GetImage(mesh, mat, channel)
            if not img or img.GetWidth() == 0:
                result["errors"].append(f"Resize {label}: could not read the image")
                continue
            img.SaveFile(temp_path)
            if not os.path.exists(temp_path):
                result["errors"].append(f"Resize {label}: could not export the image")
                continue

            # Keep the ICC profile so colours don't shift after reimport.
            with Image.open(temp_path) as src:
                icc = src.info.get("icc_profile")
                print(f"[GameReadyPublisher] Resizing {label}: "
                      f"{src.size[0]}x{src.size[1]} -> {res}x{res}")
                resized = src.resize((res, res), Image.LANCZOS)
            if icc:
                resized.save(temp_path, "PNG", icc_profile=icc)
            else:
                resized.save(temp_path, "PNG")

            mc.LoadImageToTexture(mesh, mat, channel, temp_path)

            check = mc.GetImage(mesh, mat, channel)
            new_w = check.GetWidth() if check else 0
            new_h = check.GetHeight() if check else 0
            if new_w == res and new_h == res:
                result["resized"].append(label)
            else:
                result["errors"].append(
                    f"Resize {label}: size is {new_w}x{new_h} after reload, expected {res}x{res}"
                )
        except Exception as e:
            result["errors"].append(f"Resize {label}: {e}")

    for err in result["errors"]:
        print(f"[GameReadyPublisher] ERROR: {err}")
    return result
