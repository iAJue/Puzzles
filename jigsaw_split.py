"""Split an input image into jigsaw-like puzzle piece PNGs.

Usage:
    python jigsaw_split.py input.jpg --rows 3 --cols 4 --output pieces_dir --seed 42

Each piece is saved with transparency so you only keep the puzzle shape.
"""

from __future__ import annotations

import argparse
import os
import random
from dataclasses import dataclass
from typing import List, Tuple

try:
    from PIL import Image, ImageDraw
except ImportError as exc:  # pragma: no cover - pillow not installed
    raise SystemExit("Pillow is required. Install with: pip install pillow") from exc


@dataclass
class PieceEdges:
    top: int
    right: int
    bottom: int
    left: int


def build_edge_layout(rows: int, cols: int, rng: random.Random) -> Tuple[List[List[int]], List[List[int]]]:
    """Create matching bump/hole directions for every shared edge."""
    horizontal = [[0 for _ in range(cols)] for _ in range(rows + 1)]  # between rows
    vertical = [[0 for _ in range(cols + 1)] for _ in range(rows)]  # between cols

    for r in range(1, rows):  # internal horizontal seams
        for c in range(cols):
            horizontal[r][c] = rng.choice([-1, 1])

    for r in range(rows):  # internal vertical seams
        for c in range(1, cols):
            vertical[r][c] = rng.choice([-1, 1])

    return horizontal, vertical


def bounds(total: int, parts: int) -> List[int]:
    """Compute near-even integer boundaries that exactly cover total pixels."""
    base = total // parts
    extra = total % parts
    sizes = [base + (1 if i < extra else 0) for i in range(parts)]
    pts = [0]
    for s in sizes:
        pts.append(pts[-1] + s)
    return pts


def piece_edges(r: int, c: int, horizontal, vertical) -> PieceEdges:
    """Return edge orientation (1=tab, -1=hole, 0=flat) for a piece."""
    top = -horizontal[r][c]
    bottom = horizontal[r + 1][c]
    left = -vertical[r][c]
    right = vertical[r][c + 1]
    return PieceEdges(top=top, right=right, bottom=bottom, left=left)


def draw_piece_mask(width: int, height: int, edges: PieceEdges, tab_radius: int) -> Tuple[Image.Image, int]:
    """Generate a white-on-black mask describing the puzzle shape."""
    # Keep padding consistent and large enough for tabs to fully fit.
    pad = tab_radius * 2 + 2
    w, h = width + pad * 2, height + pad * 2
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle([pad, pad, pad + width - 1, pad + height - 1], fill=255)

    neck = max(2, int(tab_radius * 0.45))

    def rect(x0: int, y0: int, x1: int, y1: int, *, fill: int) -> None:
        draw.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], fill=fill)

    def add_tab(side: str, orientation: int) -> None:
        if orientation == 0:
            return

        r = tab_radius
        tab_offset = max(1, int(round(r * 0.6)))  # smaller -> less protruding tabs (and matching shallower holes)

        def ellipse(cx: int, cy: int, *, fill: int) -> None:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)

        if side in ("top", "bottom"):
            cx = pad + width // 2
            boundary_y = pad if side == "top" else (pad + height)
            inside_y = boundary_y if side == "top" else (boundary_y - 1)
            sign_out = -1 if side == "top" else 1
            sign_in = -sign_out

            if orientation == 1:  # bump (outward)
                rect(cx - neck, inside_y, cx + neck, boundary_y + sign_out * tab_offset, fill=255)
                ellipse(cx, boundary_y + sign_out * tab_offset, fill=255)
            else:  # hole (inward)
                rect(cx - neck, inside_y, cx + neck, inside_y + sign_in * tab_offset, fill=0)
                ellipse(cx, boundary_y + sign_in * tab_offset, fill=0)

        else:  # left/right
            cy = pad + height // 2
            boundary_x = pad if side == "left" else (pad + width)
            inside_x = boundary_x if side == "left" else (boundary_x - 1)
            sign_out = -1 if side == "left" else 1
            sign_in = -sign_out

            if orientation == 1:  # bump (outward)
                rect(inside_x, cy - neck, boundary_x + sign_out * tab_offset, cy + neck, fill=255)
                ellipse(boundary_x + sign_out * tab_offset, cy, fill=255)
            else:  # hole (inward)
                rect(inside_x, cy - neck, inside_x + sign_in * tab_offset, cy + neck, fill=0)
                ellipse(boundary_x + sign_in * tab_offset, cy, fill=0)

    add_tab("top", edges.top)
    add_tab("right", edges.right)
    add_tab("bottom", edges.bottom)
    add_tab("left", edges.left)
    return mask, pad


def split_image(image_path: str, rows: int, cols: int, output_dir: str, seed: int | None = None) -> None:
    rng = random.Random(seed)
    image = Image.open(image_path).convert("RGBA")
    width, height = image.size
    x_bounds = bounds(width, cols)
    y_bounds = bounds(height, rows)

    os.makedirs(output_dir, exist_ok=True)
    horizontal, vertical = build_edge_layout(rows, cols, rng)

    # Use a single tab size across all pieces so seams match perfectly.
    cell_w_min = min(x_bounds[i + 1] - x_bounds[i] for i in range(cols))
    cell_h_min = min(y_bounds[i + 1] - y_bounds[i] for i in range(rows))
    global_tab_radius = max(8, min(cell_w_min, cell_h_min) // 5)

    for r in range(rows):
        for c in range(cols):
            x0, x1 = x_bounds[c], x_bounds[c + 1]
            y0, y1 = y_bounds[r], y_bounds[r + 1]
            piece_w, piece_h = x1 - x0, y1 - y0
            edges = piece_edges(r, c, horizontal, vertical)
            mask, pad = draw_piece_mask(piece_w, piece_h, edges, global_tab_radius)
            crop_box = (
                max(0, x0 - pad),
                max(0, y0 - pad),
                min(width, x1 + pad),
                min(height, y1 + pad),
            )
            crop = image.crop(crop_box)

            piece = Image.new("RGBA", mask.size, (0, 0, 0, 0))
            offset_x = max(0, (x0 - pad) * -1)
            offset_y = max(0, (y0 - pad) * -1)
            piece.paste(crop, (offset_x, offset_y))
            piece.putalpha(mask)

            filename = os.path.join(output_dir, f"piece_r{r}_c{c}.png")
            piece.save(filename)
            print(f"Saved {filename}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split an image into jigsaw puzzle pieces.")
    parser.add_argument("image", help="Path to the source image")
    parser.add_argument("--rows", type=int, required=True, help="Number of puzzle rows")
    parser.add_argument("--cols", type=int, required=True, help="Number of puzzle columns")
    parser.add_argument("--output", default="pieces", help="Directory to write piece PNGs")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed for repeatable tabs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    split_image(args.image, args.rows, args.cols, args.output, args.seed)


if __name__ == "__main__":
    main()
