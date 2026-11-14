"""Scripted playthrough that makes Birdman64 draw (and dump) every texture.

Menu layout (Birdman64 1.5.1, unlocked save):
- Vehicle & class grid: rows Beginner / A / B / Pilot (stick down = next class),
  columns hang glider / rocket belt / gyrocopter (stick right).
- Extra Games page (3 stick-rights): Birdman row (4 islands, stick right) and
  Cannonball / Sky Diving / Jumble Hopper rows (stick ups) x Level 1-3.
- Test briefing: C-right = next test, A on Start.
Script format: <retrace|+delta> [buttons] [stick X,Y]
"""
import os

T0 = 1100  # the title menu is up at ~1000 retraces


def tap(t, x, y):
    return [f"{t} stick {x},{y}", f"{t + 20} stick 0,0"]


def menus(col=0, row=0, test=0, bonus_ups=None, pilot=0, bonus_right=0):
    L = [f"{T0} A", "+6", f"{T0 + 100} A", "+6"]  # title -> file 1
    t = T0 + 210
    if bonus_ups is None:
        for _ in range(col):
            L += tap(t, 80, 0); t += 70
        for _ in range(row):
            L += tap(t, 0, -80); t += 70
    else:
        for _ in range(3):
            L += tap(t, 80, 0); t += 50
        for _ in range(bonus_ups):
            L += tap(t, 0, -80); t += 50
        for _ in range(bonus_right):
            L += tap(t, 80, 0); t += 50
    t += 60; L += [f"{t} A", "+6"]                 # -> pilot select
    t += 120
    for _ in range(pilot):
        L += tap(t, 80, 0); t += 50
    L += [f"{t} A", "+6"]                           # pilot -> class overview
    t += 140; L += [f"{t} A", "+6"]                 # overview -> briefing
    t += 140
    for _ in range(test):
        L += [f"{t} CR", "+6"]; t += 100
    t += 40; L += [f"{t} A", "+6"]                  # Start
    return L, t + 150                               # flying from about here


def flight(kind, t0, length):
    L, t, i = [], t0, 0
    pattern = [(-60, 0), (0, 0), (0, -50), (60, 0), (0, 0), (0, 50), (-40, -30), (40, 30)]
    while t < t0 + length:
        x, y = pattern[i % len(pattern)]; i += 1
        if kind in ("rocket", "gyro"):
            L.append(f"{t} A stick {x},{y}")          # A = thrust/throttle
        elif kind == "glider":
            L.append(f"{t} stick {x},{y}")
        elif kind == "birdman":
            for k in range(0, 120, 12):
                L += [f"{t + k} A stick {x},{y}", "+6"]   # flap
        elif kind == "cannon":
            L += [f"{t} stick {x // 3},{y // 3}", f"{t + 60} A", "+6"]
        elif kind == "skydive":
            L.append(f"{t} stick {x},{y}")
            if i % 4 == 0:
                L += [f"{t + 30} A", "+6"]
        elif kind == "hopper":
            L += [f"{t} stick {x // 2},-70", f"{t + 40} A", "+6"]
        t += 120
    L.append(f"{t0 + length} stick 0,0")
    return L


def runs():
    """(name, script lines, retraces) for every run, in order."""
    out = [("attract_demos", ["37900 stick 0,0"], 38000)]  # no input: intro + all six demos

    def event(name, kind, length=2400, **kw):
        L, t = menus(**kw)
        out.append((name, L + flight(kind, t, length), t + length + 300))

    for kind, col in (("glider", 0), ("rocket", 1), ("gyro", 2)):
        for row, cname in enumerate(("beg", "A", "B", "pilot")):
            for test in range(3 if row < 3 else 4):
                event(f"{kind}_{cname}_t{test + 1}", kind, col=col, row=row, test=test,
                      pilot=(col * 2 + row + test) % 6)
    for lvl in range(3):
        event(f"cannon_L{lvl + 1}", "cannon", 1800, bonus_ups=1, bonus_right=lvl)
        event(f"skydive_L{lvl + 1}", "skydive", 2000, bonus_ups=2, bonus_right=lvl)
        event(f"hopper_L{lvl + 1}", "hopper", 2400, bonus_ups=3, bonus_right=lvl)
    for isl in range(4):
        for test in range(4):
            event(f"birdman_i{isl + 1}_t{test + 1}", "birdman", bonus_ups=0, bonus_right=isl, test=test)

    # results + photo screens: Birdman64's own test script (MIT, see data/README)
    here = os.path.join(os.path.dirname(__file__), "data", "fly_hang_glider_finish.txt")
    lines = [l for l in open(here, encoding="utf-8-sig").read().splitlines()
             if l.strip() and not l.lstrip().startswith("#")]
    out.append(("results_screens", lines, 4400))
    return out
