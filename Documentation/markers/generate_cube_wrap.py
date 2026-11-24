"""
Generates the 1:1 printouts for the cube of the Cube Arc game (A4 PDF):
  page 1  - one-piece marker wrap: all six AprilTags on a net that folds around the cube,
  page 2  - cutting template for the six panels of a cube from thick cardboard,
  page 3+ - cutting template for a cube folded from one piece of thin card, one page per thickness.

Usage:
    python generate_cube_wrap.py                            # cube_wrap_50mm.pdf, 3 mm cardboard, 0.5 and 1 mm card
    python generate_cube_wrap.py --edge-mm 45 --board-mm 4 --card-mm 0.8
    python generate_cube_wrap.py --edge-mm 55 --sleeve --cell-mm 5
        # cube_sleeve_55mm.pdf: wrap only, slightly larger, for a cube that must stay free of glue
        # (Rubik's cube); --cell-mm 5 keeps the tags of the 50 mm cube, so tagSize stays 0.025

Print at 100 % (no "fit to page"). Needs only the Python standard library.
Tags have the same size and orientation as in generate_cube_markers.py and CubeFaceLayout.cs.
"""
import argparse

from generate_cube_markers import (MM, PAGE_H, TOTAL_WIDTH, WIDTH_AT_BORDER, cell_size_mm, pdf_text,
                                   tag_cells, write_pdf)

TAB_MM = 8.0  # depth of the glue tabs (45-degree corners)
SLEEVE_CLEARANCE_MM = 0.5  # how much larger the faces of a glue-free sleeve are than the cube
CARD_CLEARANCE_MM = 0.3  # how much smaller than the wrap the folded card cube is
CARD_TAB_MM = 10.0

# The net seen from outside: tag ID -> (column, row, tag drawn upside down). Face 2 (front) is the
# root, 0 folds up, 4 and 5 fold to the sides, 1 folds down and 3 continues from 1.
NET = {
    0: (0, 0, False),
    2: (0, 1, False),
    4: (-1, 1, False),
    5: (1, 1, False),
    1: (0, 2, True),
    3: (0, 3, True),
}
FACE_NAMES = {0: "HORNÍ", 1: "SPODNÍ", 2: "PŘEDNÍ", 3: "ZADNÍ", 4: "LEVÁ", 5: "PRAVÁ"}

# Glue tabs: (face, side of that face in the net, face that gets glued over the tab)
TABS = [(0, "L", 4), (0, "R", 5), (1, "L", 4), (1, "R", 5), (3, "L", 4), (3, "R", 5), (3, "B", 0)]

# Fold lines between faces: (face, side)
FOLDS = [(2, "T"), (2, "B"), (2, "L"), (2, "R"), (1, "B")]

SIDE_CORNERS = {"T": ("TL", "TR"), "R": ("TR", "BR"), "B": ("BR", "BL"), "L": ("BL", "TL")}
SIDE_OUT = {"T": (0, -1), "R": (1, 0), "B": (0, 1), "L": (-1, 0)}


def face_corners(face, edge):
    """Corners of a face in net millimetres (x right, y down, net centred on x = 0)."""
    col, row, _ = NET[face]
    x, y = (col - 0.5) * edge, row * edge
    return {"TL": (x, y), "TR": (x + edge, y), "BR": (x + edge, y + edge), "BL": (x, y + edge)}


def side_points(face, side, edge):
    c = face_corners(face, edge)
    a, b = SIDE_CORNERS[side]
    return c[a], c[b]


def tab_polygon(face, side, edge, tab=TAB_MM):
    """Trapezoid glue tab on one side of a face; the first and last point lie on the fold."""
    (ax, ay), (bx, by) = side_points(face, side, edge)
    ox, oy = SIDE_OUT[side]
    ux, uy = (bx - ax) / edge, (by - ay) / edge
    return [(ax, ay), (ax + (ox + ux) * tab, ay + (oy + uy) * tab),
            (bx + (ox - ux) * tab, by + (oy - uy) * tab), (bx, by)]


def outline(edge):
    """The cut line around the whole net, clockwise."""
    tabs = {(f, s) for f, s, _ in TABS}
    order = [(0, "T"), (0, "R"), (5, "T"), (5, "R"), (5, "B"), (1, "R"), (3, "R"), (3, "B"), (3, "L"),
             (1, "L"), (4, "B"), (4, "L"), (4, "T"), (0, "L")]
    points = []
    for face, side in order:
        pts = tab_polygon(face, side, edge) if (face, side) in tabs else list(side_points(face, side, edge))
        points += pts if not points or pts[0] != points[-1] else pts[1:]
    return points[:-1] if points[0] == points[-1] else points


class Page:
    """Collects drawing operators; coordinates are millimetres from the top left corner of the page."""

    def __init__(self):
        self.ops = []

    def xy(self, x, y):
        return f"{x * MM:.3f} {PAGE_H - y * MM:.3f}"

    def raw(self, text):
        self.ops.append(text)

    def polygon(self, points, paint):
        path = " l\n".join(self.xy(*p) for p in points[1:])
        self.raw(f"{self.xy(*points[0])} m\n{path} l h {paint}\n")

    def line(self, a, b):
        self.raw(f"{self.xy(*a)} m {self.xy(*b)} l S\n")

    def text(self, x, y, size, text):
        self.raw(pdf_text(x * MM, PAGE_H - y * MM, size, text))

    def text_rotated(self, x, y, size, text, quarter_turns):
        """Text turned by 90 degrees counter-clockwise per quarter turn, roughly centred on (x, y)."""
        cos, sin = [(1, 0), (0, 1), (-1, 0), (0, -1)][quarter_turns % 4]
        half = len(text) * size * 0.24
        down = size * 0.36
        tx = x * MM - cos * half + sin * down
        ty = PAGE_H - y * MM - sin * half - cos * down
        self.raw(f"q {cos} {sin} {-sin} {cos} {tx:.3f} {ty:.3f} cm {pdf_text(0, 0, size, text)}Q\n")

    def scale_bar(self, x, y):
        self.raw(f"0 g {self.xy(x, y)} {100 * MM:.2f} {1.2 * MM:.2f} re f\n")
        for i in range(11):
            self.raw(f"{self.xy(x + i * 10, y)} {0.3 * MM:.2f} {-2.5 * MM:.2f} re f\n")
        self.text(x + 103, y + 1, 9, "100 mm")

    def content(self):
        return "".join(self.ops)


def draw_tag(page, tag_id, x, y, cell, upside_down):
    grid = tag_cells(tag_id)
    n = TOTAL_WIDTH
    page.raw("0 g\n")
    for row in range(n):
        for col in range(n):
            if not grid[row][col]:
                r, c = (n - 1 - row, n - 1 - col) if upside_down else (row, col)
                # tiny overlap avoids hairline gaps between cells in some viewers
                size = cell * MM + 0.05
                page.raw(f"{page.xy(x + c * cell, y + (r + 1) * cell)} {size:.3f} {size:.3f} re f\n")


def metres(mm):
    """Millimetres as a Unity value in metres, with at least three decimals."""
    text = f"{mm / 1000:.4f}"
    return text[:-1] if text.endswith("0") else text


def build_wrap(edge, cell, sleeve=False):
    page = Page()
    page.raw("0 g\n")
    name = "návlek s markery" if sleeve else "obal s markery"
    page.text(15, 14, 13, f"Cube Arc – {name} na kostku {edge:g} mm".replace(".", ",") + " (AprilTag tagStandard41h12)")
    page.text(15, 20, 9, "Tiskněte ve 100 % (bez přizpůsobení stránce) na matný papír. Pravítkem zkontrolujte, že měřítko měří 100 mm:")
    page.scale_bar(15, 26)
    page.text(140, 27, 9, f"cubeEdge = {metres(edge)}   tagSize = {cell * WIDTH_AT_BORDER / 1000:.4f}")
    if sleeve:
        edge += SLEEVE_CLEARANCE_MM

    ox, oy = 105, 37  # net origin on the page

    def at(points):
        return [(ox + x, oy + y) for x, y in points]

    # Glue tabs, lightly shaded
    for face, side, _ in TABS:
        page.raw("0.93 g\n")
        page.polygon(at(tab_polygon(face, side, edge)), "f")

    margin = (edge - cell * TOTAL_WIDTH) / 2
    for face, (_, _, upside_down) in NET.items():
        left, top = face_corners(face, edge)["TL"]
        x0, y0 = ox + left, oy + top
        draw_tag(page, face, x0 + margin, y0 + margin, cell, upside_down)

        # Arrow at the top edge of the tag and face name at its bottom edge, both in the white margin
        page.raw("0.4 g\n")
        sign = -1 if upside_down else 1
        cx, cy = x0 + edge / 2, y0 + edge / 2
        ay = cy - sign * (edge / 2 - margin / 2)
        page.polygon([(cx - 1.6, ay + sign * 0.8), (cx + 1.6, ay + sign * 0.8), (cx, ay - sign * 0.8)], "f")
        ty = cy + sign * (edge / 2 - margin / 2)
        page.text_rotated(cx, ty, min(5.0, margin * 2), f"ID {face} – {FACE_NAMES[face]}", 2 if upside_down else 0)

    for face, side, over in TABS:
        pts = at(tab_polygon(face, side, edge))
        cx, cy = sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4
        page.raw("0.35 g\n")
        page.text_rotated(cx, cy, 8, f"patří pod ID {over}", {"L": 1, "R": 3, "B": 0}[side])

    # Fold lines (dashed) and cut line (solid)
    page.raw("0.55 G 0.4 w [4 2.5] 0 d\n")
    for face, side in FOLDS + [(f, s) for f, s, _ in TABS]:
        page.line(*at(side_points(face, side, edge)))
    page.raw("[] 0 d 0.35 G 0.5 w 1 j\n")
    page.polygon(at(outline(edge)), "S")

    # Legend beside the lower part of the net
    ly = oy + edge * 2 + 16
    lx = ox + edge / 2 + TAB_MM + 8
    page.line((lx, ly), (lx + 12, ly))
    page.raw("0.55 G 0.4 w [4 2.5] 0 d\n")
    page.line((lx, ly + 8), (lx + 12, ly + 8))
    page.raw("[] 0 d 0.93 g\n")
    page.polygon([(lx, ly + 13.5), (lx + 12, ly + 13.5), (lx + 12, ly + 18.5), (lx, ly + 18.5)], "f")
    page.raw("0 g\n")
    page.text(lx + 15, ly + 1, 9, "stříhat")
    page.text(lx + 15, ly + 9, 9, "ohnout dozadu")
    page.text(lx + 15, ly + 17, 9, "lepidlo jen sem" if sleeve else "lepicí chlopeň")
    page.text(lx, ly + 27, 9, "Postup skládání:")
    page.text(lx, ly + 32, 9, "Navod_rubikova_kostka.pdf" if sleeve else "Navod_kostka_z_kartonu.pdf")
    return page.content()


def panel_sizes(edge, board):
    """(letter, where it goes, width, height) of the cardboard panels; each is cut twice."""
    inner = edge - 2 * board
    return [
        ("A", "horní a spodní stěna", edge, edge),
        ("B", "přední a zadní stěna", edge, inner),
        ("C", "levá a pravá stěna", inner, inner),
    ]


def build_panels(edge, board):
    page = Page()
    page.raw("0 g\n")
    page.text(15, 14, 13, f"Cube Arc – šablona na kostku {edge:g} mm z lepenky tloušťky {board:g} mm")
    page.text(15, 20, 9, "Tiskněte ve 100 % (bez přizpůsobení stránce). Pravítkem zkontrolujte, že měřítko měří 100 mm:")
    page.scale_bar(15, 26)
    page.text(15, 36, 9, "Vystřihněte dílky nahrubo, přilepte je na lepenku a řežte po čáře. U dílů B a C ať vlny lepenky běží ve směru šipky.")

    for row, (letter, where, w, h) in enumerate(panel_sizes(edge, board)):
        y = 44 + row * (edge + 12)
        for col in range(2):
            x = 30 + col * (edge + 25)
            page.raw("0.35 G 0.5 w 0 g\n")
            page.polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], "S")
            page.text_rotated(x + w / 2, y + h / 2 - 6, 24, letter, 0)
            page.text_rotated(x + w / 2, y + h / 2 + 4, 8, f"{w:g} × {h:g} mm".replace(".", ","), 0)
            page.text_rotated(x + w / 2, y + h / 2 + 9, 7, where, 0)
            if letter != "A":
                ax = x + w - 5
                page.raw("0.35 G 0.6 w 0.35 g\n")
                page.line((ax, y + 8), (ax, y + h - 8))
                for tip, d in ((y + 6, 1), (y + h - 6, -1)):
                    page.polygon([(ax, tip), (ax - 1.3, tip + d * 2.6), (ax + 1.3, tip + d * 2.6)], "f")
                page.raw("0 g\n")

    y = 44 + 3 * (edge + 12) + 2
    page.text(15, y, 9, f"Máte jinou lepenku? Změřte její tloušťku t. Díl A zůstává {edge:g} × {edge:g}, "
                        f"B je {edge:g} × ({edge:g} – 2t), C je ({edge:g} – 2t) × ({edge:g} – 2t).")
    page.text(15, y + 5, 9, "Kostka smí být o 0,5 mm menší, ale ne větší, jinak se obal nespojí.")
    return page.content()


def card_faces(edge, card):
    """
    Faces of the one-piece card cube in net millimetres: face -> (x, y, width, height), y down.

    The sizes are measured between the middle planes of the folded card, so that the finished cube
    is edge - CARD_CLEARANCE_MM on the outside: the strip 0-1-3 is narrower by two card thicknesses
    (faces 4 and 5 lie over its tabs) and face 3 is shorter by one (face 0 lies over its tab).
    """
    s = edge - CARD_CLEARANCE_MM - card
    strip = s - 2 * card
    depth = s + card / 2  # faces with a free end reach the outer surface of the back wall
    return {
        0: (-strip / 2, 0, strip, depth),
        2: (-s / 2, depth, s, s),
        4: (-s / 2 - depth, depth, depth, s),
        5: (s / 2, depth, depth, s),
        1: (-strip / 2, depth + s, strip, s),
        3: (-strip / 2, depth + 2 * s, strip, s - card),
    }


def card_tab(faces, face, side, tab=CARD_TAB_MM):
    """Trapezoid tab of the card net, in the direction of the outline (clockwise)."""
    x, y, w, h = faces[face]
    if side == "R":
        return [(x + w, y), (x + w + tab, y + tab), (x + w + tab, y + h - tab), (x + w, y + h)]
    if side == "L":
        return [(x, y + h), (x - tab, y + h - tab), (x - tab, y + tab), (x, y)]
    return [(x + w, y + h), (x + w - tab, y + h + tab), (x + tab, y + h + tab), (x, y + h)]


def card_outline(edge, card):
    f = card_faces(edge, card)

    def corner(face, right, bottom):
        x, y, w, h = f[face]
        return (x + w * right, y + h * bottom)

    points = [corner(0, 0, 0)] + card_tab(f, 0, "R") + [corner(2, 1, 0)]
    points += [corner(5, 1, 0), corner(5, 1, 1), corner(2, 1, 1)] + card_tab(f, 1, "R") + card_tab(f, 3, "R")
    points += card_tab(f, 3, "B") + card_tab(f, 3, "L") + card_tab(f, 1, "L") + [corner(2, 0, 1)]
    points += [corner(4, 0, 1), corner(4, 0, 0), corner(2, 0, 0)] + card_tab(f, 0, "L")
    return [p for i, p in enumerate(points) if p != points[i - 1]]


def build_card(edge, card):
    page = Page()
    thick = f"{card:g}".replace(".", ",")
    page.raw("0 g\n")
    page.text(15, 14, 13, f"Cube Arc – kostka {edge:g} mm z jednoho kusu, tenký karton {thick} mm".replace(".", ","))
    page.text(15, 20, 9, "Tiskněte ve 100 % (bez přizpůsobení stránce). Pravítkem zkontrolujte, že měřítko měří 100 mm:")
    page.scale_bar(15, 26)
    page.text(140, 27, 9, "Šablona bez markerů, obal je na straně 1.")

    ox, oy = 105, 37
    faces = card_faces(edge, card)

    def at(points):
        return [(ox + x, oy + y) for x, y in points]

    for face, side, over in TABS:
        pts = at(card_tab(faces, face, side))
        page.raw("0.93 g\n")
        page.polygon(pts, "f")
        page.raw("0.35 g\n")
        cx, cy = sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4
        page.text_rotated(cx, cy, 8, f"pod {over}", {"L": 1, "R": 3, "B": 0}[side])
    page.raw("0.35 g\n")
    for face, (x, y, w, h) in faces.items():
        page.text_rotated(ox + x + w / 2, oy + y + h / 2 - 2, 30, str(face), 2 if NET[face][2] else 0)
        page.text_rotated(ox + x + w / 2, oy + y + h / 2 + (-12 if NET[face][2] else 8), 8, FACE_NAMES[face].lower(),
                          2 if NET[face][2] else 0)

    page.raw("0.55 G 0.4 w [4 2.5] 0 d\n")
    for face, side in [(0, "B"), (1, "T"), (1, "B"), (4, "R"), (5, "L")]:
        x, y, w, h = faces[face]
        page.line(*at({"B": [(x, y + h), (x + w, y + h)], "T": [(x, y), (x + w, y)],
                       "R": [(x + w, y), (x + w, y + h)], "L": [(x, y), (x, y + h)]}[side]))
    for face, side, _ in TABS:
        pts = at(card_tab(faces, face, side))
        page.line(pts[0], pts[-1])
    page.raw("[] 0 d 0.35 G 0.5 w 1 j\n")
    page.polygon(at(card_outline(edge, card)), "S")

    ly = oy + edge * 2 + 16
    lx = ox + edge / 2 + CARD_TAB_MM + 8
    page.line((lx, ly), (lx + 12, ly))
    page.raw("0.55 G 0.4 w [4 2.5] 0 d\n")
    page.line((lx, ly + 8), (lx + 12, ly + 8))
    page.raw("[] 0 d 0.93 g\n")
    page.polygon([(lx, ly + 13.5), (lx + 12, ly + 13.5), (lx + 12, ly + 18.5), (lx, ly + 18.5)], "f")
    page.raw("0 g\n")
    page.text(lx + 15, ly + 1, 9, "stříhat")
    page.text(lx + 15, ly + 9, 9, "ohnout dozadu")
    page.text(lx + 15, ly + 17, 9, "lepicí chlopeň")
    page.text(lx, ly + 27, 9, "Postup skládání:")
    page.text(lx, ly + 32, 9, "Navod_kostka_z_kartonu.pdf")
    page.text(lx, ly + 37, 9, "strana 4")
    return page.content()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--edge-mm", type=float, default=50.0, help="cube edge length in millimetres")
    parser.add_argument("--board-mm", type=float, default=3.0, help="cardboard thickness in millimetres")
    parser.add_argument("--card-mm", type=float, nargs="+", default=[0.5, 1.0], help="thin card thicknesses for the one-piece cube")
    parser.add_argument("--cell-mm", type=float, default=None, help="tag cell size (default: the tag fills 90 %% of the face)")
    parser.add_argument("--sleeve", action="store_true", help="only a slightly larger wrap that is not glued to the cube")
    parser.add_argument("--out", default=None, help="output PDF path")
    args = parser.parse_args()

    if not 40 <= args.edge_mm <= 60:
        parser.error("--edge-mm must be between 40 and 60 (the net has to fit on one A4 page)")
    if not 0.5 <= args.board_mm <= 8:
        parser.error("--board-mm must be between 0.5 and 8")

    if not all(0.1 <= c <= 1.5 for c in args.card_mm):
        parser.error("--card-mm must be between 0.1 and 1.5")
    largest = cell_size_mm(args.edge_mm)
    cell = args.cell_mm or largest
    if not 3 <= cell <= largest:
        parser.error(f"--cell-mm must be between 3 and {largest:g} for this cube")

    out = args.out or f"cube_{'sleeve' if args.sleeve else 'wrap'}_{args.edge_mm:g}mm.pdf"
    pages = [build_wrap(args.edge_mm, cell, args.sleeve)]
    if not args.sleeve:
        pages += [build_panels(args.edge_mm, args.board_mm)] + [build_card(args.edge_mm, c) for c in args.card_mm]
    write_pdf(out, pages)

    print(f"Wrote {out}")
    print(f"cubeEdge = {metres(args.edge_mm)} m, tagSize = {cell * WIDTH_AT_BORDER / 1000:.4f} m "
          f"(whole printed tag {cell * TOTAL_WIDTH:.1f} mm)")


if __name__ == "__main__":
    main()
