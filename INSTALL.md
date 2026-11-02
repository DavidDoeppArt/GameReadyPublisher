# Installing Game Ready Publisher

**Requires:** Character Creator 4 (built and tested on CC4 4.0, Windows). CC5 is untested.

## 1. Copy the plugin

Copy the whole `GameReadyPublisher` folder into CC4's plugin folder:

```
C:\Program Files\Reallusion\Character Creator 4\Bin64\OpenPlugin\
```

You should end up with:

```
...\Bin64\OpenPlugin\GameReadyPublisher\main.py
...\Bin64\OpenPlugin\GameReadyPublisher\game_ready_publisher\...
```

Windows will ask for administrator permission because this is inside Program Files.
If CC4 is installed somewhere else, use that location's `Bin64\OpenPlugin` folder instead.

## 2. Make sure Pillow is installed

The plugin uses the Pillow image library to resize textures. Some CC4 installs already have it.

**To check:** open the plugin (step 3). If Pillow is missing, the window says so and the
Resize button is disabled.

**To install it:** open **Command Prompt as Administrator** and run:

```
"C:\Program Files\Reallusion\Character Creator 4\Bin64\CharacterCreatorpy.exe" -m pip install pillow
```

`CharacterCreatorpy.exe` is CC4's own Python, so Pillow goes where CC4 can find it.
Restart CC4 afterwards.

## 3. Open it

Restart CC4. Open the plugin from **Plugins → Game Ready Publisher → Open**.

You can also run `main.py` from **Script → Load Python**. That reloads the plugin code and opens the window,
which is useful if you're editing the scripts.

## Uninstall

Delete the `GameReadyPublisher` folder from `OpenPlugin`. To also remove your custom rules,
delete `%APPDATA%\GameReadyPublisher`.

## Troubleshooting

**The menu entry doesn't appear.** Check the folder layout above: `main.py` must sit directly inside
`OpenPlugin\GameReadyPublisher`, not one level deeper.

**A texture shows an error after Resize.** Details are printed in CC4's Console Log. Clothing, hair and
accessory textures are the most likely to report a size mismatch.

**"No avatar in scene."** Load a character first, then click Scan.
