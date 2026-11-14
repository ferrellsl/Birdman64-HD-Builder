"""Build the PW64-HD texture pack for Birdman64 from the user's own ROM.

  python -m pw64hd.build [--no-install] [--install-dir DIR]

Steps (each one is skipped on a re-run once it has finished):
  1. find the ROM in rom/
  2. download Birdman64 1.5.1 and Real-ESRGAN (pinned, checksum-verified)
  3. let Birdman64 build the game from the ROM, unlock a scratch save
  4. play every event headless, dumping textures (about 3,900)
  5. upscale them into output/PW64-HD
  6. install into Birdman64's packs folder and select it
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.request
import zipfile

from . import play
from .game import Game
from .upscale import build_pack

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
WORK = os.path.join(ROOT, "work")
OUTPUT = os.path.join(ROOT, "output", "PW64-HD")

DOWNLOADS = {
    "birdman64": dict(
        url="https://github.com/NoahVl/Birdman64/releases/download/v1.5.1/Birdman64-windows-x64.zip",
        sha256="b03ca52fccb59d108854f2b955d0e3b0206a6bce9dbcf82edc2a5f2562232d5c",
        dir=os.path.join(TOOLS, "birdman64-1.5.1"), exe="Birdman64.exe"),
    "realesrgan": dict(
        url="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip",
        sha256="abc02804e17982a3be33675e4d471e91ea374e65b70167abc09e31acb412802d",
        dir=os.path.join(TOOLS, "realesrgan"), exe="realesrgan-ncnn-vulkan.exe"),
}


def say(msg="", end="\n"):
    print(msg, end=end, flush=True)


def fetch(name):
    d = DOWNLOADS[name]
    found = glob.glob(os.path.join(d["dir"], "**", d["exe"]), recursive=True)
    if found:
        return found[0]
    os.makedirs(d["dir"], exist_ok=True)
    z = os.path.join(d["dir"], "download.zip")
    say(f"  downloading {os.path.basename(d['url'])} ...")
    urllib.request.urlretrieve(d["url"], z)
    h = hashlib.sha256(open(z, "rb").read()).hexdigest()
    if h != d["sha256"]:
        os.remove(z)
        raise RuntimeError(f"{name}: download checksum mismatch ({h})")
    with zipfile.ZipFile(z) as zf:
        zf.extractall(d["dir"])
    os.remove(z)
    return glob.glob(os.path.join(d["dir"], "**", d["exe"]), recursive=True)[0]


def find_rom():
    roms = [p for p in glob.glob(os.path.join(ROOT, "rom", "*"))
            if p.lower().endswith((".z64", ".n64", ".v64", ".zip"))]
    if not roms:
        raise RuntimeError("No ROM found. Put your Pilotwings 64 ROM (.z64, .n64, .v64 or .zip) "
                           "in the 'rom' folder and run build.bat again.")
    if len(roms) > 1:
        raise RuntimeError("More than one file in the 'rom' folder - leave just the Pilotwings 64 ROM there.")
    return roms[0]


class Progress:
    def __init__(self):
        self.path = os.path.join(WORK, "progress.json")
        self.done = json.load(open(self.path)) if os.path.exists(self.path) else {}

    def mark(self, key, value=True):
        self.done[key] = value
        json.dump(self.done, open(self.path, "w"), indent=1)


def install(pack, target_data_dir):
    dst = os.path.join(target_data_dir, "packs", "PW64-HD")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(pack, dst)
    toml = os.path.join(target_data_dir, "pw64.toml")
    text = open(toml, encoding="utf-8").read() if os.path.exists(toml) else ""
    if text:
        shutil.copy(toml, toml + ".before-hd-pack")
    line = 'texture_pack = "PW64-HD"'
    if re.search(r"^\s*texture_pack\s*=.*$", text, re.M):
        text = re.sub(r"^\s*texture_pack\s*=.*$", line, text, count=1, flags=re.M)
    elif re.search(r"^\[graphics\]\s*$", text, re.M):
        text = re.sub(r"^\[graphics\]\s*$", "[graphics]\n" + line, text, count=1, flags=re.M)
    else:
        text = text.rstrip() + ("\n\n" if text.strip() else "") + "[graphics]\n" + line + "\n"
    open(toml, "w", encoding="utf-8").write(text)
    return dst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-install", action="store_true", help="only build output/PW64-HD")
    ap.add_argument("--install-dir", help="Birdman64 data folder (default %%APPDATA%%\\Birdman64)")
    ap.add_argument("--quick", action="store_true", help=argparse.SUPPRESS)  # smoke test: 2 short runs
    args = ap.parse_args()
    t_start = time.time()
    os.makedirs(WORK, exist_ok=True)
    prog = Progress()

    say("Birdman64 HD texture pack builder\n")
    rom = find_rom()
    say(f"[1/6] ROM: {os.path.basename(rom)}")

    say("[2/6] Tools")
    exe = fetch("birdman64")
    esrgan = fetch("realesrgan")
    game = Game(exe, rom, WORK)

    say("[3/6] Preparing the game (first start builds it from your ROM; a few minutes)")
    if not prog.done.get("first_build"):
        game.first_build(); prog.mark("first_build")
    say("      Unlocking a scratch save (a Birdman64 window opens for a few seconds)...")
    game.unlock()

    runs = play.runs()
    if args.quick:
        runs = [r for r in runs if r[0] in ("gyro_B_t2", "birdman_i1_t2")]
    say(f"[4/6] Playing every event headless to collect textures ({len(runs)} runs)")
    for i, (name, lines, retraces) in enumerate(runs, 1):
        if prog.done.get("run:" + name):
            continue
        new = game.play(name, lines, retraces)
        prog.mark("run:" + name)
        say(f"      {i:2}/{len(runs)} {name:<22} +{new:<4} textures (total {game.tex_count()})")

    say(f"[5/6] Upscaling {game.tex_count()} textures into output\\PW64-HD (the longest step)")
    failed = build_pack(game.tex, OUTPUT, esrgan, log=say)
    n = len(glob.glob(os.path.join(OUTPUT, "*.png")))
    size = sum(os.path.getsize(p) for p in glob.glob(os.path.join(OUTPUT, "*.png"))) / 2**20
    say(f"      pack: {n} textures, {size:.0f} MB" + (f" ({failed} kept their original)" if failed else ""))

    if args.no_install:
        say("[6/6] Not installing (--no-install). Copy output\\PW64-HD into Birdman64's 'packs' folder.")
    else:
        target = args.install_dir or os.path.join(os.environ.get("APPDATA", ""), "Birdman64")
        if not os.path.isdir(target):
            say(f"[6/6] {target} not found - start Birdman64 once, or copy output\\PW64-HD into its 'packs' folder yourself.")
        else:
            dst = install(OUTPUT, target)
            say(f"[6/6] Installed to {dst} and selected in pw64.toml (backup: pw64.toml.before-hd-pack).")
    say(f"\nDone in {(time.time() - t_start) / 60:.0f} minutes. Start Birdman64 to fly in HD.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        say(f"\nERROR: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        say("\nStopped. Run build.bat again to continue where it left off.")
        sys.exit(1)
