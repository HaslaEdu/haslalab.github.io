#!/usr/bin/env python3
"""Build self-contained SVG display variants without changing official source assets.

Pillow/NumPy are used only for in-memory pixel analysis. The source raster bytes are
embedded unchanged; exterior-background removal is an SVG vector mask, and dark
ink adjustments are SVG filters/vector overlays. No derived raster is written.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from collections import deque

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "logo"
INK = "#ded5ee"
NS = "http://www.w3.org/2000/svg"
# Reviewed in the actual dark UI. These published marks use very dark colored
# ink; lift their tone while retaining the source channel ordering and alpha.
DARK_GAMMA = {"cpho": 0.40, "rupho": 0.40, "ruphow": 0.40, "ruphox": 0.40,
              "ruphoy": 0.40, "iypt": 0.45, "ibo": 0.45, "ijso": 0.45,
              "useso": 0.40, "iao": 0.45, "owao": 0.45, "apho": 0.45,
              "eupho": 0.45, "kphe": 0.45, "amc": 0.45}
# Pure blue/navy retains a low luminance even after gamma. A small additive
# floor lifts those reviewed marks on dark UI; white stays white and alpha stays.
DARK_FLOOR = {key: 0.20 for key in ("iao", "owao", "apho", "eupho", "kphe", "amc")}
PALE_INK = {"imcho"}  # The published IMChO mark is effectively one dark navy ink.
# Reviewed flat-paper wordmarks: white enclosed by A/O/P/etc. is paper, not
# white ink. Preserve the illustrated emblem to the left of these x positions.
# KMO/USABO/RuPhO are entirely flat colored wordmarks with negative-space holes.
PAPER_WORDMARK_X = {"kmo": 0, "amc": 76, "putnam": 195, "usabo": 0,
                    "usnco": 300, "rupho": 0, "ruphow": 0, "ruphox": 0,
                    "ruphoy": 0}
PAPER_WORDMARK_SIZE = {"kmo": (246, 49), "amc": (204, 70), "putnam": (683, 178),
                       "usabo": (300, 136), "usnco": (1243, 290),
                       **{key: (538, 76) for key in ("rupho", "ruphow", "ruphox", "ruphoy")}}
# These sources were published against a colored/white matte. Their soft edge
# pixels contain paper mixed into the ink; deleting only white pixels leaves a
# visible light fringe. Reconstruct those reviewed edge samples as SVG paint.
EDGE_MATTE = {"usaaao": (246, 230, 240), "amc": (255, 255, 255),
              "kmchc": (211, 237, 250), "wopho": (255, 255, 255),
              "eotvos": (254, 254, 254),
              **{key: (255, 255, 255) for key in ("rupho", "ruphow", "ruphox", "ruphoy")}}
EDGE_MATTE_SIZE = {"usaaao": (400, 400), "amc": (204, 70), "kmchc": (104, 128),
                   "wopho": (500, 132), "eotvos": (80, 98),
                   **{key: (538, 76) for key in ("rupho", "ruphow", "ruphox", "ruphoy")}}


def checked_svg(data: bytes) -> ET.Element:
    text = data.decode("utf-8-sig")
    if re.search(r"<!DOCTYPE|<!ENTITY|<\s*(?:script|foreignObject)\b", text, re.I):
        raise ValueError("Executable or external SVG content is not allowed")
    root = ET.fromstring(text)
    for node in root.iter():
        for key, value in node.attrib.items():
            local = key.rsplit("}", 1)[-1].lower()
            if local.startswith("on"):
                raise ValueError("SVG event handlers are not allowed")
            if local == "href" and not value.startswith(("#", "data:image/")):
                raise ValueError("SVG must not refer to an external resource")
            if re.search(r"@import|url\(\s*[\"']?(?:https?:|//)", value, re.I):
                raise ValueError("External SVG styles are not allowed")
        if node.tag.rsplit("}", 1)[-1] == "style" and re.search(r"@import|https?:|url\(\s*[\"']?//", node.text or "", re.I):
            raise ValueError("External SVG styles are not allowed")
    return root


def source_image(path: Path):
    data = path.read_bytes()
    notes = []
    if path.suffix.lower() == ".svg":
        svg = checked_svg(data)
        embedded = [value for node in svg.iter() if node.tag.rsplit("}", 1)[-1] == "image"
                    for key, value in node.attrib.items() if key.rsplit("}", 1)[-1] == "href" and value.startswith("data:image/png;base64,")]
        # The current CMO SVG is a single original PNG in a scaling pattern. Reuse
        # that exact embedded image, rather than rasterizing/redrawing the SVG.
        if len(embedded) == 1:
            data = base64.b64decode(embedded[0].split(",", 1)[1])
            notes.append("The official SVG contains one raster image; its original embedded PNG bytes are reused unchanged.")
        else:
            view = [float(v) for v in svg.get("viewBox", "").replace(",", " ").split()]
            width = view[2] if len(view) == 4 else float(svg.get("width", "100").removesuffix("px"))
            height = view[3] if len(view) == 4 else float(svg.get("height", "100").removesuffix("px"))
            return data, "image/svg+xml", None, width, height, ["Native vector source retained without automatic pixel-based adjustments."]
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    return data, "image/png", np.array(image), image.width, image.height, notes


def edge_connected(candidate: np.ndarray) -> np.ndarray:
    """Scan-line flood fill: only components reaching the image boundary."""
    height, width = candidate.shape
    reached = np.zeros(candidate.shape, dtype=bool)
    queue = deque()
    for x in np.flatnonzero(candidate[0]):
        queue.append((int(x), 0))
    for x in np.flatnonzero(candidate[-1]):
        queue.append((int(x), height - 1))
    for y in np.flatnonzero(candidate[:, 0]):
        queue.append((0, int(y)))
    for y in np.flatnonzero(candidate[:, -1]):
        queue.append((width - 1, int(y)))
    while queue:
        x, y = queue.popleft()
        if reached[y, x] or not candidate[y, x]:
            continue
        left = x
        while left and candidate[y, left - 1] and not reached[y, left - 1]:
            left -= 1
        right = x + 1
        while right < width and candidate[y, right] and not reached[y, right]:
            right += 1
        reached[y, left:right] = True
        for adjacent in (y - 1, y + 1):
            if not 0 <= adjacent < height:
                continue
            row = candidate[adjacent, left:right] & ~reached[adjacent, left:right]
            starts = np.flatnonzero(row & ~np.r_[False, row[:-1]])
            queue.extend((left + int(start), adjacent) for start in starts)
    return reached


def mask_path(bits: np.ndarray) -> str:
    """Coalesce equal horizontal pixel runs into SVG rectangle subpaths."""
    active = {}
    rectangles = []
    for y in range(bits.shape[0] + 1):
        row = bits[y] if y < bits.shape[0] else np.zeros(bits.shape[1], dtype=bool)
        edges = np.flatnonzero(np.diff(np.r_[False, row, False].astype(np.int8)))
        spans = {(int(edges[i]), int(edges[i + 1])) for i in range(0, len(edges), 2)}
        for span in active.keys() - spans:
            top = active.pop(span)
            rectangles.append((span[0], top, span[1] - span[0], y - top))
        for span in spans - active.keys():
            active[span] = y
    return "".join(f"M{x} {y}h{w}v{h}h{-w}z" for x, y, w, h in rectangles)


def background_mask(rgba: np.ndarray):
    rgb = rgba[:, :, :3].astype(np.float32)
    alpha = rgba[:, :, 3]
    height, width = alpha.shape
    # Existing alpha is authoritative: e.g. APAO's white ring and Harvard's
    # white lettering belong to the mark and must not be deleted.
    if float(np.mean(alpha < 8)) > 0.01:
        return np.zeros(alpha.shape, dtype=bool), None
    sample = max(1, min(6, height // 8, width // 8))
    corners = np.concatenate([rgb[:sample, :sample].reshape(-1, 3), rgb[:sample, -sample:].reshape(-1, 3),
                              rgb[-sample:, :sample].reshape(-1, 3), rgb[-sample:, -sample:].reshape(-1, 3)])
    background = np.median(corners, axis=0)
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722])
    chroma = np.ptp(rgb, axis=2)
    if float(background.mean()) >= 210 and float(np.ptp(background)) < 60:
        # Includes a published pale pink/gray field, but never crosses dark or
        # saturated strokes. Interior white letters disconnected from the edge stay.
        near = (luminance >= 215) & (chroma <= 60) & (np.max(np.abs(rgb - background), axis=2) <= 65)
        kind = "light"
    elif float(background.max()) <= 35:
        near = (luminance <= 35) & (chroma <= 35)
        kind = "dark"
    else:
        return np.zeros(alpha.shape, dtype=bool), None
    removed = edge_connected(near & (alpha > 0))
    if removed.mean() < 0.01:
        return np.zeros(alpha.shape, dtype=bool), None
    return removed, kind


def dark_wordmark_mask(key: str, rgba: np.ndarray, exterior: np.ndarray):
    """Clear reviewed white-paper counters without erasing white emblem art.

    A flood fill from the image edge cannot reach a letter's closed counter.
    These source-specific wordmark regions have no white ink, so the same light
    paper colors can safely be removed there even when enclosed by colored ink.
    The source raster and the light-mode mask are deliberately left unchanged.
    """
    if key not in PAPER_WORDMARK_X:
        return exterior, None
    if (rgba.shape[1], rgba.shape[0]) != PAPER_WORDMARK_SIZE[key]:
        raise ValueError(f"Review the wordmark paper region after replacing {key}'s source artwork")
    rgb = rgba[:, :, :3].astype(np.float32)
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722])
    # Include the mild pink/gray paper field in the official USABO source and
    # JPEG near-whites. Dark/color strokes remain outside this paper range.
    paper = (luminance >= 215) & (np.ptp(rgb, axis=2) <= 60) & (rgba[:, :, 3] > 0)
    start = PAPER_WORDMARK_X[key]
    paper[:, :start] = False
    extra = paper & ~exterior
    return exterior | paper, {"x": start, "y": 0, "width": rgba.shape[1] - start,
                              "height": rgba.shape[0], "additionalPaperPixels": int(extra.sum())}


def bounds(bits: np.ndarray):
    ys, xs = np.nonzero(bits)
    if not len(xs):
        return [0, 0, bits.shape[1], bits.shape[0]]
    # Small proportional breathing room, rather than the source's large padding.
    pad = max(1, round(min(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1) * 0.025))
    left = max(0, int(xs.min()) - pad)
    top = max(0, int(ys.min()) - pad)
    right = min(bits.shape[1], int(xs.max()) + pad + 1)
    bottom = min(bits.shape[0], int(ys.max()) + pad + 1)
    return [left, top, right - left, bottom - top]


def mono_filter(white_ink=False):
    r, g, b = (int(INK[i:i + 2], 16) / 255 for i in (1, 3, 5))
    alpha = ".2126 .7152 .0722 0 0" if white_ink else "-.2126 -.7152 -.0722 0 1"
    return (f'<filter id="mono" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
            f'<feColorMatrix in="SourceGraphic" result="ink" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 {alpha}"/>'
            '<feComposite in="ink" in2="SourceGraphic" operator="in" result="coverage"/>'
            f'<feColorMatrix in="coverage" type="matrix" values="0 0 0 0 {r:.6f} 0 0 0 0 {g:.6f} 0 0 0 0 {b:.6f} 0 0 0 1 0"/>'
            '</filter>')


def matte_edge_paint(key, rgba, mode, gamma, floor):
    """Unmix reviewed paper-contaminated AA pixels without eroding solid ink.

    C = coverage * ink + (1-coverage) * matte. A nearby solid sample supplies
    the ink estimate. Its RGB is unmatted while its recovered coverage becomes
    alpha. Closed white emblem faces remain outside the reachable edge region.
    All derived paint is vector paths; the original embedded image is unchanged.
    """
    if key not in EDGE_MATTE:
        return None
    if (rgba.shape[1], rgba.shape[0]) != EDGE_MATTE_SIZE[key]:
        raise ValueError(f"Review the edge matte recipe after replacing {key}'s source artwork")
    rgb = rgba[:, :, :3].astype(np.float32)
    source_alpha = rgba[:, :, 3].astype(np.float32) / 255
    matte = np.array(EDGE_MATTE[key], dtype=np.float32)
    height, width = source_alpha.shape
    delta = matte - rgb
    strength = np.max(np.abs(delta), axis=2)
    # Core samples are unwhitened dark/saturated ink, never the light paper.
    core = (strength >= 145) & (source_alpha >= .85)
    if key == "kmchc":
        core = (strength >= 125) & (source_alpha >= .85)
    if key == "eotvos":
        core = (rgb.max(axis=2) < 40) & (source_alpha >= .85)
    weak = strength < (125 if key == "kmchc" else 145)
    if key == "amc":
        # The exterior can reach AA on the outside of the polyhedron, but cannot
        # cross its navy frame to erase its intentionally white enclosed faces.
        region = edge_connected(weak)
        region[:, 76:] |= weak[:, 76:]
    elif key == "wopho":
        # Opaque gray/silver bevel surfaces and internal white reflections are
        # artwork. Only the translucent export halo and exterior white rim flow.
        region = edge_connected((source_alpha < .995) | (strength < 65))
        region &= (source_alpha < .995) | (strength < 65)
    elif key == "eotvos":
        region = edge_connected(weak)
        # Its outer ellipse is genuine engraved artwork. Only treat the thin
        # exterior paper fringe: the text ring and portrait retain their exact
        # original image sampling rather than being rebuilt as pixel paths.
        yy, xx = np.indices((height, width))
        outside_ellipse = ((xx - 39.5) / 37) ** 2 + ((yy - 48.5) / 47) ** 2 >= .98
        region &= outside_ellipse
    else:
        # USAAAO and KMChC have the same paper color in their enclosed gaps.
        # RuPhO is a flat wordmark with no white ink anywhere in the source.
        region = weak
    paper = region & (strength < 23)
    candidates = region & ~paper & (source_alpha > 0)
    if key == "eotvos":
        # The previous engraving display already removed the very pale exterior
        # paper. Do not reintroduce it as a faint new ring while fixing its edge.
        paper |= region & (rgb.max(axis=2) >= 215)
        candidates &= rgb.max(axis=2) < 215
    ys, xs = np.nonzero(candidates)
    ink = np.zeros((len(xs), 3), dtype=np.float32)
    found = np.zeros(len(xs), dtype=bool)
    # A bounded nearest-solid search stays local to each colored stroke. Source
    # resolution is small, so no optional image-processing dependency is needed.
    offsets = sorted(((dx * dx + dy * dy, dy, dx) for dy in range(-8, 9)
                      for dx in range(-8, 9) if dx or dy))
    for _, dy, dx in offsets:
        todo = np.flatnonzero(~found)
        if not len(todo):
            break
        tx, ty = xs[todo] + dx, ys[todo] + dy
        valid = (tx >= 0) & (tx < width) & (ty >= 0) & (ty < height)
        todo, tx, ty = todo[valid], tx[valid], ty[valid]
        hit = core[ty, tx]
        ids = todo[hit]
        ink[ids] = rgb[ty[hit], tx[hit]]
        found[ids] = True
    if key == "eotvos":
        # This is a grayscale printed engraving, not a color-edge estimate.
        # Black paper coverage preserves the actual ellipse and portrait lines.
        ink[:] = 0
        found[:] = True
    selected = np.flatnonzero(found)
    colors = np.zeros((height, width, 3), dtype=np.uint8)
    opacity = np.zeros((height, width), dtype=np.uint8)
    replaced = paper.copy()
    if len(selected):
        y, x = ys[selected], xs[selected]
        observed, pigment = rgb[y, x], ink[selected]
        vector = matte - pigment
        coverage = np.clip(np.sum((matte - observed) * vector, axis=1) /
                           np.maximum(np.sum(vector * vector, axis=1), 1), 0, 1)
        residual = np.linalg.norm((matte - observed) - coverage[:, None] * vector, axis=1)
        # Samples not explained by a matte mix are genuine local colors/bevels.
        cleanable = (residual < 28) & (coverage < .995)
        y, x, pigment, observed, coverage = y[cleanable], x[cleanable], pigment[cleanable], observed[cleanable], coverage[cleanable]
        recovered = np.clip((observed - matte * (1 - coverage[:, None])) /
                            np.maximum(coverage[:, None], .001), 0, 255)
        recovered = np.where(coverage[:, None] < .35, pigment, recovered)
        alpha = source_alpha[y, x] * coverage
        # Suppress only very weak paper/JPEG noise; retain fractional edge ink.
        alpha = np.clip((alpha - .018) / .982, 0, 1)
        if mode.startswith("monochrome"):
            recovered[:] = np.array([222, 213, 238])
        else:
            original = recovered.copy()
            if gamma:
                recovered = 255 * (floor + (1 - floor) * (recovered / 255) ** gamma)
            if mode == "preserve-color-light-neutral-ink":
                luminance = original @ np.array([.2126, .7152, .0722])
                neutral = (np.ptp(original, axis=1) <= 18) & (luminance < 180)
                mix = np.clip((190 - luminance) / 190, 0, 1)
                recovered[neutral] = (recovered[neutral] * (1 - mix[neutral, None]) +
                                      np.array([222, 213, 238]) * mix[neutral, None])
        # 5-bit channels / 32 alpha levels keep small AA details while allowing
        # same-color rectangles to coalesce into compact deterministic paths.
        colors[y, x] = (np.round(recovered / 8) * 8).clip(0, 255).astype(np.uint8)
        opacity[y, x] = np.round(alpha * 32).clip(0, 32).astype(np.uint8)
        replaced[y, x] = True
    paint = []
    active = np.nonzero(opacity)
    groups = np.unique(np.c_[colors[active], opacity[active]], axis=0)
    for r, g, b, a in groups:
        bits = (opacity == a) & np.all(colors == (r, g, b), axis=2)
        paint.append(f'<path fill="#{r:02x}{g:02x}{b:02x}" opacity="{int(a) / 32:.5f}" d="{mask_path(bits)}"/>')
    return {"replaced": replaced, "paint": "".join(paint), "pixels": int(replaced.sum()),
            "paintPixels": int(np.count_nonzero(opacity)), "matte": list(EDGE_MATTE[key])}


def svg_variant(data, mime, width, height, view, removed, mode, neutral=None, gamma=False, floor=0, edge=None):
    definitions = []
    wrapper = []
    if removed is not None and removed.any():
        definitions.append(f'<mask id="exterior" maskUnits="userSpaceOnUse" x="0" y="0" width="{width}" height="{height}" mask-type="luminance">'
                           f'<rect width="{width}" height="{height}" fill="white"/><path fill="black" d="{mask_path(removed)}"/></mask>')
        wrapper.append('mask="url(#exterior)"')
    if edge is not None:
        definitions.append(f'<mask id="matte" maskUnits="userSpaceOnUse" x="0" y="0" width="{width}" height="{height}" mask-type="luminance">'
                           f'<rect width="{width}" height="{height}" fill="white"/><path fill="black" d="{mask_path(edge["replaced"])}"/></mask>')
    if mode.startswith("monochrome"):
        definitions.append(mono_filter(mode == "monochrome-light-ink"))
        image_filter = ' filter="url(#mono)"'
    elif gamma:
        definitions.append('<filter id="lift" color-interpolation-filters="sRGB"><feComponentTransfer>'
                           f'<feFuncR type="gamma" amplitude="{1-floor:.3f}" exponent="{gamma:.3f}" offset="{floor:.3f}"/>'
                           f'<feFuncG type="gamma" amplitude="{1-floor:.3f}" exponent="{gamma:.3f}" offset="{floor:.3f}"/>'
                           f'<feFuncB type="gamma" amplitude="{1-floor:.3f}" exponent="{gamma:.3f}" offset="{floor:.3f}"/>'
                           '</feComponentTransfer></filter>')
        image_filter = ' filter="url(#lift)"'
    else:
        image_filter = ""
    payload = base64.b64encode(data).decode("ascii")
    image = f'<image x="0" y="0" width="{width}" height="{height}" preserveAspectRatio="none" href="data:{mime};base64,{payload}"{image_filter}/>'
    overlays = []
    if neutral is not None:
        # Sixteen vector-opacity levels preserve the source antialiasing/alpha;
        # colored pixels and enclosed white lettering are never repainted.
        for level in range(1, 17):
            selected = neutral == level
            if selected.any():
                overlays.append(f'<path fill="{INK}" opacity="{level / 16:.4f}" d="{mask_path(selected)}"/>')
    x, y, w, h = view
    return (f'<svg xmlns="{NS}" width="{w}" height="{h}" viewBox="{x} {y} {w} {h}" role="img">'
            f'<title>Official source mark: {mode} display variant</title>'
            '<defs>' + "".join(definitions) + '</defs>' +
            ('<g mask="url(#matte)">' if edge is not None else '') +
            '<g ' + " ".join(wrapper) + '>' + image + "".join(overlays) + '</g>' +
            ('</g>' + edge["paint"] if edge is not None else '') + '</svg>\n')


def build(path: Path):
    data, mime, rgba, width, height, notes = source_image(path)
    source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    floor = DARK_FLOOR.get(path.stem, 0)
    if rgba is None:
        removed = None
        dark_removed = None
        wordmark_cleanup = None
        view = [0, 0, width, height]
        mode = "preserve-color"
        neutral = None
        gamma = False
        background = None
    else:
        rgb = rgba[:, :, :3].astype(np.float32)
        alpha = rgba[:, :, 3]
        luminance = rgb @ np.array([0.2126, 0.7152, 0.0722])
        chroma = np.ptp(rgb, axis=2)
        removed, background = background_mask(rgba)
        dark_removed, wordmark_cleanup = dark_wordmark_mask(path.stem, rgba, removed)
        visible = (alpha > 12) & ~removed
        ink = visible & (luminance < 235) if background != "dark" else visible & (luminance > 40)
        dark_ink = background == "dark"
        # A dark navy mark is still colored, and even a small published colored
        # star (USAAAO) is worth preserving instead of turning the whole mark gray.
        colored = ink & (chroma > 18)
        monochrome = path.stem in PALE_INK or int(colored.sum()) / max(int(ink.sum()), 1) < 0.015
        mode = "monochrome-light-ink" if monochrome and dark_ink else "monochrome-dark-ink" if monochrome else "preserve-color"
        if monochrome:
            visible &= luminance > 25 if dark_ink else luminance < 245
            notes.append(f"Dark display uses {INK} ink via an SVG luminance/alpha filter; source white holes and original transparency remain open.")
        neutral = None
        gamma = False
        if not monochrome:
            neutral_pixels = ink & (chroma <= 18) & (luminance < 180)
            if path.stem != "baupc" and neutral_pixels.sum() / max(ink.sum(), 1) > 0.05:
                coverage = np.clip((190 - luminance) / 190, 0, 1) * alpha / 255
                neutral = np.where(neutral_pixels, np.ceil(coverage * 16), 0).astype(np.uint8)
                mode = "preserve-color-light-neutral-ink"
                notes.append(f"Only neutral dark lettering/strokes receive a {INK} vector overlay for contrast; colored marks and enclosed white lettering are preserved.")
            colored_luminance = luminance[colored]
            gamma = DARK_GAMMA.get(path.stem, 0.72 if len(colored_luminance) and np.median(colored_luminance) < 100 else False)
            if gamma:
                notes.append(f"An SVG gamma lift ({gamma}, per RGB channel) improves dark colored ink visibility without hue inversion or a background plate.")
                if floor:
                    notes.append(f"A {floor:.2f} per-channel additive floor and {1-floor:.2f} amplitude raise pure blue/navy luminance in the reviewed dark UI; original alpha and white remain unchanged.")
        view = bounds(visible)
        if background:
            notes.append(f"Only edge-connected {background} background is removed by a vector mask; enclosed light areas are preserved.")
        if wordmark_cleanup:
            notes.append(f"In dark mode the reviewed flat-paper wordmark region x>={wordmark_cleanup['x']} also clears enclosed light-paper counters and gaps; {wordmark_cleanup['additionalPaperPixels']} additional paper pixels removed. Any illustrated emblem to its left keeps its original enclosed white artwork. Light mode is unchanged.")
        notes.append("Exterior transparent padding is cropped only with the SVG viewBox. Source asset bytes are unchanged.")
    dark = LOGO / "dark" / (path.stem + ".svg")
    light = LOGO / "light" / (path.stem + ".svg")
    edge = matte_edge_paint(path.stem, rgba, mode, gamma, floor) if rgba is not None else None
    if edge:
        notes.append(f"Reviewed white/color matte {edge['matte']} is unmixed from soft edge pixels using nearby solid ink and fractional SVG alpha; {edge['paintPixels']} corrected edge samples replace the contaminated paint. Closed white emblem faces and solid artwork are preserved.")
    dark.write_text(svg_variant(data, mime, width, height, view, dark_removed, mode, neutral, gamma, floor, edge), encoding="utf-8")
    # Keep a published dark field in light mode: white published lettering needs
    # that native background. This is not an added plate.
    light_removed = None if background == "dark" else removed
    light.write_text(svg_variant(data, mime, width, height, view, light_removed, "preserve-color"), encoding="utf-8")
    result = {"original": path.relative_to(ROOT).as_posix(), "light": light.relative_to(ROOT).as_posix(),
            "dark": dark.relative_to(ROOT).as_posix(), "sourceWidth": width, "sourceHeight": height,
            "viewBox": view, "aspectRatio": round(view[2] / view[3], 6), "mode": mode,
            "backgroundRemoved": background, "sourceSha256": source_sha, "notes": notes}
    if wordmark_cleanup:
        result["darkWordmarkPaperCleanup"] = wordmark_cleanup
    if edge:
        result["darkMatteCleanup"] = {field: edge[field] for field in ("matte", "pixels", "paintPixels")}
    return result


def main():
    (LOGO / "dark").mkdir(exist_ok=True)
    (LOGO / "light").mkdir(exist_ok=True)
    paths = sorted(path for path in LOGO.iterdir() if path.suffix.lower() in {".png", ".svg"})
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    entries = {path.stem: build(path) for path in paths}
    for path, digest in before.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, f"Source changed: {path}"
    manifest = {"version": 1, "generatedBy": "tools/build_logo_variants.py", "logos": entries}
    (LOGO / "variants.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    client = {key: {field: value[field] for field in ("original", "light", "dark", "aspectRatio")} for key, value in entries.items()}
    (LOGO / "variants.js").write_text("/* Generated by tools/build_logo_variants.py; source assets remain unchanged. */\nwindow.LOGO_VARIANTS=" + json.dumps(client, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    for key, entry in entries.items():
        for field in ("light", "dark"):
            checked_svg((ROOT / entry[field]).read_bytes())
        print(key, entry["mode"], "background=" + str(entry["backgroundRemoved"]), "viewBox=" + str(entry["viewBox"]))
    print(f"Generated {len(entries)} light and dark SVG variants; every source hash unchanged.")


if __name__ == "__main__":
    main()
