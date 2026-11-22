"""
Generates a printable A4 PDF with the six AprilTag markers (family tagStandard41h12, IDs 0-5)
for the physical cube used by the Cube Arc game. Needs only the Python standard library.

Usage:
    python generate_cube_markers.py                 # 50 mm cube -> cube_markers_50mm.pdf
    python generate_cube_markers.py --edge-mm 60

Print at 100 % (no "fit to page") and check the 100 mm scale bar with a ruler.
The script prints the values to enter on AprilTagCubeTracker (cubeEdge, tagSize).

The tag codes and bit layout below were read from the native AprilTag library shipped
in the Unity package jp.keijiro.apriltag 1.0.3 (tagStandard41h12_create), and are drawn
the same way as apriltag_to_image() in the AprilTag sources.
"""
import argparse
import math

# --- tagStandard41h12 (from the AprilTag library) ---
TOTAL_WIDTH = 9          # cells across the whole tag image
WIDTH_AT_BORDER = 5      # cells across the detected border = the "tag size" for pose estimation
REVERSED_BORDER = True
NBITS = 41
BIT_X = [-2, -1, 0, 1, 2, 3, 4, 5, 1, 2, 6, 6, 6, 6, 6, 6, 6, 6, 3, 3, 6, 5, 4, 3, 2, 1, 0, -1, 3, 2,
         -2, -2, -2, -2, -2, -2, -2, -2, 1, 1, 2]
BIT_Y = [-2, -2, -2, -2, -2, -2, -2, -2, 1, 1, -2, -1, 0, 1, 2, 3, 4, 5, 1, 2, 6, 6, 6, 6, 6, 6, 6, 6, 3, 3,
         6, 5, 4, 3, 2, 1, 0, -1, 3, 2, 2]
CODES = [0x1bd8a64ad10, 0x1bdc4f3b2d5, 0x1bdff82b89a, 0x1be3a11be5f, 0x1be74a0c424, 0x1beaf2fc9e9]

# Face for each tag ID; must match MR_app/Assets/App/Games/CubeArc/Scripts/Core/CubeFaceLayout.cs
# (title, detail) printed as two lines under each face
FACES = [
    ("ID 0 – HORNÍ stěna", "Horní hrana tagu ke stěně ID 3."),
    ("ID 1 – SPODNÍ stěna", "Horní hrana tagu ke stěně ID 3."),
    ("ID 2 – PŘEDNÍ stěna", "Horní hrana tagu nahoru (k ID 0)."),
    ("ID 3 – ZADNÍ stěna", "Horní hrana tagu nahoru (k ID 0)."),
    ("ID 4 – LEVÁ stěna (při pohledu na ID 2)", "Horní hrana tagu nahoru (k ID 0)."),
    ("ID 5 – PRAVÁ stěna (při pohledu na ID 2)", "Horní hrana tagu nahoru (k ID 0)."),
]

# Text is written in Windows-1250 (Central European) and the font gets a /Differences
# encoding that names the glyph for each Czech character, so diacritics print correctly
# with the standard Helvetica font (no font embedding needed).
TEXT_CODEC = "cp1250"
GLYPH_NAMES = {
    "á": "aacute", "č": "ccaron", "ď": "dcaron", "é": "eacute", "ě": "ecaron", "í": "iacute",
    "ň": "ncaron", "ó": "oacute", "ř": "rcaron", "š": "scaron", "ť": "tcaron", "ú": "uacute",
    "ů": "uring", "ý": "yacute", "ž": "zcaron",
    "Á": "Aacute", "Č": "Ccaron", "Ď": "Dcaron", "É": "Eacute", "Ě": "Ecaron", "Í": "Iacute",
    "Ň": "Ncaron", "Ó": "Oacute", "Ř": "Rcaron", "Š": "Scaron", "Ť": "Tcaron", "Ú": "Uacute",
    "Ů": "Uring", "Ý": "Yacute", "Ž": "Zcaron",
    "–": "endash",
}

MM = 72.0 / 25.4  # PDF points per millimetre
PAGE_W, PAGE_H = 210 * MM, 297 * MM


def tag_cells(tag_id):
    """Returns a TOTAL_WIDTH x TOTAL_WIDTH grid, True = white, row 0 = top of the tag."""
    grid = [[False] * TOTAL_WIDTH for _ in range(TOTAL_WIDTH)]
    white_border_width = WIDTH_AT_BORDER + (0 if REVERSED_BORDER else 2)
    s = (TOTAL_WIDTH - white_border_width) // 2
    for i in range(white_border_width - 1):
        grid[s][s + i] = True
        grid[s + i][TOTAL_WIDTH - 1 - s] = True
        grid[TOTAL_WIDTH - 1 - s][s + i + 1] = True
        grid[s + 1 + i][s] = True

    border_start = (TOTAL_WIDTH - WIDTH_AT_BORDER) // 2
    code = CODES[tag_id]
    for i in range(NBITS):
        if code & (1 << (NBITS - i - 1)):
            grid[BIT_Y[i] + border_start][BIT_X[i] + border_start] = True
    return grid


def pdf_text(x, y, size, text):
    unsupported = {ch for ch in text if ord(ch) > 127 and ch not in GLYPH_NAMES}
    if unsupported:
        raise ValueError(f"add these characters to GLYPH_NAMES: {''.join(sorted(unsupported))}")
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"BT /F1 {size:.1f} Tf {x:.2f} {y:.2f} Td ({safe}) Tj ET\n"


def build_page(edge_mm, cell_mm):
    tag_mm = cell_mm * TOTAL_WIDTH
    ops = []

    # Header (y measured from the top of the page)
    def top(mm_from_top):
        return PAGE_H - mm_from_top * MM

    ops.append("0 g\n")
    ops.append(pdf_text(15 * MM, top(14), 13, f"Cube Arc – markery na kostku {edge_mm:g} mm (AprilTag tagStandard41h12)"))
    ops.append(pdf_text(15 * MM, top(20), 9, "Tiskněte ve 100 % (bez přizpůsobení stránce). Pravítkem zkontrolujte, že měřítko měří 100 mm:"))
    ops.append(pdf_text(15 * MM, top(25), 9, f"Nastavení v Unity (AprilTagCubeTracker): cubeEdge = {edge_mm / 1000:.3f}, tagSize = {cell_mm * WIDTH_AT_BORDER / 1000:.4f}"))

    # 100 mm scale bar
    bar_y = top(31)
    ops.append(f"{15 * MM:.2f} {bar_y:.2f} {100 * MM:.2f} {1.2 * MM:.2f} re f\n")
    for i in range(11):
        x = 15 * MM + i * 10 * MM
        ops.append(f"{x:.2f} {bar_y:.2f} {0.3 * MM:.2f} {-2.5 * MM:.2f} re f\n")
    ops.append(pdf_text(118 * MM, bar_y - 1 * MM, 9, "100 mm"))

    # 2 columns x 3 rows of face squares
    col_x = [20 * MM, (20 + edge_mm + 25) * MM]
    row_top_mm = [42, 42 + edge_mm + 16, 42 + 2 * (edge_mm + 16)]
    for tag_id in range(6):
        cx = col_x[tag_id % 2]
        face_top = top(row_top_mm[tag_id // 2])
        face_bottom = face_top - edge_mm * MM

        # Cut outline of the face (thin grey)
        ops.append("0.6 G 0.3 w\n")
        ops.append(f"{cx:.2f} {face_bottom:.2f} {edge_mm * MM:.2f} {edge_mm * MM:.2f} re S\n")

        # Tag, centred on the face. Black cells are drawn; white is the paper.
        ops.append("0 g\n")
        margin = (edge_mm - tag_mm) / 2
        origin_x = cx + margin * MM
        origin_top = face_top - margin * MM
        grid = tag_cells(tag_id)
        for row in range(TOTAL_WIDTH):
            for col in range(TOTAL_WIDTH):
                if not grid[row][col]:
                    x = origin_x + col * cell_mm * MM
                    y = origin_top - (row + 1) * cell_mm * MM
                    # tiny overlap avoids hairline gaps between cells in some viewers
                    ops.append(f"{x:.3f} {y:.3f} {cell_mm * MM + 0.05:.3f} {cell_mm * MM + 0.05:.3f} re f\n")

        # Arrow above the tag marks its top edge
        ax = cx + edge_mm * MM / 2
        ay = face_top - margin * MM / 2
        ops.append("0.4 g\n")
        ops.append(f"{ax - 2 * MM:.2f} {ay - 1 * MM:.2f} m {ax + 2 * MM:.2f} {ay - 1 * MM:.2f} l {ax:.2f} {ay + 1 * MM:.2f} l f\n")

        ops.append("0 g\n")
        title, detail = FACES[tag_id]
        ops.append(pdf_text(cx, face_bottom - 5 * MM, 8.5, title))
        ops.append(pdf_text(cx, face_bottom - 9 * MM, 7.5, detail))

    return "".join(ops)


def font_encoding():
    """WinAnsi base encoding with the Windows-1250 codes of the Czech characters mapped to their glyphs."""
    diffs = sorted((ch.encode(TEXT_CODEC)[0], name) for ch, name in GLYPH_NAMES.items())
    entries = " ".join(f"{code} /{name}" for code, name in diffs)
    return f"<< /Type /Encoding /BaseEncoding /WinAnsiEncoding /Differences [{entries}] >>"


def write_pdf(path, content):
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W:.2f} {PAGE_H:.2f}] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(content.encode(TEXT_CODEC))} >>\nstream\n{content}endstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding 6 0 R >>",
        font_encoding(),
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode(TEXT_CODEC)
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode("latin-1")
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("latin-1")
    with open(path, "wb") as f:
        f.write(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--edge-mm", type=float, default=50.0, help="cube edge length in millimetres")
    parser.add_argument("--out", default=None, help="output PDF path")
    args = parser.parse_args()

    if not 40 <= args.edge_mm <= 85:
        parser.error("--edge-mm must be between 40 and 85 (six faces have to fit on one A4 page)")

    # Tag fills ~90 % of the face; cell size rounded down to 0.1 mm so it prints cleanly.
    cell_mm = math.floor(args.edge_mm * 0.9 / TOTAL_WIDTH * 10) / 10
    out = args.out or f"cube_markers_{args.edge_mm:g}mm.pdf"
    write_pdf(out, build_page(args.edge_mm, cell_mm))

    print(f"Wrote {out}")
    print(f"cubeEdge = {args.edge_mm / 1000:.3f} m, tagSize = {cell_mm * WIDTH_AT_BORDER / 1000:.4f} m "
          f"(whole printed tag {cell_mm * TOTAL_WIDTH:.1f} mm)")


if __name__ == "__main__":
    main()
