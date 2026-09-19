"""Core difference detection engine for visual regression."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageFilter, ImageDraw, ImageFont


@dataclass
class DiffRegion:
    """A contiguous region of difference between two images."""
    box: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    area: int = 0
    severity: str = "low"  # low | medium | high

    def __post_init__(self):
        if self.area == 0:
            self.area = (self.box[2] - self.box[0]) * (self.box[3] - self.box[1])


@dataclass
class DiffResult:
    """Result of comparing two images."""
    image_a: Path
    image_b: Path
    width: int = 0
    height: int = 0
    similarity: float = 1.0  # 1.0 = identical
    diff_pixels: int = 0
    regions: list[DiffRegion] = field(default_factory=list)
    diff_image: Image.Image | None = None
    side_by_side: Image.Image | None = None

    @property
    def passed(self) -> bool:
        return self.similarity >= 0.98

    @property
    def status(self) -> str:
        if self.similarity >= 0.995:
            return "IDENTICAL"
        elif self.similarity >= 0.98:
            return "MINOR"
        elif self.similarity >= 0.90:
            return "MODERATE"
        elif self.similarity >= 0.70:
            return "SIGNIFICANT"
        return "MAJOR"


def _load_images(a: Path, b: Path) -> tuple[Image.Image, Image.Image]:
    img_a = Image.open(a).convert("RGB")
    img_b = Image.open(b).convert("RGB")
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size, Image.LANCZOS)
    return img_a, img_b


def _find_blobs(mask: Image.Image, min_area: int = 50) -> list[tuple[int, int, int, int]]:
    """Find connected components in a binary mask."""
    w, h = mask.size
    visited: set[tuple[int, int]] = set()
    boxes: list[tuple[int, int, int, int]] = []
    pixels = mask.load()

    def dfs(x: int, y: int) -> tuple[int, int, int, int]:
        stack = [(x, y)]
        min_x, min_y, max_x, max_y = x, y, x, y
        local_visited: set[tuple[int, int]] = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited or (cx, cy) in local_visited:
                continue
            local_visited.add((cx, cy))
            if not (0 <= cx < w and 0 <= cy < h):
                continue
            if pixels[cx, cy] == 0:
                continue
            visited.add((cx, cy))
            min_x = min(min_x, cx)
            max_x = max(max_x, cx)
            min_y = min(min_y, cy)
            max_y = max(max_y, cy)
            stack.extend([(cx-1, cy), (cx+1, cy), (cx, cy-1), (cx, cy+1)])
        return min_x, min_y, max_x + 1, max_y + 1

    for y in range(h):
        for x in range(w):
            if (x, y) not in visited and pixels[x, y] != 0:
                box = dfs(x, y)
                area = (box[2] - box[0]) * (box[3] - box[1])
                if area >= min_area:
                    boxes.append(box)

    return boxes


def compute_diff(a: Path | str, b: Path | str, threshold: int = 30,
                 min_region_area: int = 50) -> DiffResult:
    """Compare two images and return a structured diff result."""
    a_path = Path(a)
    b_path = Path(b)

    img_a, img_b = _load_images(a_path, b_path)
    w, h = img_a.size

    # Pixel-level diff
    diff = ImageChops.difference(img_a, img_b)
    diff_data = diff.getdata()

    diff_pixels = 0
    for r, g, b in diff_data:
        if r > threshold or g > threshold or b > threshold:
            diff_pixels += 1

    total_pixels = w * h
    similarity = 1.0 - (diff_pixels / total_pixels) if total_pixels else 1.0

    # Highlight diff regions
    diff_gray = diff.convert("L")
    diff_mask = diff_gray.point(lambda p: 255 if p > threshold else 0)
    regions: list[DiffRegion] = []

    blob_boxes = _find_blobs(diff_mask, min_area=min_region_area)
    for blob_box in blob_boxes:
        area = (blob_box[2] - blob_box[0]) * (blob_box[3] - blob_box[1])
        sev = "high" if area > w * h * 0.05 else ("medium" if area > w * h * 0.01 else "low")
        regions.append(DiffRegion(box=blob_box, area=area, severity=sev))

    # Build diff highlight image (red overlay)
    diff_highlight = img_a.copy()
    if regions:
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for region in regions:
            x1, y1, x2, y2 = region.box
            od.rectangle([x1, y1, x2, y2], fill=(255, 50, 50, 80), outline=(255, 0, 0, 255))
        diff_highlight = Image.alpha_composite(diff_highlight.convert("RGBA"), overlay).convert("RGB")

    # Side-by-side
    side = Image.new("RGB", (w * 2 + 20, h), (240, 240, 240))
    side.paste(img_a, (0, 0))
    side.paste(diff_highlight, (w + 20, 0))
    sd = ImageDraw.Draw(side)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
    sd.text((w / 2 - 30, 5), "BEFORE", fill=(0, 0, 0))
    sd.text((w + 20 + w / 2 - 40, 5), "AFTER (diff)", fill=(0, 0, 0))

    return DiffResult(
        image_a=a_path,
        image_b=b_path,
        width=w,
        height=h,
        similarity=round(similarity, 4),
        diff_pixels=diff_pixels,
        regions=regions,
        diff_image=diff_highlight,
        side_by_side=side,
    )
