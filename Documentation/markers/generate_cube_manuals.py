"""
Generates the illustrated manuals (Czech, A4 PDF) for the physical cube of the Cube Arc game:
  Navod_lepeni_markeru.pdf   - sticking the six printed markers (cube_markers_50mm.pdf) on a cube,
  Navod_kostka_z_kartonu.pdf - building a cardboard cube and wrapping it (cube_wrap_50mm.pdf),
  Navod_rubikova_kostka.pdf  - glue-free sleeve around a 55 mm Rubik's cube (cube_sleeve_55mm.pdf).

Usage:
    python generate_cube_manuals.py

The illustrations are drawn by cube_drawing.py with the real markers in the orientation required by
CubeFaceLayout.cs. Needs Chrome or Edge to turn the HTML into PDF (set BROWSER to its path if it is
not found); no Python packages.
"""
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

from cube_drawing import (ACCENT, BOARD, CELL, HALF, INK, Fig, Frame, add, face_frame, fold_net, mul, tab_points)
from generate_cube_markers import TOTAL_WIDTH
from generate_cube_wrap import (FACE_NAMES, FOLDS, NET, TABS, face_corners, outline, panel_sizes, side_points,
                                tab_polygon)

HERE = pathlib.Path(__file__).resolve().parent
BLANK = ("#eef0f2", "#dde1e5", "#c8ced4")  # plain cube of any material
RED, GREEN = "#c92a2a", "#2b8a3e"


# ---------------------------------------------------------------- shared pieces

def stuck(fig, faces, transform=None, palette=BLANK, names=()):
    """Cube with the given markers already on it; names = [(face, text)] written on bare faces."""
    fig.cube(palette=palette)
    for face in range(6):
        fr = face_frame(face)
        if transform:
            fr = fr.transformed(transform)
        if not fig.facing(fr.normal):
            continue
        if face in faces:
            fig.marker(fr, face)
        else:
            for f, s in names:
                if f == face:
                    fig.face_text(fr, s, size=22, color="#6b7280")


def hover(fig, frame, tag_id, distance=24, corner=2):
    """A marker square floating in front of its face, with guide lines and an arrow along one of them."""
    away = mul(frame.normal, distance)
    for c in frame.corners():
        fig.line3(c, add(c, away), stroke="#9aa0a6", width=0.3, dash="1.2 1.2")
    top = frame.moved(away)
    fig.plane_arrow(top)
    fig.marker(top, tag_id, stroke=ACCENT, width=0.7)
    c = frame.corners()[corner]
    fig.arrow3(add(c, mul(away, 0.8)), add(c, mul(away, 0.12)), color=INK, width=0.8)


def flat_tag(fig, x, y, size, tag_id, stroke="#888", dash=None, shadow=False):
    """Marker square drawn flat on the page with its top left corner at (x, y)."""
    f = Fig(fig.w, fig.h, az=0, el=0, scale=size / 50, cx=x + size / 2, cy=y + size / 2)
    if shadow:
        fig.add(f'<rect x="{x + 0.7}" y="{y + 0.7}" width="{size}" height="{size}" fill="#00000022"/>')
    f.marker(Frame((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)), tag_id, stroke=stroke, width=0.3,
             palette=("#fff", "#fff", "#fff"))
    fig.add(f.svg().split(">", 1)[1].rsplit("</svg>", 1)[0])


def flat_net(fig, x, y, scale, labels=True):
    """The whole wrap drawn flat; (x, y) is the middle of its top edge."""
    def at(points):
        return [(x + px * scale, y + py * scale) for px, py in points]

    fig.poly2(at(outline(50)), fill="#fff", width=0.4)
    for face, side, _ in TABS:
        fig.poly2(at(tab_polygon(face, side, 50)), fill="#e9e7e3", width=0.25)
    for face, (_, _, down) in NET.items():
        left, top = face_corners(face, 50)["TL"]
        cx, cy = at([(left + 25, top + 25)])[0]
        sub = Fig(fig.w, fig.h, az=0, el=0, scale=scale, cx=cx, cy=cy)
        fr = Frame((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
        sub.tag(fr.turned() if down else fr, face)
        fig.add(sub.svg().split(">", 1)[1].rsplit("</svg>", 1)[0])
    for face, side in FOLDS:
        a, b = at(side_points(face, side, 50))
        fig.line2(a, b, stroke="#777", width=0.3, dash="1 0.8")
    return at


def cross_mark(fig, x, y, r=2.6, color=RED):
    fig.line2((x - r, y - r), (x + r, y + r), stroke=color, width=1.2)
    fig.line2((x - r, y + r), (x + r, y - r), stroke=color, width=1.2)


def tick_mark(fig, x, y, r=2.8, color=GREEN):
    fig.add(f'<path d="M{x - r:.2f},{y:.2f} l{r * 0.75:.2f},{r * 0.8:.2f} l{r * 1.3:.2f},{-r * 1.7:.2f}" fill="none" '
            f'stroke="{color}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>')


def finished_views(width=180, height=52, palette=BLANK):
    """Both halves of the finished cube: front/right/top and back/left/bottom, with ID callouts."""
    a = Fig(width, height, az=32, el=26, scale=0.56, cx=width * 0.25, cy=height / 2)
    stuck(a, range(6), palette=palette)
    a.leader(a.p((4, HALF, -16)), (a.cx + 32, 6), 0)
    a.leader(a.p((-12, -12, HALF)), (a.cx - 36, a.cy + 12), 2)
    a.leader(a.p((HALF, -6, -10)), (a.cx + 36, a.cy + 8), 5)
    # From below and behind: turn the cube half a turn about its left-right axis, then look as before
    b = Fig(width, height, az=-32, el=26, scale=0.56, cx=width * 0.75, cy=height / 2)

    def over(v):
        return (v[0], -v[1], -v[2])

    stuck(b, range(6), transform=over, palette=palette)
    b.leader(b.p((-4, HALF, -16)), (b.cx - 32, 6), 1)
    b.leader(b.p((12, -12, HALF)), (b.cx + 36, b.cy + 12), 3)
    b.leader(b.p((-HALF, -6, -10)), (b.cx - 36, b.cy + 8), 4)
    a.out += b.out
    a.line2((width / 2, 6), (width / 2, height - 6), stroke="#ccc", width=0.3)
    return a.svg()


# ---------------------------------------------------------------- manual 1: sticking the printed squares

def m1_check_print():
    f = Fig()
    # sheet of paper
    f.add(f'<rect x="10" y="3" width="68" height="60" fill="#fff" stroke="{INK}" stroke-width="0.35"/>')
    f.text(15, 9, "Cube Arc – markery na kostku 50 mm", size=2.9, anchor="start", weight=500)
    f.add(f'<rect x="15" y="14" width="50" height="1" fill="{INK}"/>')
    for i in range(11):
        f.line2((15.1 + i * 4.98, 15), (15.1 + i * 4.98, 16.4), width=0.25)
    f.text(67, 16, "100 mm", size=2.7, anchor="start", weight=500)
    f.ruler(15, 17, 110, unit=0.5)
    for i in range(2):
        flat_tag(f, 15 + i * 27, 30, 20, i)
    f.add('<rect x="0" y="55" width="88" height="4" fill="#fff"/>')
    f.add(f'<path d="M10,55 q4,-1.6 8,0 t8,0 t8,0 t8,0 t8,0 t8,0 t8,0 t8,0 t4,0" fill="none" stroke="{INK}" stroke-width="0.35"/>')
    f.arrow2((84, 29), (74, 21), bend=-0.25)
    return f.svg()


def m1_cut():
    f = Fig()
    # front: cut along the grey line
    flat_tag(f, 7, 12, 30, 0)
    f.text(22, 46.5, "ID 0 – HORNÍ stěna", size=2.8, weight=500)
    f.text(22, 7, "líc", size=3.6)
    f.scissors(37.4, 45, angle=-90, size=0.95, color=ACCENT)
    # back with pencil note
    f.text(66, 7, "rub", size=3.6)
    f.add(f'<rect x="51" y="12" width="30" height="30" fill="#fbf7ee" stroke="{INK}" stroke-width="0.35"/>')
    f.text(66, 36, "0", size=15, color="#444", weight=500)
    f.arrow2((66, 24), (66, 15), color="#444", width=0.8)
    f.pencil(71.5, 34, angle=-48, size=0.8)
    f.arrow2((39.5, 26), (48.5, 26), bend=-0.35)
    f.text(66, 48.5, "číslo a šipka k horní hraně", size=3, weight=500)
    return f.svg()


def m1_number_cube():
    f = Fig(cx=44, cy=28, scale=0.54)
    stuck(f, (), names=[(0, "0"), (2, "2"), (5, "5")])
    f.leader(f.p((6, HALF, -18)), (f.cx + 22, 4.5), 0)
    f.leader(f.p((-10, -10, HALF)), (f.cx - 33, f.cy + 14), 2)
    f.leader(f.p((HALF, -4, -12)), (f.cx + 33, f.cy + 10), 5)
    # hidden faces
    grey = "#868e96"
    for at, to, n in (((-HALF, 8, 0), (f.cx - 34, f.cy - 12), 4), ((4, 0, -HALF), (f.cx + 33, f.cy - 17), 3)):
        a = f.p(at)
        f.line2(a, to, stroke=grey, width=0.35, dash="1 1")
        f.badge(to[0], to[1], n, fill=grey)
    f.badge(f.cx - 7, 53.5, 1, fill=grey)
    f.arrow2((f.cx - 7, 49.6), (f.cx - 7, 45.6), color=grey, width=0.6)
    return f.svg()


def step_fig(tag, done, az=32, el=26, transform=None, cx=44, cy=31, distance=24, scale=0.5, width=88, height=58, corner=2):
    f = Fig(width, height, az=az, el=el, scale=scale, cx=cx, cy=cy)
    stuck(f, done, transform=transform)
    fr = face_frame(tag)
    if transform:
        fr = fr.transformed(transform)
    hover(f, fr, tag, distance=distance, corner=corner)
    return f


def m1_top():
    f = step_fig(0, (), cy=37.5, distance=23, scale=0.46, corner=1)
    f.text(64, 5.5, "k zadní stěně", size=3.4, anchor="start", color=ACCENT)
    return f.svg()


def m1_front():
    f = step_fig(2, (0,), cx=52, cy=24.5, distance=36)
    f.text(13, 14, "nahoru", size=3.4, color=ACCENT)
    f.text(13, 18.2, "(k ID 0)", size=3.4, color=ACCENT)
    return f.svg()


def m1_right():
    f = step_fig(5, (0, 2), az=38, cx=34, cy=26, distance=40, corner=3)
    f.text(77, 10, "nahoru", size=3.4, color=ACCENT)
    f.text(77, 14.2, "(k ID 0)", size=3.4, color=ACCENT)
    return f.svg()


def m1_left():
    f = step_fig(4, (0, 2, 5), az=-38, cx=41, cy=25, distance=34, scale=0.46, width=60, height=54)
    f.text(9, 8, "nahoru", size=3.4, color=ACCENT)
    return f.svg()


def m1_back():
    f = step_fig(3, (0, 2, 4, 5), az=180 + 32, cx=37, cy=24, distance=34, scale=0.46, width=60, height=54)
    f.text(10, 8, "nahoru", size=3.4, color=ACCENT)
    return f.svg()


def roll_away(v):
    """Tips the cube away from the viewer: front face up, bottom face to the front."""
    return (v[0], v[2], -v[1])


def m1_bottom():
    f = step_fig(1, (0, 2, 3, 4, 5), transform=roll_away, cx=38, cy=22, distance=30, scale=0.44, width=60, height=56, corner=0)
    f.text(35, 53.5, "dolů", size=3.4, color=ACCENT)
    f.leader(f.p((6, HALF, -10)), (53, 5), 2)
    f.text(3, 8, "překlopeno", size=3.2, anchor="start", weight=500)
    f.text(3, 12, "od sebe", size=3.2, anchor="start", weight=500)
    return f.svg()


def m1_mistakes():
    f = Fig(180, 46)
    y, s = 5, 26
    # correct
    f.add(f'<rect x="8" y="{y}" width="{s}" height="{s}" fill="{BLANK[1]}" stroke="{INK}" stroke-width="0.4"/>')
    flat_tag(f, 8, y, s, 2, stroke="#bbb")
    tick_mark(f, 38, y + 4)
    f.text(21, 38, "rovně, přesně na stěně", size=3.6)
    f.text(21, 42.5, "(tolerance asi 1 mm)", size=3.2, weight=400)
    # crooked / over the edge
    x = 53
    f.add(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{BLANK[1]}" stroke="{INK}" stroke-width="0.4"/>')
    f.add(f'<g transform="rotate(11 {x + s / 2} {y + s / 2}) translate(3 1)">')
    flat_tag(f, x, y, s, 2, stroke="#bbb")
    f.add("</g>")
    cross_mark(f, x + s + 7, y + 3)
    f.text(x + s / 2 + 1, 38, "křivě nebo přes hranu", size=3.6)
    # glossy tape
    x = 98
    flat_tag(f, x, y, s, 2, stroke=INK)
    f.add(f'<g transform="rotate(-32 {x + s / 2} {y + s / 2})"><rect x="{x - 7}" y="{y + 8}" width="{s + 14}" height="10" '
          'fill="#dff1ff" fill-opacity="0.82" stroke="#7fb3d5" stroke-width="0.3"/>'
          f'<rect x="{x - 5}" y="{y + 10}" width="{s + 10}" height="1.6" fill="#fff"/></g>')
    cross_mark(f, x + s + 4, y + 3)
    f.text(x + s / 2, 38, "lesklá lepicí páska", size=3.6)
    f.text(x + s / 2, 42.5, "(odlesky ruší kameru)", size=3.2, weight=400)
    # bubbles
    x = 143
    flat_tag(f, x, y, s, 2, stroke=INK)
    for bx, by, r in ((9, 9, 4.2), (17, 17, 3.2), (20, 7, 2.2)):
        f.add(f'<ellipse cx="{x + bx}" cy="{y + by}" rx="{r}" ry="{r * 0.8}" fill="#ffffffb0" stroke="#666" stroke-width="0.4"/>')
        f.add(f'<path d="M{x + bx - r * 0.5},{y + by - r * 0.2} q{r * 0.2},{-r * 0.4} {r * 0.6},{-r * 0.35}" fill="none" stroke="#fff" stroke-width="0.7"/>')
    cross_mark(f, x + s + 4, y + 3)
    f.text(x + s / 2, 38, "bubliny a záhyby", size=3.6)
    return f.svg()


# ---------------------------------------------------------------- manual 2: cardboard cube + wrap

T = 3.0  # board thickness in the drawings
I = HALF - T


def board(fig, name, offset=(0, 0, 0)):
    """One cardboard panel in its place in the cube, moved by offset."""
    boxes = {
        "bottom": ((-HALF, -HALF, -HALF), (HALF, -I, HALF), 1),
        "top": ((-HALF, I, -HALF), (HALF, HALF, HALF), 1),
        "front": ((-HALF, -I, I), (HALF, I, HALF), 2),
        "back": ((-HALF, -I, -HALF), (HALF, I, -I), 2),
        "left": ((-HALF, -I, -I), (-I, I, I), 0),
        "right": ((I, -I, -I), (HALF, I, I), 0),
    }
    lo, hi, axis = boxes[name]
    fig.box(add(lo, offset), add(hi, offset), cut=axis)


def m2_exploded():
    f = Fig(88, 76, az=32, el=24, scale=0.44, cx=44, cy=38)
    k = 26
    for name, off in (("bottom", (0, -k, 0)), ("back", (0, 0, -k - 6)), ("left", (-k - 4, 0, 0)),
                      ("right", (k + 4, 0, 0)), ("front", (0, 0, k + 6)), ("top", (0, k, 0))):
        board(f, name, off)
    for v, s in (((0, HALF + k, 0), "A"), ((-4, 0, HALF + k + 6), "B"), ((HALF + k + 4, 0, 0), "C")):
        x, y = f.p(v)
        f.badge(x, y, s, r=4)
    f.leader(f.p((-14, -HALF - k + 2, HALF)), (14, 70), "A")
    f.leader(f.p((8, I, -HALF - k - 4)), (80, 8), "B")
    f.leader(f.p((-HALF - k - 4, 10, -8)), (8, 18), "C")
    return f.svg()


def m2_cut_panels():
    f = Fig()
    f.add(f'<rect x="4" y="7" width="80" height="47" fill="{BOARD[0]}" stroke="{INK}" stroke-width="0.4"/>')
    for i in range(15):  # flutes
        f.line2((7 + i * 5.2, 7.3), (7 + i * 5.2, 53.7), stroke="#c9a572", width=0.5)
    k = 0.4
    xs = [9, 33, 57]
    for (letter, _, w, h), x in zip(panel_sizes(50, 3), xs):
        for row in range(2):
            y = 10 + row * 22.5
            f.add(f'<rect x="{x}" y="{y}" width="{w * k}" height="{h * k}" fill="#fffdf8" stroke="{INK}" stroke-width="0.35"/>')
            f.text(x + w * k / 2, y + h * k / 2 + 1, letter, size=6)
            f.text(x + w * k / 2, y + h * k / 2 + 5.4, f"{w:g} × {h:g}", size=2.7, weight=500)
            if letter != "A":
                f.arrow2((x + w * k - 2, y + h * k / 2), (x + w * k - 2, y + 1.5), color="#555", width=0.4)
                f.arrow2((x + w * k - 2, y + h * k / 2), (x + w * k - 2, y + h * k - 1.5), color="#555", width=0.4)
    f.knife(77, 33, angle=-52, size=0.9)
    f.line2((77, 10), (77, 33), stroke=ACCENT, width=0.5, dash="1.4 1")
    return f.svg()


def m2_base_front():
    f = Fig(az=32, el=26, scale=0.5, cx=44, cy=31)
    board(f, "bottom")
    # glue line
    f.line3((-HALF + 2, -I, HALF - T / 2), (HALF - 2, -I, HALF - T / 2), stroke="#3b82f6", width=1.1)
    f.line3((-HALF + 2, -I, -HALF + T / 2), (HALF - 2, -I, -HALF + T / 2), stroke="#3b82f6", width=1.1)
    board(f, "back", (0, 14, 0))
    f.arrow3((-HALF - 6, 8, -HALF), (-HALF - 6, -I + 2, -HALF))
    x, y = f.p((0, 14, -I))
    f.badge(x, y, "B", r=4)
    x, y = f.p((0, -I, 4))
    f.badge(x, y, "A", r=4)
    a = f.p((8, -I, HALF - T / 2))
    f.line2(a, (70, 54), stroke="#3b82f6", width=0.35)
    f.text(71, 55, "lepidlo", size=3.4, anchor="start", color="#2563eb")
    return f.svg()


def m2_sides():
    f = Fig(az=32, el=30, scale=0.56, cx=44, cy=30)
    board(f, "bottom")
    board(f, "back")
    board(f, "left", (0, 12, 0))
    board(f, "right", (0, 12, 0))
    for v in ((-HALF + T / 2, 12, 0), (HALF, 12, 0)):
        x, y = f.p(v)
        f.badge(x, y, "C", r=3.6)
    f.arrow3((-HALF - 8, 24, HALF - 10), (-HALF - 8, 0, HALF - 10))
    f.arrow3((HALF + 8, 24, -HALF), (HALF + 8, 0, -HALF))
    return f.svg()


def m2_second_b():
    f = Fig(az=32, el=30, scale=0.54, cx=50, cy=28)
    for n in ("bottom", "back", "left", "right"):
        board(f, n)
    board(f, "front", (0, 0, 26))
    x, y = f.p((0, 0, HALF + 26))
    f.badge(x, y, "B", r=4)
    f.arrow3((HALF + 5, -HALF, HALF + 30), (HALF + 5, -HALF, HALF + 4))
    return f.svg()


def crumpled(fig, cx, cy, blobs):
    """Balls of crumpled paper: (dx, dy, radius) around (cx, cy)."""
    for dx, dy, r in blobs:
        pts = []
        for i in range(9):
            rr = r * (0.82 + 0.25 * ((i * 7 + int(r * 10)) % 5) / 4)
            pts.append((cx + dx + rr * math.cos(i * 0.698), cy + dy + rr * 0.72 * math.sin(i * 0.698)))
        fig.poly2(pts, fill="#fbfaf6", stroke="#777", width=0.3)
        fig.line2((cx + dx - r * 0.4, cy + dy - r * 0.2), (cx + dx + r * 0.3, cy + dy + r * 0.1), stroke="#aaa", width=0.3)
        fig.line2((cx + dx, cy + dy - r * 0.4), (cx + dx + r * 0.1, cy + dy + r * 0.3), stroke="#aaa", width=0.3)


def m2_fill():
    f = Fig(az=32, el=38, scale=0.56, cx=44, cy=31)
    for n in ("bottom", "back", "left", "right"):
        board(f, n)
    # crumpled paper inside, clipped by the front wall drawn afterwards
    cx, cy = f.p((0, 12, 0))
    crumpled(f, cx, cy, [(-9, 2, 6), (6.5, 0.5, 6), (-0.5, -4, 5.5), (-1, 5, 6.5)])
    board(f, "front")
    return f.svg()


def m2_lid():
    f = Fig(az=32, el=26, scale=0.52, cx=44, cy=36)
    for n in ("bottom", "back", "left", "right", "front"):
        board(f, n)
    board(f, "top", (0, 18, 0))
    x, y = f.p((0, HALF + 18, 0))
    f.badge(x, y, "A", r=4)
    f.arrow3((-HALF - 7, 34, HALF), (-HALF - 7, 12, HALF))
    f.arrow3((HALF + 7, 34, -HALF), (HALF + 7, 12, -HALF))
    return f.svg()


def m2_measure(card=False):
    f = Fig(az=32, el=26, scale=0.62, cx=44, cy=28)
    if card:
        f.net(fold_net(90, 90, 90, 90, 90), {(a, s): 90 for a, s, _ in TABS}, cube_at=(0, 0, 0), card=True)
    else:
        for n in ("bottom", "back", "left", "right", "front", "top"):
            board(f, n)
    d = 7
    for a, b, off, lab in (
            ((-HALF, -HALF, HALF), (HALF, -HALF, HALF), (0, -d, 0), (0, 5.2)),
            ((HALF, -HALF, HALF), (HALF, -HALF, -HALF), (0, -d, 0), (3, 5)),
            ((-HALF, -HALF, HALF), (-HALF, HALF, HALF), (-d, 0, 0), (-8, 1.2))):
        p, q = f.p(add(a, off)), f.p(add(b, off))
        m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        f.arrow2(m, p, width=0.6)
        f.arrow2(m, q, width=0.6)
        f.text(m[0] + lab[0], m[1] + lab[1], "50 mm", size=3.6, color=ACCENT)
    return f.svg()


def m2_cut_wrap():
    f = Fig(88, 64)
    at = flat_net(f, 44, 5, 0.262)
    x, y = at([(25, 45)])[0]
    f.scissors(x + 5.8, y - 4.6, angle=135, size=0.9, color=ACCENT)
    return f.svg()


TABLE = ((-0.34, 0.62, -0.66), (0, 0, -1))  # camera: wrap lies printed side down, short arm towards us


def m2_fold():
    f = Fig(88, 64, az=30, el=8, scale=0.37, cx=42, cy=25)
    fr = fold_net(40, 30, 35, 42, 42)
    f.net(fr, {(a, s): 45 for a, s, _ in TABS})
    return f.svg()


GLUE = "#8db8f7"


def m2_place(puzzle=False):
    f = Fig(88, 64, scale=0.34, cx=44, cy=34, camera=TABLE)
    f.net(fold_net(), cube_at=None)
    hz = -42
    c = (0, 0, hz)
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.line3((sx * HALF, sy * HALF, HALF), (sx * HALF, sy * HALF, hz + HALF), stroke="#9aa0a6", width=0.3, dash="1.2 1.2")
    if puzzle:
        f.puzzle(offset=c)
    else:
        f.poly3([(-HALF, -HALF, HALF), (HALF, -HALF, HALF), (HALF, HALF, HALF), (-HALF, HALF, HALF)],
                fill="#3b82f633", stroke="#3b82f6", width=0.5)
        f.cube(offset=c, palette=BOARD_TURNED)
    f.arrow3((HALF + 8, HALF, hz + 8), (HALF + 8, HALF, HALF - 3))
    f.text(82, 62, "krátké rameno k vám", size=3.2, weight=500, anchor="end")
    return f.svg()


BOARD_TURNED = (BOARD[1], BOARD[0], BOARD[2])  # cube lies on its front face: its back is lit as the top


def m2_wrap_around(puzzle=False):
    f = Fig(88, 64, scale=0.44, cx=43, cy=33, camera=TABLE) if puzzle else Fig(60, 56, scale=0.36, cx=29, cy=29, camera=TABLE)
    tabs = {(1, "L"): 90, (1, "R"): 90, (3, "L"): 90, (3, "R"): 90, (3, "B"): 50}
    f.net(fold_net(0, 90, 90, 0, 0), tabs, cube_at=(0, 0, 0), cube_palette=BOARD_TURNED, puzzle=puzzle)
    # arrow over the cube: up behind it and forward across the top
    pts = [f.p(v) for v in ((-HALF - 14, -HALF - 12, 14), (-HALF - 14, -HALF - 12, -HALF - 20), (-HALF - 14, HALF - 6, -HALF - 12))]
    f.add(f'<path d="M{pts[0][0]:.2f},{pts[0][1]:.2f} Q{pts[1][0]:.2f},{pts[1][1]:.2f} '
          f'{(pts[1][0] + pts[2][0]) / 2:.2f},{(pts[1][1] + pts[2][1]) / 2:.2f}" fill="none" stroke="{ACCENT}" stroke-width="1.1" '
          'stroke-linecap="round"/>')
    f.arrow2(((pts[1][0] + pts[2][0]) / 2, (pts[1][1] + pts[2][1]) / 2), pts[2])
    f.leader(f.p((16, -10, -HALF)), (f.cx + 21, 6), 3)
    f.line2(f.p((8, -HALF, -8)), (f.cx + 8, 6), stroke="#868e96", width=0.35, dash="1 1")
    f.badge(f.cx + 8, 6, 1, r=3.4, fill="#868e96")
    return f.svg()


def m2_top(puzzle=False):
    f = Fig(88, 64, scale=0.44, cx=43, cy=30, camera=TABLE) if puzzle else Fig(60, 56, scale=0.36, cx=29, cy=27, camera=TABLE)
    tabs = {(a, s): 90 for a, s, _ in TABS}
    tabs[(0, "L")] = tabs[(0, "R")] = 35
    fr = fold_net(18, 90, 90, 0, 0)
    f.net(fr, tabs, cube_at=(0, 0, 0), cube_palette=BOARD_TURNED, puzzle=puzzle,
          tab_fills={(3, "B"): GLUE} if puzzle else None)
    f.arrow2(f.p(fr[0].at(HALF + 14, HALF)), f.p((HALF + 12, HALF + 6, -HALF + 6)), bend=0.3)
    x, y = f.p(fr[0].center)
    f.badge(x, y, 0, r=3.4)
    return f.svg()


def m2_sides_close(puzzle=False):
    f = Fig(88, 64, scale=0.46, cx=44, cy=31, camera=TABLE) if puzzle else Fig(60, 56, scale=0.4, cx=30, cy=29, camera=TABLE)
    fr = fold_net(90, 90, 90, 22, 22)
    f.net(fr, {(a, s): 90 for a, s, _ in TABS}, cube_at=(0, 0, 0), cube_palette=BOARD_TURNED, puzzle=puzzle,
          tab_fills={(a, s): GLUE for a, s, _ in TABS if s in "LR"} if puzzle else None)
    for face, side in ((4, -1), (5, 1)):
        x, y = f.p(fr[face].at(side * 12, -10 * side - 4))
        f.badge(x, y, face, r=3.2)
    f.arrow2(f.p(fr[4].at(-HALF, HALF + 4)), f.p((-HALF - 4, HALF, -HALF + 8)), bend=0.25)
    f.arrow2(f.p(fr[5].at(HALF + 4, -HALF)), f.p((HALF + 8, -HALF, -HALF - 8)), bend=-0.25)
    return f.svg()


# ---------------------------------------------------------------- one-piece card cube

def m3_cut():
    f = Fig(88, 64)
    f.add(f'<rect x="10" y="2" width="68" height="60" fill="{BOARD[0]}" stroke="{INK}" stroke-width="0.35"/>')
    k = 0.255

    def at(points):
        return [(44 + x * k, 5 + y * k) for x, y in points]

    f.poly2(at(outline(50)), fill="#fff", width=0.45)
    for face, side, _ in TABS:
        f.poly2(at(tab_polygon(face, side, 50)), fill="#e9e7e3", width=0.25)
    for face, (_, _, down) in NET.items():
        left, top = face_corners(face, 50)["TL"]
        cx, cy = at([(left + 25, top + 25)])[0]
        f.text(cx, cy + 1.6, face, size=5, color="#6b7280",
               extra=f'transform="rotate(180 {cx:.2f} {cy:.2f})"' if down else "")
    for face, side in FOLDS:
        a, b = at(side_points(face, side, 50))
        f.line2(a, b, stroke="#777", width=0.35, dash="1 0.8")
    x, y = at([(33, 88)])[0]
    f.scissors(x + 11, y + 8, angle=-150, size=0.95, color=ACCENT)
    return f.svg()


def m3_fold():
    f = Fig(88, 64, az=30, el=8, scale=0.37, cx=42, cy=25)
    f.net(fold_net(40, 30, 35, 42, 42), {(a, s): 45 for a, s, _ in TABS}, card=True)
    return f.svg()


ALL_IN = {(a, s): 90 for a, s, _ in TABS}


def m3_ring():
    f = Fig(88, 64, az=140, el=28, scale=0.42, cx=47, cy=43)
    f.net(fold_net(14, 90, 90, 8, 8), ALL_IN, card=True, tab_fills={(3, "B"): GLUE})
    fr = fold_net(14)[0]
    x, y = f.p(fr.center)
    f.badge(x, y, 0, r=3.6)
    f.arrow2(f.p(fr.at(-HALF - 4, 18)), f.p((-HALF - 2, HALF + 4, -HALF + 4)), bend=0.3)
    return f.svg()


def m3_first_side():
    f = Fig(88, 64, az=140, el=26, scale=0.48, cx=56, cy=32)
    f.net(fold_net(90, 90, 90, 90, 4), ALL_IN, card=True, tab_fills={(a, s): GLUE for a, s in ((0, "R"), (1, "R"), (3, "R"))})
    fr = fold_net(90, 90, 90, 0, 4)[5]
    x, y = f.p(fr.center)
    f.badge(x, y, 5, r=3.6)
    f.arrow2(f.p(fr.at(HALF - 6, -HALF - 5)), f.p((HALF + 8, -HALF - 5, -HALF + 8)), bend=-0.25)
    return f.svg()


def m3_fill():
    f = Fig(88, 64, az=-140, el=26, scale=0.48, cx=32, cy=32)
    frames = fold_net(90, 90, 90, 4, 90)
    f.net(frames, ALL_IN, card=True)
    cx, cy = f.p((-HALF + 3, 0, 0))
    crumpled(f, cx, cy, [(0, -5, 5.2), (-4, 0.5, 5), (4, 1, 5.2), (-3, 6, 4.6), (2, 7.5, 4.8), (0.5, 2, 4.4)])
    for face in (1, 3, 0):  # the near tabs hold the paper in
        pts, _ = tab_points(frames[face], "L", 90)
        f.poly3(pts, fill=GLUE, width=0.3)
    f.poly3(frames[3].corners(), fill="none", width=0.35)
    fr = frames[4]
    x, y = f.p(fr.center)
    f.badge(x, y, 4, r=3.6)
    f.arrow2(f.p(fr.at(-HALF + 6, -HALF - 5)), f.p((-HALF - 8, -HALF - 5, -HALF + 8)), bend=0.25)
    return f.svg()


# ---------------------------------------------------------------- Rubik's cube sleeve

def m4_cube():
    """The puzzle cube and the measure of its side."""
    f = Fig(88, 64, az=32, el=26, scale=0.56, cx=48, cy=29)
    f.puzzle()
    p, q = f.p((-HALF - 7, -HALF, HALF)), f.p((-HALF - 7, HALF, HALF))
    m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    f.arrow2(m, p, width=0.6)
    f.arrow2(m, q, width=0.6)
    f.text(m[0] - 9, m[1] + 1.2, "55 mm", size=3.8, color=ACCENT)
    return f.svg()


# ---------------------------------------------------------------- pages

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font-family: 'Segoe UI', Arial, sans-serif; color: #1b1b1b; font-size: 10.4pt; line-height: 1.34; }
.page { width: 210mm; height: 297mm; padding: 11mm 12mm 9mm; page-break-after: always; position: relative;
        display: flex; flex-direction: column; gap: 4mm; overflow: hidden; }
.page:last-child { page-break-after: auto; }
header { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 0.6mm solid #1b1b1b; padding-bottom: 1.6mm; }
h1 { font-size: 19pt; margin: 0; letter-spacing: -0.2pt; }
header span { font-size: 9.5pt; color: #555; }
h2 { font-size: 12.5pt; margin: 0; }
.need { background: #f4f3f0; border-radius: 2mm; padding: 2.6mm 4mm; }
.need p { margin: 0; }
.need b { margin-right: 1mm; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; flex: 1; min-height: 0; grid-auto-rows: 1fr; }
.grid.three { grid-template-columns: 1fr 1fr 1fr; flex: 0 0 86mm; }
.three h2 { font-size: 11.5pt; } .three .step { font-size: 9.8pt; }
.step { border: 0.3mm solid #c9c9c9; border-radius: 2mm; padding: 2.4mm 3mm 2.4mm; display: flex; flex-direction: column; min-height: 0; }
.step .head { display: flex; gap: 2.4mm; align-items: center; }
.num { flex: none; width: 7.4mm; height: 7.4mm; border-radius: 50%; background: #1b1b1b; color: #fff; font-weight: 700;
       font-size: 12pt; display: flex; align-items: center; justify-content: center; }
.step .pic { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; margin: 1mm 0; }
.step .pic svg { width: 100%; height: 100%; }
.step p { margin: 0; }
.wide svg { width: 100%; display: block; }
.box { border: 0.3mm solid #c9c9c9; border-radius: 2mm; padding: 2.6mm 4mm; }
.box p { margin: 0.6mm 0 0; }
.caption { display: grid; grid-template-columns: 1fr 1fr; text-align: center; font-size: 9.4pt; }
.accent { color: #d9480f; font-weight: 600; }
table { border-collapse: collapse; font-size: 9.6pt; width: 100%; }
td, th { border: 0.25mm solid #bbb; padding: 0.9mm 2mm; text-align: center; }
th { background: #f4f3f0; font-weight: 600; }
.split { display: grid; grid-template-columns: 84mm 1fr; gap: 5mm; align-items: center; }
footer { font-size: 8.4pt; color: #666; display: flex; justify-content: space-between; margin-top: auto; }
svg text { font-family: 'Segoe UI', Arial, sans-serif; }
ul { margin: 1mm 0 0; padding-left: 5mm; } li { margin: 0.4mm 0; }
"""


def step(n, title, pic, text):
    return (f'<div class="step"><div class="head"><div class="num">{n}</div><h2>{title}</h2></div>'
            f'<div class="pic">{pic}</div><p>{text}</p></div>')


def page(title, sub, body, foot):
    return (f'<section class="page"><header><h1>{title}</h1><span>{sub}</span></header>{body}'
            f'<footer><span>Cube Arc – fyzická kostka</span><span>{foot}</span></footer></section>')


def html(title, pages):
    return (f'<!doctype html><html lang="cs"><head><meta charset="utf-8"><title>{title}</title><style>{CSS}</style></head>'
            f'<body>{"".join(pages)}</body></html>')


def manual_markers():
    t, s = "Nalepení markerů na kostku", "arch cube_markers_50mm.pdf · kostka 50 mm"
    p1 = ('<div class="need"><p><b>Potřebujete:</b> vytištěný arch, kostku o hraně 50 mm, pravítko, nůžky (nebo nůž a kovové pravítko), '
          'tužku, lepicí tyčinku nebo disperzní lepidlo. Povrch kostky musí být čistý a suchý.</p></div>'
          '<div class="grid">'
          + step(1, "Zkontrolujte tisk", m1_check_print(),
                 "Měřítko na archu musí měřit přesně <b>100 mm</b>. Pokud ne, vytiskněte arch znovu ve velikosti 100 % "
                 "(bez „přizpůsobit stránce“).")
          + step(2, "Označte rub a vystřihněte", m1_cut(),
                 "Popisek pod markerem odstřihnete, proto si <b>nejdřív</b> na rub napište číslo a šipku. "
                 "Pak stříhejte po šedé čáře: čtverec 50 × 50 mm.")
          + step(3, "Očíslujte kostku", m1_number_cube(),
                 "Tužkou napište na stěny čísla: <b>0</b> nahoře, <b>1</b> dole, <b>2</b> vpředu (k vám), "
                 "<b>3</b> vzadu, <b>4</b> vlevo, <b>5</b> vpravo.")
          + step(4, "ID 0 na horní stěnu", m1_top(),
                 'Šipka na markeru míří <span class="accent">od vás, k zadní stěně</span>.')
          + step(5, "ID 2 na přední stěnu", m1_front(),
                 'Šipka míří <span class="accent">nahoru</span>. Přitlačte od středu k okrajům.')
          + step(6, "ID 5 na pravou stěnu", m1_right(),
                 'Šipka míří <span class="accent">nahoru</span>. Kostka pořád stojí stěnou 0 nahoru.')
          + '</div>')
    p2 = ('<div class="grid three">'
          + step(7, "ID 4 na levou stěnu", m1_left(), 'Šipka míří <span class="accent">nahoru</span>.')
          + step(8, "ID 3 na zadní stěnu", m1_back(),
                 'Otočte kostku na stole o půl otáčky (stěna 0 zůstává nahoře). Šipka míří <span class="accent">nahoru</span>.')
          + step(9, "ID 1 na spodní stěnu", m1_bottom(),
                 'Natočte ID 2 zpět k sobě a kostku překlopte <b>od sebe</b>, takže ID 2 je nahoře. Šipka míří '
                 '<span class="accent">dolů</span>, k ID 3 na stole.')
          + '</div>'
          '<div class="box"><h2>Pravidlo pro kontrolu</h2><ul>'
          '<li>Na stěnách kolem dokola (2, 5, 3, 4) míří šipky <b>nahoru k ID 0</b>.</li>'
          '<li>Na horní a spodní stěně (0 a 1) míří šipky <b>k ID 3</b>.</li>'
          '<li>Při pohledu na ID 2 je ID 4 <b>vlevo</b> a ID 5 <b>vpravo</b>.</li></ul></div>'
          '<div class="box"><h2>Hotová kostka: porovnejte vzory s obrázkem</h2>'
          f'<div class="wide">{finished_views()}</div>'
          '<p class="caption">'
          '<span>pohled zepředu a shora</span><span>kostka vzhůru nohama: spodní a zadní stěna</span></p></div>'
          f'<div class="box"><h2>Na co si dát pozor</h2><div class="wide">{m1_mistakes()}</div></div>')
    return html(t, [page(t, s, p1, "strana 1 / 2"), page(t, s, p2, "strana 2 / 2")])


def manual_cardboard():
    t, s = "Kostka z kartonu s obalem", "arch cube_wrap_50mm.pdf · kostka 50 mm"
    rows = "".join(
        f"<tr><td>{str(b).replace('.', ',')} mm</td><td>50 × 50</td><td>50 × {50 - 2 * b:g}</td><td>{50 - 2 * b:g} × {50 - 2 * b:g}</td></tr>"
        for b in (1.5, 2, 3, 4, 5))
    p1 = ('<div class="need"><p><b>Potřebujete:</b> lepenku z krabice (nejlépe 3 mm), arch cube_wrap_50mm.pdf vytištěný ve 100 % na matný papír, '
          'kovové pravítko, odlamovací nůž a podložku, nůžky, disperzní lepidlo (Herkules) nebo tavnou pistoli, lepicí tyčinku, starý papír na výplň.</p></div>'
          f'<div class="box split"><div class="wide">{m2_exploded()}</div><div><h2>Tři tvary, každý dvakrát</h2>'
          '<p style="margin-bottom:2mm"><b>A</b> horní a spodní, <b>B</b> přední a zadní, <b>C</b> levá a pravá stěna. '
          'Rozměry závisí na tloušťce lepenky, změřte ji:</p>'
          f'<table><tr><th>lepenka</th><th>A</th><th>B</th><th>C</th></tr>{rows}</table>'
          '<p style="margin-top:2mm">Šablona na straně 2 archu je pro 3 mm. Kostka smí být o 0,5 mm menší, <b>ne větší</b>, jinak se obal nespojí. '
          'Máte jen tenký karton? Složte kostku <b>z jednoho kusu, viz strana 4</b>.</p></div></div>'
          '<div class="grid">'
          + step(1, "Vyřežte díly", m2_cut_panels(),
                 "Přilepte šablonu na lepenku nebo díly narýsujte. U B a C vedou vlny ve směru šipky. "
                 "Řežte nožem podél pravítka, kolmo a na víc tahů.")
          + step(2, "A a první B", m2_base_front(),
                 "Naneste lepidlo na okraj spodního dílu A (modře) a postavte na něj B. Hrany musí lícovat.")
          + step(3, "Oba díly C", m2_sides(),
                 "Naneste lepidlo na spodní i svislé hrany a postavte C na levý a pravý okraj, opřené o B. Zvenku lícují s dílem A.")
          + step(4, "Druhý B", m2_second_b(),
                 "Uzavřete krabičku druhým dílem B. Zkontrolujte pravé úhly a nechte zaschnout.")
          + '</div>')
    p2 = ('<div class="grid">'
          + step(5, "Vyplňte papírem", m2_fill(),
                 "Nacpěte dovnitř zmačkaný papír, aby stěny při uchopení nepružily. Nesmí je vyboulit.")
          + step(6, "Zavřete víkem A", m2_lid(),
                 "Naneste lepidlo na horní hrany, přiložte druhý A a zatižte knihou. Disperzní lepidlo nechte schnout aspoň hodinu.")
          + step(7, "Přeměřte", m2_measure(),
                 "Ve všech třech směrech má být 49,5–50 mm. Přesahy zabruste smirkovým papírem, prohlubně zakryjte papírem.")
          + step(8, "Vystřihněte obal", m2_cut_wrap(),
                 "Měřítko na archu musí měřit 100 mm. Stříhejte po plné čáře <b>i s chlopněmi</b>, nic neoddělujte.")
          + step(9, "Ohněte všechny čárkované čáry", m2_fold(),
                 "Přejeďte je podél pravítka tupou hranou (zavřená propiska) a ohněte dozadu, potisk zůstává <b>vně</b>.")
          + step(10, "Kostku na střed obalu", m2_place(),
                 "Obal leží potiskem dolů, <b>krátké rameno míří k vám</b>. Natřete lepicí tyčinkou vyznačený čtverec "
                 "(rub ID 2) a postavte na něj kostku přesně mezi ohyby.")
          + '</div>')
    p3 = ('<div class="grid three" style="flex-basis:104mm">'
          + step(11, "Dlouhé rameno: 1 a 3", m2_wrap_around(),
                 "Natřete rub ID 1 a 3 a přetáhněte rameno zezadu přes kostku. Chlopně po stranách a na konci přilepte na kostku.")
          + step(12, "Krátké rameno: 0", m2_top(),
                 "Natřete rub ID 0 a zvedněte ho na stěnu k vám, přes chlopeň ID 3. Jeho dvě chlopně přilepte na boky.")
          + step(13, "Boky: 4 a 5", m2_sides_close(),
                 "Nakonec přilepte oba boky přes chlopně. Přitlačte od středu k okrajům, aby nevznikly bubliny.")
          + '</div>'
          '<div class="box"><h2>Hotovo: porovnejte vzory s obrázkem</h2>'
          f'<div class="wide">{finished_views(palette=BOARD)}</div>'
          '<p class="caption">'
          '<span>pohled zepředu a shora</span><span>kostka vzhůru nohama: spodní a zadní stěna</span></p></div>'
          '<div class="box"><h2>Aby sledování fungovalo</h2><ul>'
          '<li>Markery nepřelepujte páskou ani nelaminujte, odlesky ruší kameru.</li>'
          '<li>V Unity u <b>AprilTagCubeTracker</b>: cubeEdge = 0,050 a tagSize = 0,025 (to jsou výchozí hodnoty).</li>'
          '<li>Kostku držte konečky prstů za hrany nebo rohy. Pomačkané nebo ušpiněné stěny přelepte novým markerem z archu cube_markers_50mm.pdf.</li>'
          '</ul></div>')
    p4 = ('<div class="need"><p><b>Místo kroků 1–7:</b> kostka z jednoho kusu tenkého kartonu do 1 mm (krabice od cereálií, zadní deska bloku). '
          'Šablona je v archu cube_wrap_50mm.pdf: <b>strana 3 pro karton 0,5 mm, strana 4 pro 1 mm.</b> '
          'Vlnitou lepenku takhle neohýbejte, kostka by vyšla větší a obal by se nespojil.</p></div>'
          '<div class="grid">'
          + step("A", "Nalepte šablonu a vystřihněte", m3_cut(),
                 "Přilepte šablonu na karton a stříhejte po plné čáře <b>i s chlopněmi</b>.")
          + step("B", "Narýhujte a ohněte", m3_fold(),
                 "Čárkované čáry přejeďte podél pravítka tupou hranou (zavřená propiska) a ohněte dozadu, čísla zůstávají <b>vně</b>.")
          + step("C", "Slepte pás dokola", m3_ring(),
                 "Ohněte všechny chlopně dovnitř. Natřete chlopeň u stěny 3 (modře) a přilepte na ni stěnu 0. Podržte minutu.")
          + step("D", "Zavřete bok 5", m3_first_side(),
                 "Natřete tři chlopně a přiklopte bok 5. Položte kostku tímto bokem na stůl a chlopně zevnitř přitlačte.")
          + step("E", "Vyplňte a zavřete bok 4", m3_fill(),
                 "Nacpěte pevně zmačkaný papír, aby stěny nepružily. Natřete poslední tři chlopně a přiklopte bok 4.")
          + step("F", "Přeměřte", m2_measure(card=True),
                 "Ve všech třech směrech má být 49,5–50 mm. Nechte zaschnout a <b>pokračujte krokem 8</b> (obal s markery).")
          + '</div>')
    foot = "strana {} / 4"
    return html(t, [page(t, s, p, foot.format(i)) for i, p in enumerate((p1, p2, p3, p4), start=1)])


def manual_sleeve():
    t, s = "Návlek na Rubikovu kostku", "arch cube_sleeve_55mm.pdf · kostka 55 mm"
    p1 = ('<div class="need"><p><b>Na kostku nepřijde žádné lepidlo.</b> Lepí se jen papír na papír, návlek drží sám a dá se kdykoli sundat. '
          '<b>Potřebujete:</b> arch vytištěný ve 100 % na matný papír, pravítko, nůžky, oboustrannou pásku (nejjistější) nebo lepicí tyčinku.</p></div>'
          '<div class="grid">'
          + step(1, "Srovnejte a změřte kostku", m4_cube(),
                 "Vrstvy musí lícovat. Stěna má měřit 55 mm; návlek je o 0,5 mm větší. Když se liší o víc než 0,5 mm, vytiskněte jinou velikost (viz strana 2).")
          + step(2, "Vystřihněte návlek", m2_cut_wrap(),
                 "Měřítko na archu musí měřit 100 mm. Stříhejte po plné čáře <b>i s chlopněmi</b>.")
          + step(3, "Ohněte a postavte kostku", m2_place(puzzle=True),
                 "Všechny čárkované čáry ohněte dozadu. Obal leží potiskem dolů, krátké rameno k vám. Kostku jen <b>postavte, nelepte</b>.")
          + step(4, "Dlouhé rameno kolem kostky", m2_wrap_around(puzzle=True),
                 "Přetáhněte ID 1 a 3 zezadu přes kostku. Chlopně ohněte kolem hran. Zatím <b>bez lepidla</b>, jen přidržte.")
          + '</div>')
    p2 = ('<div class="grid" style="flex:0 0 96mm">'
          + step(5, "Krátké rameno na chlopeň", m2_top(puzzle=True),
                 "Pásku nebo lepidlo dejte na <b>vnější</b> stranu chlopně ID 3 (modře). Zvedněte ID 0, utáhněte a přitlačte.")
          + step(6, "Zavřete boky", m2_sides_close(puzzle=True),
                 "Totéž na vnější straně bočních chlopní (modře): přiklopte ID 4 a ID 5. Lepidlo <b>ne až k ohybu</b>, aby nevyteklo ke kostce.")
          + '</div>'
          '<div class="box"><h2>Hotovo: porovnejte vzory s obrázkem</h2>'
          f'<div class="wide">{finished_views()}</div>'
          '<p class="caption">'
          '<span>pohled zepředu a shora</span><span>kostka vzhůru nohama: spodní a zadní stěna</span></p></div>'
          '<div class="box"><h2>Dobré vědět</h2><ul>'
          '<li><b>Sundání:</b> podeberte bok 4 nebo 5, případně ho opatrně rozstřihněte nad chlopní.</li>'
          '<li><b>Unity:</b> tagSize zůstává 0,025, takže na zkoušku není třeba nic měnit. Přesněji nastavte u AprilTagCubeTracker cubeEdge = 0,055; '
          'bez toho je střed kostky posunutý asi o 2,5 mm.</li>'
          '<li><b>Jiná velikost:</b> generate_cube_wrap.py --edge-mm 56 --sleeve --cell-mm 5 (hodnota edge-mm = hrana kostky).</li>'
          '<li><b>Držení:</b> konečky prstů za hrany nebo rohy. Návlek zároveň brání otáčení vrstev.</li></ul></div>')
    return html(t, [page(t, s, p1, "strana 1 / 2"), page(t, s, p2, "strana 2 / 2")])


# ---------------------------------------------------------------- HTML -> PDF

def find_browser():
    candidates = [os.environ.get("BROWSER"), shutil.which("chrome"), shutil.which("google-chrome"), shutil.which("chromium"),
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    sys.exit("Chrome or Edge not found; set the BROWSER environment variable to its path.")


def main():
    browser = find_browser()
    for name, doc in (("Navod_lepeni_markeru", manual_markers()), ("Navod_kostka_z_kartonu", manual_cardboard()),
                      ("Navod_rubikova_kostka", manual_sleeve())):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            source = pathlib.Path(tmp) / f"{name}.html"
            source.write_text(doc, encoding="utf-8")
            target = HERE / f"{name}.pdf"
            subprocess.run([browser, "--headless", "--disable-gpu", f"--user-data-dir={tmp}/profile", "--no-first-run",
                            "--no-pdf-header-footer", f"--print-to-pdf={target}", source.as_uri()],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
            print(f"Wrote {target.name}")


if __name__ == "__main__":
    main()
