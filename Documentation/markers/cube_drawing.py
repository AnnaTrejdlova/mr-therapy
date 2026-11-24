"""
Small drawing helper for the illustrated cube manuals (see generate_cube_manuals.py): an orthographic
3D view of the cube, its markers, the foldable wrap and cardboard panels, written as SVG.
Standard library only.

Cube axes used here (right-handed): +X right, +Y up (face 0), +Z towards the viewer (face 2).
In Unity (left-handed) face 2 is at -Z, so this is the same physical cube as CubeFaceLayout.cs.
"""
import math

from generate_cube_markers import TOTAL_WIDTH, cell_size_mm, tag_cells
from generate_cube_wrap import NET, TAB_MM, TABS

EDGE = 50.0
HALF = EDGE / 2
CELL = cell_size_mm(EDGE)

INK = "#1b1b1b"
ACCENT = "#d9480f"
PAPER = ("#ffffff", "#f4f3f0", "#e7e5e0")      # top, front/back, sides
PAPER_BACK = ("#f3ead9", "#ece1cc", "#e2d5bc")
BOARD = ("#dfbe91", "#d1ab79", "#bd9361")
BOARD_CUT = ("#c79f6c", "#b88d5a", "#a67b4a")


# --- vectors ---
def add(*vs):
    return tuple(map(sum, zip(*vs)))


def mul(v, k):
    return tuple(c * k for c in v)


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(v):
    return mul(v, 1 / math.sqrt(dot(v, v)))


# Face -> (outward normal, direction of the tag's top edge); same table as CubeFaceLayout.cs
LAYOUT = {
    0: ((0, 1, 0), (0, 0, -1)),
    1: ((0, -1, 0), (0, 0, -1)),
    2: ((0, 0, 1), (0, 1, 0)),
    3: ((0, 0, -1), (0, 1, 0)),
    4: ((-1, 0, 0), (0, 1, 0)),
    5: ((1, 0, 0), (0, 1, 0)),
}


class Frame:
    """A square face: centre, right, up and outward normal."""

    def __init__(self, center, right, up, normal):
        self.center, self.right, self.up, self.normal = center, right, up, normal

    def at(self, u, v, out=0.0):
        return add(self.center, mul(self.right, u), mul(self.up, v), mul(self.normal, out))

    def corners(self, half=HALF):
        return [self.at(-half, half), self.at(half, half), self.at(half, -half), self.at(-half, -half)]

    def turned(self):
        return Frame(self.center, mul(self.right, -1), mul(self.up, -1), self.normal)

    def moved(self, offset):
        return Frame(add(self.center, offset), self.right, self.up, self.normal)

    def transformed(self, f):
        return Frame(f(self.center), f(self.right), f(self.up), f(self.normal))


def face_frame(face, half=HALF):
    n, up = LAYOUT[face]
    return Frame(mul(n, half), cross(up, n), up, n)


# --- the foldable net ---
def fold_child(parent, side, degrees, half=HALF):
    """Frame of the face hinged on one side of `parent`; 0 degrees = flat, 90 = folded back."""
    out = {"T": parent.up, "B": mul(parent.up, -1), "L": mul(parent.right, -1), "R": parent.right}[side]
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    new_out = add(mul(out, c), mul(parent.normal, -s))
    normal = add(mul(parent.normal, c), mul(out, s))
    center = add(parent.center, mul(out, half), mul(new_out, half))
    right, up = parent.right, parent.up
    if side == "T":
        up = new_out
    elif side == "B":
        up = mul(new_out, -1)
    elif side == "L":
        right = mul(new_out, -1)
    else:
        right = new_out
    return Frame(center, right, up, normal)


def fold_net(a0=0, a1=0, a3=0, a4=0, a5=0):
    """Net frames in net orientation (tags 1 and 3 are printed upside down on them)."""
    f = {2: Frame((0, 0, HALF), (1, 0, 0), (0, 1, 0), (0, 0, 1))}
    f[0] = fold_child(f[2], "T", a0)
    f[1] = fold_child(f[2], "B", a1)
    f[3] = fold_child(f[1], "B", a3)
    f[4] = fold_child(f[2], "L", a4)
    f[5] = fold_child(f[2], "R", a5)
    return f


def tag_frame(net_frame, face):
    return net_frame.turned() if NET[face][2] else net_frame


def tab_points(frame, side, degrees):
    """3D outline of a glue tab folded by `degrees`, and its outward normal."""
    tab = fold_child(frame, side, degrees)
    out = {"T": tab.up, "B": mul(tab.up, -1), "L": mul(tab.right, -1), "R": tab.right}[side]
    along = tab.right if side in "TB" else tab.up
    hinge = add(tab.center, mul(out, -HALF))
    pts = [add(hinge, mul(along, -HALF)), add(hinge, mul(along, -HALF + TAB_MM), mul(out, TAB_MM)),
           add(hinge, mul(along, HALF - TAB_MM), mul(out, TAB_MM)), add(hinge, mul(along, HALF))]
    return pts, tab.normal


# --- figure ---
class Fig:
    """One illustration. 3D points are in cube millimetres, the SVG viewBox is width x height."""

    def __init__(self, width=88, height=58, az=32, el=26, scale=0.62, cx=None, cy=None, camera=None):
        """The view is given by azimuth and elevation, or by camera = (direction to the eye, up)."""
        self.w, self.h = width, height
        if camera is None:
            a, e = math.radians(az), math.radians(el)
            camera = (math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a)), (0, 1, 0)
        self.dir = unit(camera[0])
        self.rgt = unit(cross(camera[1], self.dir))
        self.upv = cross(self.dir, self.rgt)
        self.scale = scale
        self.cx = width / 2 if cx is None else cx
        self.cy = height / 2 if cy is None else cy
        self.out = []

    # 3D -> page
    def p(self, v):
        return (self.cx + dot(v, self.rgt) * self.scale, self.cy - dot(v, self.upv) * self.scale)

    def depth(self, v):
        return dot(v, self.dir)

    def facing(self, normal):
        return dot(normal, self.dir) > 1e-6

    def shade(self, normal, palette):
        x, y, z = (abs(c) for c in normal)
        if y >= x and y >= z:
            return palette[0]
        return palette[1] if z >= x else palette[2]

    # 2D primitives
    def add(self, svg):
        self.out.append(svg)

    def poly2(self, pts, fill="none", stroke=INK, width=0.35, extra=""):
        d = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        self.add(f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" '
                 f'stroke-linejoin="round" {extra}/>')

    def line2(self, a, b, stroke=INK, width=0.35, dash=None):
        dd = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="{stroke}" '
                 f'stroke-width="{width}" stroke-linecap="round"{dd}/>')

    def text(self, x, y, s, size=4.2, anchor="middle", color=INK, weight=600, extra=""):
        self.add(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" fill="{color}" '
                 f'font-weight="{weight}" {extra}>{s}</text>')

    def arrow2(self, a, b, bend=0.0, color=ACCENT, width=1.1):
        """Arrow from a to b; bend moves the middle sideways (fraction of the length)."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        mx, my = (a[0] + b[0]) / 2 - dy * bend, (a[1] + b[1]) / 2 + dx * bend
        tx, ty = b[0] - mx, b[1] - my
        n = math.hypot(tx, ty) or 1
        tx, ty = tx / n, ty / n
        head = 3.0
        ex, ey = b[0] - tx * head * 0.8, b[1] - ty * head * 0.8
        self.add(f'<path d="M{a[0]:.2f},{a[1]:.2f} Q{mx:.2f},{my:.2f} {ex:.2f},{ey:.2f}" fill="none" '
                 f'stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>')
        self.poly2([b, (b[0] - tx * head - ty * head * 0.55, b[1] - ty * head + tx * head * 0.55),
                    (b[0] - tx * head + ty * head * 0.55, b[1] - ty * head - tx * head * 0.55)],
                   fill=color, stroke="none", width=0)

    def badge(self, x, y, s, r=3.6, fill=INK):
        self.add(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{fill}" stroke="#fff" stroke-width="0.5"/>')
        self.text(x, y + r * 0.42, s, size=r * 1.25, color="#fff", weight=700)

    def leader(self, at, to, s, fill=INK):
        self.line2(at, to, stroke="#fff", width=1.3)
        self.line2(at, to, stroke=fill, width=0.45)
        self.add(f'<circle cx="{at[0]:.2f}" cy="{at[1]:.2f}" r="1" fill="{fill}" stroke="#fff" stroke-width="0.4"/>')
        self.badge(to[0], to[1], s, fill=fill)

    # 3D primitives
    def poly3(self, pts, **kw):
        self.poly2([self.p(v) for v in pts], **kw)

    def line3(self, a, b, **kw):
        self.line2(self.p(a), self.p(b), **kw)

    def arrow3(self, a, b, **kw):
        self.arrow2(self.p(a), self.p(b), **kw)

    def tag(self, frame, tag_id, arrow=True):
        """The real marker printed on a face."""
        half = CELL * TOTAL_WIDTH / 2
        d = []
        for row, line in enumerate(tag_cells(tag_id)):
            col = 0
            while col < TOTAL_WIDTH:
                if line[col]:
                    col += 1
                    continue
                start = col
                while col < TOTAL_WIDTH and not line[col]:
                    col += 1
                u0, u1 = -half + start * CELL, -half + col * CELL
                v0, v1 = half - row * CELL, half - (row + 1) * CELL
                pts = [self.p(frame.at(u, v)) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
                d.append("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z")
        self.add(f'<path d="{" ".join(d)}" fill="#111" stroke="#111" stroke-width="0.12"/>')
        if arrow:
            m = (HALF - half) / 2
            self.poly3([frame.at(-1.6, HALF - m - 0.8), frame.at(1.6, HALF - m - 0.8), frame.at(0, HALF - m + 0.8)],
                       fill="#666", stroke="none", width=0)

    def marker(self, frame, tag_id, stroke=INK, width=0.35, palette=PAPER):
        """A paper square with its marker; plain back when seen from behind."""
        if self.facing(frame.normal):
            self.poly3(frame.corners(), fill=self.shade(frame.normal, palette), stroke=stroke, width=width)
            self.tag(frame, tag_id)
        else:
            self.poly3(frame.corners(), fill=self.shade(frame.normal, PAPER_BACK), stroke=stroke, width=width)

    def plane_arrow(self, frame, start=HALF + 2, length=19, color=ACCENT):
        """Arrow lying in the plane of a face, continuing the direction of the tag's top edge."""
        a, b = start, start + length
        pts = [(-2.6, a), (-2.6, b - 9), (-7, b - 9), (0, b), (7, b - 9), (2.6, b - 9), (2.6, a)]
        self.poly3([frame.at(u, v) for u, v in pts], fill=color, stroke="#fff", width=0.3)

    def face_text(self, frame, s, size=20, color=INK, u=0.0, v=0.0, weight=600):
        """Text lying in the plane of a face (affine map of the SVG text)."""
        ox, oy = self.p(frame.at(u, v))
        rx, ry = self.p(frame.at(u + 1, v))
        dx, dy = self.p(frame.at(u, v - 1))
        self.add(f'<g transform="matrix({rx - ox:.4f} {ry - oy:.4f} {dx - ox:.4f} {dy - oy:.4f} {ox:.2f} {oy:.2f})">'
                 f'<text x="0" y="{size * 0.35:.2f}" font-size="{size}" text-anchor="middle" fill="{color}" '
                 f'font-weight="{weight}">{s}</text></g>')

    def box(self, lo, hi, palette=BOARD, stroke=INK, width=0.3, cut=None):
        """Axis-aligned box. `cut` = axis of the board thickness: the other faces get the cut-edge colour."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        quads = [
            ((1, 0, 0), [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], 0),
            ((-1, 0, 0), [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], 0),
            ((0, 1, 0), [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], 1),
            ((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], 1),
            ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], 2),
            ((0, 0, -1), [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], 2),
        ]
        for normal, pts, axis in quads:
            if self.facing(normal):
                pal = BOARD_CUT if cut is not None and axis != cut else palette
                self.poly3(pts, fill=self.shade(normal, pal), stroke=stroke, width=width)

    def cube(self, half=HALF, palette=BOARD, offset=(0, 0, 0)):
        self.box(tuple(c - half for c in offset), tuple(c + half for c in offset), palette)

    def puzzle(self, half=HALF, offset=(0, 0, 0)):
        """A 3 x 3 x 3 puzzle cube."""
        colors = {0: "#ffffff", 1: "#f7c948", 2: "#3f9b57", 3: "#3b6fb6", 4: "#e8833a", 5: "#c8453c"}
        for face in range(6):
            fr = face_frame(face, half).moved(offset)
            if not self.facing(fr.normal):
                continue
            self.poly3(fr.corners(half), fill="#2b2b2b", width=0.3)
            k = half * 2 / 3
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    r = k * 0.42
                    self.poly3([fr.at(i * k - r, j * k + r), fr.at(i * k + r, j * k + r), fr.at(i * k + r, j * k - r),
                                fr.at(i * k - r, j * k - r)], fill=colors[face], stroke="none", width=0)

    def card_face(self, frame, face):
        """Face of the one-piece card cube: paper template outside, bare card inside."""
        if self.facing(frame.normal):
            self.poly3(frame.corners(), fill=self.shade(frame.normal, PAPER), width=0.35)
            self.face_text(frame.turned() if NET[face][2] else frame, face, size=22, color="#6b7280")
        else:
            self.poly3(frame.corners(), fill=self.shade(frame.normal, BOARD), width=0.35)

    def net(self, frames, tab_angles=None, cube_at=None, only=None, cube_palette=BOARD, puzzle=False, card=False,
            tab_fills=None):
        """
        Folded or half-folded wrap, painted back to front. tab_angles: {(face, side): degrees}.
        puzzle: a puzzle cube inside; card: the one-piece card cube instead of the marker wrap;
        tab_fills: {(face, side): colour} for tabs with glue on them.
        """
        tab_angles, tab_fills = tab_angles or {}, tab_fills or {}
        items = []

        def place(pts, normal, kind, data):
            """Queues a piece; pieces already lying on the wrapped cube are drawn right after it, or not at all."""
            depth = self.depth(mul(add(*pts), 0.25))
            if cube_at == (0, 0, 0) and all(abs(c) <= HALF + 0.1 for v in pts for c in v):
                if not self.facing(normal):
                    return
                depth = max(depth, 0.01 if kind == "tab" else 0.02)
            items.append((depth, kind, data))

        for face, fr in frames.items():
            if only is None or face in only:
                place(fr.corners(), fr.normal, "face", face)
        for face, side, over in TABS:
            if only is None or face in only:
                pts, normal = tab_points(frames[face], side, tab_angles.get((face, side), 0))
                cover = frames[over]
                if dot(normal, cover.normal) > 0.999 and all(abs(dot(sub(v, cover.center), cover.normal)) < 0.1 for v in pts):
                    if not self.facing(normal):  # seen from inside, the tab lies in front of the face it holds
                        items.append((self.depth(cover.center) + 0.01, "tab", (pts, normal, None)))
                    continue
                place(pts, normal, "tab", (pts, normal, tab_fills.get((face, side))))
        if cube_at is not None:
            items.append((self.depth(cube_at), "cube", None))
        for _, kind, data in sorted(items, key=lambda i: i[0]):
            if kind == "face":
                if card:
                    self.card_face(frames[data], data)
                else:
                    self.marker(tag_frame(frames[data], data), data)
            elif kind == "tab":
                pts, normal, color = data
                if self.facing(normal):
                    fill = color or "#e4e2de"
                else:
                    fill = self.shade(normal, BOARD if card else PAPER_BACK)
                self.poly3(pts, fill=fill, width=0.3)
            elif puzzle:
                self.puzzle(half=HALF - 0.2, offset=cube_at)
            else:
                self.cube(half=HALF - 0.2, offset=cube_at, palette=cube_palette)

    # 2D tools
    def scissors(self, x, y, angle=0, size=1.0, color=INK):
        self.add(f'<g transform="translate({x:.2f} {y:.2f}) rotate({angle}) scale({size})" fill="none" '
                 f'stroke="{color}" stroke-width="0.8" stroke-linecap="round">'
                 '<line x1="-3.4" y1="-1.7" x2="6" y2="1.5"/><line x1="-3.4" y1="1.7" x2="6" y2="-1.5"/>'
                 '<ellipse cx="-5.2" cy="-2.3" rx="2" ry="1.4" transform="rotate(20 -5.2 -2.3)" fill="#fff"/>'
                 '<ellipse cx="-5.2" cy="2.3" rx="2" ry="1.4" transform="rotate(-20 -5.2 2.3)" fill="#fff"/></g>')

    def pencil(self, x, y, angle=-50, size=1.0):
        """Pencil with its tip at (x, y)."""
        self.add(f'<g transform="translate({x:.2f} {y:.2f}) rotate({angle}) scale({size})" stroke="{INK}" '
                 'stroke-width="0.35" stroke-linejoin="round">'
                 '<polygon points="0,0 4,-1.5 4,1.5" fill="#f1d9b0"/><polygon points="0,0 1.4,-0.5 1.4,0.5" fill="#222"/>'
                 '<rect x="4" y="-1.5" width="13" height="3" fill="#f2b632"/>'
                 '<rect x="17" y="-1.5" width="2" height="3" fill="#ccc"/>'
                 '<rect x="19" y="-1.5" width="2" height="3" rx="0.6" fill="#e58a8a"/></g>')

    def knife(self, x, y, angle=-50, size=1.0):
        """Cutter with the blade tip at (x, y)."""
        self.add(f'<g transform="translate({x:.2f} {y:.2f}) rotate({angle}) scale({size})" stroke="{INK}" '
                 'stroke-width="0.35" stroke-linejoin="round">'
                 '<polygon points="0,0 2.2,-2 8,-2 8,0.4" fill="#d7dbe0"/>'
                 '<rect x="8" y="-2.4" width="15" height="3.6" rx="1" fill="#4b5563"/>'
                 '<rect x="11" y="-1.5" width="6" height="1.2" rx="0.5" fill="#9aa3af" stroke="none"/></g>')

    def ruler(self, x, y, length, unit=1.0, numbers=True, height=7):
        """Horizontal ruler; `unit` = drawing units per millimetre, zero at x."""
        self.add(f'<rect x="{x - 1.5:.2f}" y="{y:.2f}" width="{length * unit + 3:.2f}" height="{height}" rx="0.6" '
                 f'fill="#fdf3c7" stroke="{INK}" stroke-width="0.3"/>')
        for mm in range(0, int(length) + 1, 5):
            t = 2.4 if mm % 10 == 0 else 1.4
            self.line2((x + mm * unit, y), (x + mm * unit, y + t), width=0.25)
            if numbers and mm % 20 == 0:
                self.text(x + mm * unit, y + 5.4, mm // 10, size=2.8, weight=500)

    def svg(self):
        return (f'<svg viewBox="0 0 {self.w} {self.h}" xmlns="http://www.w3.org/2000/svg">' +
                "".join(self.out) + "</svg>")
