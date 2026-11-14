# Birdman64 HD Texture Builder

Builds a 4× HD texture pack for [Birdman64](https://github.com/NoahVl/Birdman64), the native PC port of Pilotwings 64, **from your own ROM**, on your own PC, with no manual steps.

Put your ROM in a folder, double-click `build.bat`, and 15 minutes or so later Birdman64 starts in HD: sharper terrain, cliffs, buildings, runways, vehicles, menus and gauges, with the sky, lettering and backgrounds handled so they stay true to the original.

This repository contains **no game data**: no ROM, no textures, no saves. The pack is made on your machine from the game you own, the same "bring your own ROM" approach Birdman64 takes.

## Quick start

1. Install and run [Birdman64](https://github.com/NoahVl/Birdman64/releases) once, so it has a settings folder.
2. Download this repository (green **Code** button → **Download ZIP**) and unzip it anywhere.
3. Put your Pilotwings 64 ROM (`.z64`, `.n64`, `.v64`, or a `.zip` containing one) in the `rom` folder.
4. Double-click `build.bat`.
5. When it says **Done**, start Birdman64.

The pack is installed to `%APPDATA%\Birdman64\packs\PW64-HD` and selected for you. Your previous settings file is kept as `pw64.toml.before-hd-pack`. You can switch the pack on or off in Birdman64 under **Settings → Display & graphics → Texture pack**.

If the build is interrupted, run `build.bat` again: it continues where it stopped.

## Requirements

- Windows 10 or 11, 64-bit
- A graphics card with Vulkan support (any recent NVIDIA, AMD or Intel GPU). A full build takes about 12 minutes on an RTX 3080 Laptop GPU, including the downloads; integrated graphics will take considerably longer.
- About 1.5 GB of free disk space while building (the finished pack is about 70 MB)
- An internet connection for the first run (the tools below are downloaded once)
- Your own Pilotwings 64 ROM (the US version, as Birdman64 requires)

Nothing is installed system-wide. Everything the builder downloads stays in the `tools` folder.

## What it does

`build.bat` runs these steps, with progress shown in the window:

1. **Tools.** Downloads three things into `tools`, each pinned to a fixed version and checked against a SHA-256 checksum:
   - [uv](https://github.com/astral-sh/uv), a small Python runner. It fetches its own Python 3.12, Pillow and NumPy.
   - [Birdman64 1.5.1](https://github.com/NoahVl/Birdman64/releases/tag/v1.5.1). The build drives the game's menus by script, so it uses this exact version rather than whatever version you play.
   - [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) (ncnn-Vulkan build), the AI upscaler.
2. **Game.** Birdman64 builds the game from your ROM, in a scratch folder (`work`). Your own saves and settings are never used.
3. **Scratch save.** Unlocks every event in a scratch save using Birdman64's built-in *Unlock everything* option. A Birdman64 window appears for a few seconds during this step.
4. **Texture collection.** Plays every event with no window, using scripted controller input: every vehicle, class and test, all Extra Games levels, Birdman on all four islands, the intro demos and the results screens. Birdman64 saves each texture as it is drawn. This collects about 3,900 textures.
5. **Upscaling.** Each texture is handled one of these ways:
   - **Most textures:** 4× with Real-ESRGAN (`realesrgan-x4plus`). Textures that repeat across the landscape stay seamless, and each result is checked against the original; anything that doesn't match keeps the original.
   - **HUD lettering and font sheets:** plain 4× pixel enlargement. The AI redraws small letters (it turned *SEA LEVEL* into *SEN LEVEL*).
   - **Sky, cloud, haze and sea layers:** an exact smooth enlargement. The AI invents hard streaks in soft layers. These are also offset to cancel a small sampling difference in how Birdman64 draws pack textures, which otherwise shows as a ribbon across the sky.
   - **2D backgrounds** that the game draws in thin strips (pilot select, title screen): smooth enlargement, so the strips still line up.
   - Textures smaller than 8 px are left as they are.
6. **Install.** Copies `output\PW64-HD` into Birdman64's `packs` folder and selects it.

The lists of special-case textures are in `pw64hd/data/` (`nearest.txt` and `smooth.txt`). They contain only Birdman64's texture IDs (hashes), no image data.

## Options

Run these from a command prompt in the builder folder:

```bat
build.bat --no-install
```
Only builds `output\PW64-HD`. Copy that folder into Birdman64's `packs` folder yourself.

```bat
build.bat --install-dir "D:\Games\Birdman64"
```
Installs into a different Birdman64 data folder, for example a portable install (one that keeps `pw64.eep` next to `Birdman64.exe`).

## Troubleshooting

- **"No ROM found"**: put the ROM file itself (or a zip containing it) directly in the `rom` folder.
- **"could not build the game from your ROM"**: Birdman64 didn't accept the ROM. Check that it's the US version and that it runs in Birdman64 normally. The details are in `work\logs\first_build.log`.
- **"Unlocking the scratch save failed"**: see `work\logs\unlock.log`. Don't click or type in the Birdman64 window while it's open.
- **The upscaling step is very slow**: Real-ESRGAN uses the first Vulkan GPU it finds. On a laptop with two GPUs, set Windows Graphics settings to use the high-performance GPU for `realesrgan-ncnn-vulkan.exe` (in `tools\realesrgan`).
- **Start over from scratch**: delete the `work` and `output` folders and run `build.bat` again.

## Sharing

Please don't upload a built pack. It is made from Nintendo's artwork. Share this builder instead, so everyone builds the pack from their own copy of the game.

## Credits

- [Birdman64](https://github.com/NoahVl/Birdman64) (MIT) for the port, its texture-pack support, and the automation hooks that make this possible. `pw64hd/data/fly_hang_glider_finish.txt` is copied from its test scripts.
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) (BSD-3-Clause) by Xintao Wang et al., and its [ncnn-Vulkan port](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan).
- [uv](https://github.com/astral-sh/uv) (MIT / Apache-2.0) by Astral.

Not affiliated with or endorsed by Nintendo or Paradigm. Pilotwings is a trademark of Nintendo.

## License

The builder's code is MIT-licensed. See [LICENSE](LICENSE).
