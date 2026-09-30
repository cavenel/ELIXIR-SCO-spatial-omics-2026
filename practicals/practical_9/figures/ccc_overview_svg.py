#!/usr/bin/env python
"""Generate an editable SVG schematic overview figure for the spatial
cell-cell communication (CCC) book chapter.

Writes ``ccc_overview.svg`` next to this script.  The SVG is plain markup
(presentation attributes, real <text> elements, one <g id="panel-X"> per
panel) so that it can be opened and edited in Illustrator / Inkscape.

Layout: panel A spans the full width; panels B-E sit on a 2x2 grid of
identically sized framed boxes with equal gutters.

Render a preview with e.g.::

    rsvg-convert -w 3200 ccc_overview.svg -o ccc_overview_preview.png
"""

from __future__ import annotations

import math
import os
import random

# --------------------------------------------------------------------------
# canvas / grid
# --------------------------------------------------------------------------
MARGIN = 32
GUTTER = 32
W = 1600
PW = (W - 2 * MARGIN - GUTTER) / 2.0          # panel width for B-E
AH = 330                                       # panel A height
PH = 516                                       # panel B-E height

ROW1_Y = MARGIN
ROW2_Y = ROW1_Y + AH + GUTTER
ROW3_Y = ROW2_Y + PH + GUTTER
H = int(ROW3_Y + PH + MARGIN)

COL1_X = MARGIN
COL2_X = MARGIN + PW + GUTTER

PANELS = {
    "A": (COL1_X, ROW1_Y, W - 2 * MARGIN, AH),
    "B": (COL1_X, ROW2_Y, PW, PH),
    "C": (COL2_X, ROW2_Y, PW, PH),
    "D": (COL1_X, ROW3_Y, PW, PH),
    "E": (COL2_X, ROW3_Y, PW, PH),
}
PAD = 22                                       # inner padding of a panel frame

FONT = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"

INK = "#1A1A1A"
GREY = "#7A7A7A"
FRAME = "#111111"
PANEL_STROKE = "#C9CED4"
PANEL_BG = "#FFFFFF"

# cartoon cell palette: light blue / dark slate blue / orange / neutral grey
CELLS = {
    "blue":  ("#9CC9E8", "#4E8FBF"),
    "slate": ("#3C5A73", "#1D3448"),
    "orange": ("#F3B24A", "#C9801B"),
    "grey":  ("#C3C8CE", "#8D949C"),
}
TISSUE_FILL = "#FBFCFD"
SOFT_BLUE = "#DCEAF6"
SOFT_ORANGE = "#FBE6C7"
SOFT_SLATE = "#C9D6E1"
ACCENT_RED = "#E03030"

out = []


def add(s: str) -> None:
    out.append(s)


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --------------------------------------------------------------------------
# text helpers (SVG has no auto wrapping -> do it ourselves)
# --------------------------------------------------------------------------
CHAR_W = 0.52           # mean advance width for Helvetica-like faces
TEXT_BOXES = []         # (panel, x0, y0, x1, y1, label)
SHAPE_BOXES = []        # (panel, x0, y0, x1, y1, label)
_current_panel = ["?"]


def text_width(t: str, size: float, weight: str = "normal") -> float:
    f = CHAR_W * (1.06 if weight == "bold" else 1.0)
    return len(t) * f * size


def wrap_lines(text: str, max_width: float, size: float, weight: str = "normal"):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if text_width(trial, size, weight) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _register(x, y, t, size, anchor, weight):
    w = text_width(t, size, weight)
    x0 = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
    TEXT_BOXES.append((_current_panel[0], x0, y - size * 0.78, x0 + w,
                       y + size * 0.22, t))


def shape(x0, y0, x1, y1, label):
    SHAPE_BOXES.append((_current_panel[0], min(x0, x1), min(y0, y1),
                        max(x0, x1), max(y0, y1), label))


def text(x, y, t, size=13, fill=INK, anchor="start", weight="normal",
         style="normal", opacity=None, register=True, extra=""):
    if register:
        _register(x, y, t, size, anchor, weight)
    op = f' opacity="{opacity}"' if opacity is not None else ""
    st = ' font-style="italic"' if style == "italic" else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}"{st} fill="{fill}" text-anchor="{anchor}"{op}{extra}>'
        f'{esc(t)}</text>')


def vtext(x, y, t, size=11, fill=INK, weight="normal"):
    """Text rotated -90 deg about (x, y), anchored middle; bbox registered."""
    w = text_width(t, size, weight)
    TEXT_BOXES.append((_current_panel[0], x - size * 0.78, y - w / 2,
                       x + size * 0.22, y + w / 2, t))
    text(x, y, t, size=size, fill=fill, anchor="middle", weight=weight,
         register=False, extra=f' transform="rotate(-90 {x:.1f} {y:.1f})"')


def para(x, y, t, max_width, size=12, fill=INK, anchor="start", weight="normal",
         style="normal", leading=1.22):
    """Wrapped multi-line text block; returns the y of the last baseline."""
    lines = wrap_lines(t, max_width, size, weight)
    for i, ln in enumerate(lines):
        text(x, y + i * size * leading, ln, size=size, fill=fill, anchor=anchor,
             weight=weight, style=style)
    return y + (len(lines) - 1) * size * leading


def method(x, y, t, max_width, anchor="start", size=11.5):
    """Short grey italic method label."""
    return para(x, y, t, max_width, size=size, fill=GREY, anchor=anchor,
                style="italic")


# --------------------------------------------------------------------------
# glyph helpers
# --------------------------------------------------------------------------
BLOB = ("M -8.5,3.6 C -10.6,-2.0 -6.2,-9.2 0.6,-9.6 C 7.2,-10.0 10.6,-4.4 9.6,1.1 "
        "C 8.6,6.6 3.6,9.7 -2.0,9.7 C -6.0,9.7 -7.6,7.0 -8.5,3.6 Z")


def blob(cx, cy, kind="blue", s=1.0, rot=0.0, halo=None):
    fill, nuc = CELLS[kind]
    g = [f'<g transform="translate({cx:.1f},{cy:.1f}) scale({s:.3f}) rotate({rot:.0f})">']
    g.append('<ellipse cx="1.5" cy="8.5" rx="8" ry="2.4" fill="#000000" opacity="0.10"/>')
    g.append(f'<path d="{BLOB}" fill="{fill}" stroke="#FFFFFF" stroke-width="0.8"/>')
    g.append(f'<ellipse cx="1.2" cy="-1.0" rx="3.6" ry="3.2" fill="{nuc}"/>')
    if halo:
        g.append(f'<ellipse cx="0" cy="0" rx="13" ry="13" fill="none" '
                 f'stroke="{halo}" stroke-width="1.6"/>')
    g.append('</g>')
    add("".join(g))


def rect(x, y, w, h, fill="none", stroke=None, sw=1.2, rx=0, opacity=None,
         dash=None, reg=None):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
        f'fill="{fill}"{s}{d}{o}/>')
    if reg:
        shape(x, y, x + w, y + h, reg)


def line(x1, y1, x2, y2, stroke=INK, sw=1.2, dash=None, opacity=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{sw}"{d}{o}/>')


def arrow(x1, y1, x2, y2, stroke=INK, sw=1.6, head=8.0, reg=None):
    """Straight arrow with an explicit polygon head (no <marker>: stays editable)."""
    ang = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - head * math.cos(ang), y2 - head * math.sin(ang)
    line(x1, y1, bx, by, stroke=stroke, sw=sw)
    px, py = -math.sin(ang), math.cos(ang)
    p1 = (bx + px * head * 0.42, by + py * head * 0.42)
    p2 = (bx - px * head * 0.42, by - py * head * 0.42)
    add(f'<polygon points="{x2:.1f},{y2:.1f} {p1[0]:.1f},{p1[1]:.1f} '
        f'{p2[0]:.1f},{p2[1]:.1f}" fill="{stroke}"/>')
    if reg:
        shape(min(x1, x2, bx), min(y1, y2, by), max(x1, x2, bx),
              max(y1, y2, by), reg)


def tri_up(x, y, s=6.0, fill=INK):
    add(f'<polygon points="{x:.1f},{y-s:.1f} {x-s*0.8:.1f},{y:.1f} '
        f'{x+s*0.8:.1f},{y:.1f}" fill="{fill}"/>')


def tissue_box(x, y, w, h, axes=True, fill=TISSUE_FILL, reg="tissue"):
    rect(x, y, w, h, fill=fill, stroke=FRAME, sw=1.6, reg=reg)
    if axes:
        ax, ay = x - 16, y + h + 14
        arrow(ax, ay, ax, ay - 34, sw=1.2, head=6)
        arrow(ax, ay, ax + 36, ay, sw=1.2, head=6)
        text(ax - 6, ay - 16, "Y", size=11, anchor="end", fill=INK)
        text(ax + 18, ay + 14, "X", size=11, anchor="middle", fill=INK)


def scatter_cells(rng, x, y, w, h, n=26, kinds=("blue", "slate", "orange", "grey"),
                  weights=(0.42, 0.24, 0.24, 0.10), s=0.95, pad=16, assign=None,
                  avoid=None):
    """Poisson-ish jittered grid of cells inside a box; returns (cx, cy, kind)."""
    placed = []
    tries = 0
    while len(placed) < n and tries < 6000:
        tries += 1
        cx = rng.uniform(x + pad, x + w - pad)
        cy = rng.uniform(y + pad, y + h - pad)
        if any((cx - a) ** 2 + (cy - b) ** 2 < (24 * s) ** 2 for a, b, _ in placed):
            continue
        if avoid and any(math.hypot(cx - ax, cy - ay) < ar for ax, ay, ar in avoid):
            continue
        kind = assign(cx, cy) if assign else rng.choices(kinds, weights)[0]
        placed.append((cx, cy, kind))
    for cx, cy, kind in placed:
        blob(cx, cy, kind, s=s, rot=rng.uniform(-25, 25))
    return placed


def panel_frame(key, title):
    x, y, w, h = PANELS[key]
    rect(x, y, w, h, fill="none", stroke=PANEL_STROKE, sw=1.2, rx=8)
    text(x + 20, y + 36, key, size=24, weight="bold", fill=INK)
    text(x + 54, y + 34, title, size=17, weight="bold", fill=INK)
    return x, y, w, h


def gradient(gid, c0, c1, o0=1.0, o1=1.0):
    add(f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="{c0}" stop-opacity="{o0}"/>'
        f'<stop offset="100%" stop-color="{c1}" stop-opacity="{o1}"/></linearGradient>')


# ==========================================================================
add('<?xml version="1.0" encoding="UTF-8"?>')
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" version="1.1">')
add('<defs>')
gradient("gBar", "#BFDDF1", "#D8DCE0")
gradient("gBarB", "#D8DCE0", "#9CC9E8")
gradient("gExpr", "#FFFFFF", "#111111")
gradient("gScore", "#E8EEF4", "#D94801")
add('<radialGradient id="gHot" cx="0.5" cy="0.5" r="0.5">'
    '<stop offset="0%" stop-color="#D94801" stop-opacity="0.55"/>'
    '<stop offset="45%" stop-color="#F08C3A" stop-opacity="0.30"/>'
    '<stop offset="100%" stop-color="#F7B27A" stop-opacity="0"/></radialGradient>')
add('</defs>')
rect(0, 0, W, H, fill=PANEL_BG)

# ==========================================================================
# PANEL A -- length scales
# ==========================================================================
_current_panel[0] = "A"
add('<g id="panel-A">')
AX, AY0, AW, AHH = panel_frame("A", "Length scales (µm)")

AX0, DEC = AX + 280, 350.0
AYA = AY0 + 68                                  # axis baseline


def apos(v):
    if v <= 0:
        return AX0
    if v < 10:
        return AX0 + DEC * (v / 10.0)
    return AX0 + DEC * (1.0 + math.log10(v / 10.0))


arrow(AX0, AYA, AX0 + 3.35 * DEC, AYA, sw=2.0, head=11)
for v, lab in [(0, "0"), (10, "10"), (100, "100"), (1000, "1000")]:
    x = apos(v)
    line(x, AYA, x, AYA + 11, sw=2.0)
    text(x, AYA - 11, lab, size=13, weight="bold", anchor="middle")

BARS = [
    ("Autocrine", [(0.0, 0.0, "", "gBar")], AY0 + 88),
    ("Juxtacrine", [(0.0, 20.0, "Direct contact", "gBar")], AY0 + 124),
    ("Paracrine", [(0.0, 50.0, "Short-range", "gBar"),
                   (50.0, 500.0, "Long-range", "gBarB")], AY0 + 160),
    ("Endocrine", [(1000.0, 3000.0, "", "gBarB")], AY0 + 224),
]
BH = 17
for name, segs, y in BARS:
    text(AX0 - 14, y + 13, name, size=15, anchor="end")
    for i, (a, b, lab, grad) in enumerate(segs):
        x0 = apos(a)
        x1 = max(apos(b), x0 + 16)
        if b > 1000:
            x1 = AX0 + 3.25 * DEC
        yy = y + i * 28
        rect(x0, yy, x1 - x0, BH, fill=f"url(#{grad})", rx=5)
        if lab:
            text((x0 + x1) / 2, yy + 12.5, lab, size=12, anchor="middle")

# markers below the bars
MY = AY0 + 274
for v, lab in [(20, None), (30, "30"), (100, "100"), (300, "300")]:
    x = apos(v)
    line(x, MY - 26, x, MY - 10, stroke=GREY, sw=1.0, dash="3 3")
    tri_up(x, MY, s=6.5, fill=INK if v == 20 else "#5B8FB9")
    if lab:
        text(x, MY + 16, lab, size=11.5, anchor="middle", fill="#5B8FB9")
text(apos(20) - 12, MY + 16, "contact cutoff", size=11.5, anchor="end")
text((apos(30) + apos(300)) / 2, MY + 32, "bandwidth (µm)", size=11.5,
     anchor="middle", fill=GREY, style="italic")
add('</g>')

# ==========================================================================
# PANEL B -- how CCC uses spatial information
# ==========================================================================
_current_panel[0] = "B"
RB = random.Random(11)
add('<g id="panel-B">')
BX0, BY0, BWP, BHP = panel_frame(
    "B", "Cell-cell communication uses spatial information by…")

SBW, SBH = 324, 140                 # sub-diagram box size
CLX = BX0 + 46                      # left sub-column x
CRX = BX0 + 46 + SBW + 32           # right sub-column x

# ---- i) fixed distance --------------------------------------------------
text(CLX - 16, BY0 + 72, "i) fixed distance", size=14.5, weight="bold")

R1Y = BY0 + 102
text(CLX + SBW / 2, R1Y - 10, "regions / microenvironments", size=11.5,
     anchor="middle")
text(CRX + SBW / 2, R1Y - 10, "view-specific neighbourhoods", size=11.5,
     anchor="middle")

# B1: regions / microenvironments
add(f'<clipPath id="clipB1"><rect x="{CLX}" y="{R1Y}" width="{SBW}" '
    f'height="{SBH}"/></clipPath>')
add('<g clip-path="url(#clipB1)">')
rect(CLX, R1Y, SBW, SBH, fill=SOFT_BLUE)
add(f'<path d="M {CLX},{R1Y+66} C {CLX+78},{R1Y+58} {CLX+106},{R1Y+96} '
    f'{CLX+132},{R1Y+SBH} L {CLX},{R1Y+SBH} Z" fill="{SOFT_ORANGE}"/>')
add(f'<path d="M {CLX+132},{R1Y+SBH} C {CLX+156},{R1Y+78} {CLX+212},{R1Y+60} '
    f'{CLX+SBW},{R1Y+52} L {CLX+SBW},{R1Y+SBH} Z" fill="{SOFT_SLATE}"/>')


def b1_assign(cx, cy):
    if cy > R1Y + 68 and cx < CLX + 130:
        return "orange"
    if cy > R1Y + 58 + (cx - CLX - 130) * -0.05 and cx >= CLX + 130:
        return "slate"
    return "blue" if RB.random() < 0.85 else "grey"


scatter_cells(RB, CLX, R1Y, SBW, SBH, n=23, s=0.86, assign=b1_assign, pad=13)
add('</g>')
tissue_box(CLX, R1Y, SBW, SBH, axes=True, fill="none")
method(CLX, R1Y + SBH + 42, "hard mask: CellPhoneDB microenvironments", SBW)

# B2: view-specific neighbourhoods
tissue_box(CRX, R1Y, SBW, SBH, axes=False)
rect(CRX + 30, R1Y + 20, SBW - 60, SBH - 38, stroke="#9AA2AA", sw=1.0, dash="4 4")
add(f'<clipPath id="clipB2"><rect x="{CRX}" y="{R1Y}" width="{SBW}" '
    f'height="{SBH}"/></clipPath>')
add('<g clip-path="url(#clipB2)">')
scatter_cells(RB, CRX, R1Y, SBW, SBH, n=19, s=0.84, pad=13,
              avoid=[(CRX + SBW / 2, R1Y + SBH / 2, 46),
                     (CRX + 38, R1Y + 12, 34)])
add('</g>')
fx, fy = CRX + SBW / 2, R1Y + SBH / 2
add(f'<circle cx="{fx}" cy="{fy}" r="36" fill="none" stroke="{ACCENT_RED}" '
    f'stroke-width="2"/>')
blob(fx, fy, "blue", s=0.95, halo=ACCENT_RED)
text(CRX + 4, R1Y + 15, "wider view", size=10.5, fill="#6E767E")
method(CRX, R1Y + SBH + 42, "contact graphs: kNN, radius, Delaunay", SBW)

# ---- ii) interaction decays ---------------------------------------------
text(CLX - 16, BY0 + 320, "ii) interaction decays", size=14.5, weight="bold")

R2Y = BY0 + 338

# B3: decaying kernel over the tissue
tissue_box(CLX, R2Y, SBW, SBH, axes=False)
add(f'<clipPath id="clipB3"><rect x="{CLX}" y="{R2Y}" width="{SBW}" '
    f'height="{SBH}"/></clipPath>')
add('<g clip-path="url(#clipB3)">')
scatter_cells(RB, CLX, R2Y, SBW, SBH, n=19, s=0.84, pad=12)
gx, gy = CLX + SBW / 2, R2Y + SBH / 2
for r, op in [(76, 0.10), (56, 0.18), (36, 0.30), (18, 0.46)]:
    add(f'<circle cx="{gx}" cy="{gy}" r="{r}" fill="#4F5B66" opacity="{op}"/>')
for r in (18, 36, 56, 76):
    add(f'<circle cx="{gx}" cy="{gy}" r="{r}" fill="none" stroke="#FFFFFF" '
        f'stroke-width="0.9" opacity="0.8"/>')
add('</g>')
blob(gx, gy, "blue", s=0.95, halo=ACCENT_RED)
method(CLX, R2Y + SBH + 26, "kernel weights → spatial graph", SBW)

# kernel curve w(d)
KX, KY, KW, KH = CRX + 34, R2Y + 4, 250, 58
line(KX, KY + KH, KX + KW, KY + KH, sw=1.2)
line(KX, KY + KH, KX, KY, sw=1.2)
bw = 0.34
pts = []
for i in range(61):
    t = i / 60.0
    pts.append(f"{KX + t*KW:.1f},{KY + KH - math.exp(-(t/bw)**2)*(KH-8):.1f}")
add(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#2C6EA8" stroke-width="2"/>')
line(KX + bw * KW, KY + KH, KX + bw * KW, KY + KH - math.exp(-1) * (KH - 8),
     stroke=GREY, sw=1.0, dash="3 3")
text(KX + bw * KW + 5, KY + 14, "bandwidth", size=10.5, fill=GREY)
text(KX - 6, KY + 11, "w(d)", size=11, anchor="end")
text(KX + KW, KY + KH + 13, "d", size=11, anchor="end")

# g(r) curve
GX, GY, GW, GH = CRX + 34, R2Y + 88, 250, 52
line(GX, GY + GH, GX + GW, GY + GH, sw=1.2)
line(GX, GY + GH, GX, GY, sw=1.2)
base = GY + GH - 10
line(GX, base, GX + GW, base, stroke=GREY, sw=1.0, dash="3 3")
text(GX + GW + 4, base + 4, "1", size=10.5, fill=GREY)
pts = []
for i in range(61):
    t = i / 60.0
    val = 1.0 + 1.25 * math.exp(-((t - 0.22) / 0.20) ** 2)
    pts.append(f"{GX + t*GW:.1f},{base - (val-1)*(GH-16):.1f}")
add(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#B4441F" stroke-width="2"/>')
text(GX - 6, GY + 11, "g(r)", size=11, anchor="end")
text(GX + GW, GY + GH + 13, "r", size=11, anchor="end")
method(GX - 34, R2Y + SBH + 26, "rings → cross-PCF g(r)", SBW)
add('</g>')

# ==========================================================================
# PANEL C -- what is scored
# ==========================================================================
_current_panel[0] = "C"
RC = random.Random(23)
add('<g id="panel-C">')
CX0, CY0, CWP, CHP = panel_frame(
    "C", "What is scored: cell(-type)-wise vs gene-wise")

CT_COL = {"A": "#9CC9E8", "B": "#3C5A73", "C": "#F3B24A"}
CT_INK = {"A": "#2C6EA8", "B": "#1D3448", "C": "#C9801B"}
TKS = ["A", "B", "C"]

MX0, MY0, CELL = CX0 + 80, CY0 + 110, 32
NG, NC = 8, 6
MW, MH = NG * CELL, NC * CELL
ROW_KIND = ["blue", "blue", "slate", "slate", "orange", "blue"]

# ligand-receptor bracket over g2 and g5
c2 = MX0 + 1.5 * CELL
c5 = MX0 + 4.5 * CELL
by = MY0 - 36
add(f'<path d="M {c2},{by+10} L {c2},{by} L {c5},{by} L {c5},{by+10}" fill="none" '
    f'stroke="#6E767E" stroke-width="1.2"/>')
text((c2 + c5) / 2, by - 7, "ligand–receptor database", size=12, anchor="middle",
     fill="#4A4A4A")

for j in range(NG):
    text(MX0 + (j + 0.5) * CELL, MY0 - 8, f"g{j+1}", size=12, anchor="middle")
for i in range(NC):
    blob(MX0 - 22, MY0 + (i + 0.5) * CELL, ROW_KIND[i], s=0.78)
    for j in range(NG):
        v = RC.random()
        g = int(255 * (1 - 0.86 * v ** 1.05))
        add(f'<rect x="{MX0 + j*CELL}" y="{MY0 + i*CELL}" width="{CELL}" '
            f'height="{CELL}" fill="rgb({g},{g},{g})" stroke="#FFFFFF" stroke-width="0.8"/>')
shape(MX0 - 32, MY0, MX0 + MW, MY0 + MH, "expr matrix")
rect(MX0 + 1 * CELL, MY0, CELL, MH, stroke="#2C6EA8", sw=2.4)
rect(MX0 + 4 * CELL, MY0, CELL, MH, stroke="#D97706", sw=2.4)
MBOT = MY0 + MH

# expression colourbar
rect(MX0, MBOT + 16, 140, 12, fill="url(#gExpr)", stroke="#9AA2AA", sw=0.8,
     reg="expr bar")
text(MX0 + 150, MBOT + 26, "expression", size=12)

# compact 3-column table below the colourbar
TBX, TBY = MX0 - 24, MBOT + 74
TCOL = [TBX + 44, TBX + 148, TBX + 240]
TROWS = [("x1, y1", "A", "1.0"), ("x2, y2", "A", "0.8"),
         ("x3, y3", "B", "0.7"), ("x5, y5", "C", "0.3")]
for cx, head in zip(TCOL, ["X, Y", "cell type", "weight"]):
    text(cx, TBY, head, size=12.5, weight="bold", anchor="middle")
line(TBX, TBY + 9, TBX + 280, TBY + 9, stroke="#C9CED4", sw=1.0)
for i, (xy, ct, wt) in enumerate(TROWS):
    yy = TBY + 31 + i * 23
    text(TCOL[0], yy, xy, size=12, anchor="middle", fill=CT_INK[ct])
    text(TCOL[1], yy, ct, size=12, anchor="middle", weight="bold", fill=CT_INK[ct])
    text(TCOL[2], yy, wt, size=12, anchor="middle", fill="#4A4A4A")
line(TBX, TBY + 112, TBX + 280, TBY + 112, stroke="#E2E6EA", sw=1.0)

# ---- outputs on the right, fed by arrows from the matrix -----------------
# 3x3 cell-type x cell-type heatmap
HC = 50
HX, HY = CX0 + 480, CY0 + 110
HV = [[0.25, 0.85, 0.15], [0.45, 0.30, 0.70], [0.10, 0.55, 0.35]]
arrow(MX0 + MW + 12, MY0 + 60, HX - 56, HY + 52, sw=1.8, reg="arrow1")
for i in range(3):
    for j in range(3):
        v = HV[i][j]
        r = int(255 - 180 * v)
        g = int(255 - 120 * v)
        b = int(255 - 40 * v)
        add(f'<rect x="{HX + j*HC}" y="{HY + i*HC}" width="{HC}" height="{HC}" '
            f'fill="rgb({r},{g},{b})" stroke="#FFFFFF" stroke-width="1"/>')
rect(HX, HY, 3 * HC, 3 * HC, stroke=FRAME, sw=1.0, reg="ct heatmap")
for k, t in enumerate(TKS):
    rect(HX + k * HC + 15, HY - 17, 20, 10, fill=CT_COL[t], stroke="#FFFFFF", sw=0.6,
         rx=2, reg="swatch")
    rect(HX - 17, HY + k * HC + 15, 10, 20, fill=CT_COL[t], stroke="#FFFFFF", sw=0.6,
         rx=2, reg="swatch")
text(HX + 1.5 * HC, HY - 27, "receiver cell type", size=11.5, anchor="middle",
     fill="#4A4A4A")
vtext(HX - 38, HY + 1.5 * HC, "sender cell type", size=11.5, fill="#4A4A4A")
method(HX - 22, HY + 3 * HC + 28, "cell-type-wise: NEA, CellPhoneDB", 260)

# ligand vs receptor scatter
SX, SY, SW2, SH2 = CX0 + 480, CY0 + 306, 210, 150
arrow(MX0 + MW + 12, MY0 + 138, SX - 52, SY + 52, sw=1.8, reg="arrow2")
rect(SX, SY, SW2, SH2, fill="#FFFFFF", stroke=FRAME, sw=1.2, reg="lr scatter")
for _ in range(40):
    a = RC.random()
    px = SX + 12 + a * (SW2 - 26) + RC.gauss(0, 9)
    py = SY + SH2 - 12 - (0.85 * a + RC.gauss(0, 0.13)) * (SH2 - 26)
    px = min(max(px, SX + 6), SX + SW2 - 6)
    py = min(max(py, SY + 6), SY + SH2 - 6)
    add(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.6" fill="#4E8FBF" opacity="0.75"/>')
line(SX + 10, SY + SH2 - 10, SX + SW2 - 12, SY + 26, stroke=ACCENT_RED, sw=1.8)
text(SX + SW2 / 2, SY + SH2 + 18, "ligand", size=11.5, anchor="middle", fill="#4A4A4A")
vtext(SX - 16, SY + SH2 / 2, "receptor", size=11.5, fill="#4A4A4A")
method(SX - 22, SY + SH2 + 42, "gene-wise: bivariate Moran's I", 260)
add('</g>')

# ==========================================================================
# PANEL D -- global vs local
# ==========================================================================
_current_panel[0] = "D"
RD = random.Random(37)
add('<g id="panel-D">')
DX0, DY0, DWP, DHP = panel_frame("D", "Global vs local")

BOXW, BOXH = 380, 180
GBX, GBY = DX0 + 48, DY0 + 92

# ---- global (top) -------------------------------------------------------
text(GBX, GBY - 12, "global", size=14, weight="bold", fill="#4A4A4A")
tissue_box(GBX, GBY, BOXW, BOXH, axes=False)
add(f'<clipPath id="clipD1"><rect x="{GBX}" y="{GBY}" width="{BOXW}" '
    f'height="{BOXH}"/></clipPath>')
add('<g clip-path="url(#clipD1)">')
scatter_cells(RD, GBX, GBY, BOXW, BOXH, n=24, s=0.95, pad=16)
add('</g>')

TC = 54
TX, TY = DX0 + 544, GBY + (BOXH - 3 * TC) / 2
arrow(GBX + BOXW + 14, GBY + BOXH / 2, TX - 66, GBY + BOXH / 2, sw=2.2, head=10,
      reg="d arrow")
GV = [[0.20, 0.75, 0.15], [0.35, 0.25, 0.10], [0.10, 0.30, 0.20]]
for i in range(3):
    for j in range(3):
        v = GV[i][j]
        r = int(255 - 180 * v)
        g = int(255 - 120 * v)
        b = int(255 - 40 * v)
        add(f'<rect x="{TX + j*TC}" y="{TY + i*TC}" width="{TC}" height="{TC}" '
            f'fill="rgb({r},{g},{b})" stroke="#FFFFFF" stroke-width="1"/>')
rect(TX, TY, 3 * TC, 3 * TC, stroke=FRAME, sw=1.0, reg="global heatmap")
rect(TX + TC, TY, TC, TC, stroke=ACCENT_RED, sw=2.2)
text(TX + 1.5 * TC, TY + 3 * TC + 22, "0.42", size=13, weight="bold",
     anchor="middle", fill="#B4441F")
for k, t in enumerate(TKS):
    rect(TX + k * TC + 16, TY - 17, 22, 10, fill=CT_COL[t], stroke="#FFFFFF", sw=0.6,
         rx=2, reg="swatch")
    rect(TX - 17, TY + k * TC + 17, 10, 22, fill=CT_COL[t], stroke="#FFFFFF", sw=0.6,
         rx=2, reg="swatch")
text(TX + 1.5 * TC, TY - 27, "receiver", size=11.5, anchor="middle", fill="#4A4A4A")
vtext(TX - 40, TY + 1.5 * TC, "sender", size=11.5, fill="#4A4A4A")
method(GBX, GBY + BOXH + 32, "global: NEA, CellPhoneDB, global Moran's I", 420)

# ---- local (bottom): circular hotspot with a radial gradient -------------
LBW, LBH = 380, 148
LBX, LBY = GBX, DY0 + 348
text(LBX, LBY - 12, "local", size=14, weight="bold", fill="#4A4A4A")
add(f'<clipPath id="clipD2"><rect x="{LBX}" y="{LBY}" width="{LBW}" '
    f'height="{LBH}"/></clipPath>')
add('<g clip-path="url(#clipD2)">')
add(f'<rect x="{LBX}" y="{LBY}" width="{LBW}" height="{LBH}" fill="#FAFBFC"/>')

HOTX, HOTY, HOTR = LBX + 126, LBY + 72, 68
add(f'<circle cx="{HOTX:.1f}" cy="{HOTY:.1f}" r="{HOTR}" fill="url(#gHot)"/>')

placed = []
tries = 0
while len(placed) < 34 and tries < 9000:
    tries += 1
    cx = RD.uniform(LBX + 14, LBX + LBW - 14)
    cy = RD.uniform(LBY + 14, LBY + LBH - 14)
    if any((cx - a) ** 2 + (cy - b) ** 2 < 25 ** 2 for a, b in placed):
        continue
    placed.append((cx, cy))

n_in = 0
for cx, cy in placed:
    dist = math.hypot(cx - HOTX, cy - HOTY)
    add('<ellipse cx="%.1f" cy="%.1f" rx="8.5" ry="2.5" fill="#000000" opacity="0.08"/>'
        % (cx, cy + 8))
    if dist <= HOTR:
        n_in += 1
        v = math.exp(-(dist / (0.62 * HOTR)) ** 2)
        r = int(232 - 15 * v)
        g = int(238 - 166 * v)
        b = int(244 - 243 * v)
        fill = f"rgb({r},{g},{b})"
        nuc = f"rgb({max(r-60,0)},{max(g-60,0)},{max(b-30,0)})"
    else:
        fill, nuc = CELLS["grey"]
    add(f'<g transform="translate({cx:.1f},{cy:.1f}) scale(0.92)">'
        f'<path d="{BLOB}" fill="{fill}" stroke="#FFFFFF" stroke-width="0.8"/>'
        f'<ellipse cx="1.2" cy="-1.0" rx="3.4" ry="3.0" fill="{nuc}"/></g>')
add(f'<circle cx="{HOTX:.1f}" cy="{HOTY:.1f}" r="{HOTR}" fill="none" '
    f'stroke="#B4441F" stroke-width="1.4" stroke-dasharray="6 4" opacity="0.85"/>')
add('</g>')
rect(LBX, LBY, LBW, LBH, stroke=FRAME, sw=1.6, reg="local tissue")

# score legend to the right of the local tissue box
CBX, CBY = DX0 + 500, LBY + 58
text(CBX, CBY - 10, "local score", size=12)
rect(CBX, CBY, 170, 13, fill="url(#gScore)", stroke="#9AA2AA", sw=0.8,
     reg="score bar")
method(CBX, CBY + 44, "local: inflow", 200)
add('</g>')

# ==========================================================================
# PANEL E -- many scales at once
# ==========================================================================
_current_panel[0] = "E"
RE = random.Random(59)
add('<g id="panel-E">')
EX0, EY0, EWP, EHP = panel_frame("E", "Many scales at once")

WW, WH = 520, 370
WX, WY = EX0 + 66, EY0 + 68
FX, FY = WX + 255, WY + 185
R_JUX, R_PAR = 60, 140
LBLX = WX + WW + 30

LEAD = [
    ((FX + 43, FY - 43), (LBLX, WY + 82), "juxtacrine", "#B4441F"),
    ((FX + 99, FY + 99), (LBLX, WY + 236), "paracrine", "#2C6EA8"),
    ((WX + WW - 14, WY + WH - 20), (LBLX, WY + 340), "global", "#4A4A4A"),
]

rect(WX, WY, WW, WH, fill=TISSUE_FILL, stroke=FRAME, sw=1.8, reg="e window")
add(f'<clipPath id="clipE"><rect x="{WX}" y="{WY}" width="{WW}" '
    f'height="{WH}"/></clipPath>')
add('<g clip-path="url(#clipE)">')


def _seg_dist(px, py, x1, y1, x2, y2):
    vx, vy = x2 - x1, y2 - y1
    t = max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / (vx * vx + vy * vy)))
    return math.hypot(px - (x1 + t * vx), py - (y1 + t * vy))


ecells, tries = [], 0
while len(ecells) < 30 and tries < 12000:
    tries += 1
    cx = RE.uniform(WX + 20, WX + WW - 20)
    cy = RE.uniform(WY + 20, WY + WH - 20)
    if math.hypot(cx - FX, cy - FY) < 34:
        continue
    if any((cx - a) ** 2 + (cy - b) ** 2 < 42 ** 2 for a, b, _ in ecells):
        continue
    if any(_seg_dist(cx, cy, p[0], p[1], q[0], q[1]) < 18 for p, q, _, _ in LEAD):
        continue
    if any(abs(math.hypot(cx - FX, cy - FY) - r) < 13 for r in (R_JUX, R_PAR)):
        continue
    ecells.append((cx, cy, RE.choices(["blue", "slate", "orange", "grey"],
                                      [0.4, 0.25, 0.25, 0.10])[0]))
for cx, cy, kind in ecells:
    blob(cx, cy, kind, s=1.0, rot=RE.uniform(-25, 25))
add('</g>')

add(f'<circle cx="{FX}" cy="{FY}" r="{R_PAR}" fill="#2C6EA8" opacity="0.07"/>')
add(f'<circle cx="{FX}" cy="{FY}" r="{R_PAR}" fill="none" stroke="#2C6EA8" '
    f'stroke-width="2.2" stroke-dasharray="8 6"/>')
add(f'<circle cx="{FX}" cy="{FY}" r="{R_JUX}" fill="#B4441F" opacity="0.08"/>')
add(f'<circle cx="{FX}" cy="{FY}" r="{R_JUX}" fill="none" stroke="#B4441F" '
    f'stroke-width="2.2"/>')
blob(FX, FY, "blue", s=1.2)

for (p, q, label, col) in LEAD:
    line(p[0], p[1], q[0] - 6, q[1], stroke="#8A9098", sw=1.0)
    add(f'<circle cx="{p[0]}" cy="{p[1]}" r="2.8" fill="#8A9098"/>')
    text(q[0], q[1] + 4, label, size=13, fill=col)

method(WX, WY + WH + 30, "multi-scale models: InterScale", 340)
add('</g>')

add('</svg>')

# --------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(HERE, "ccc_overview.svg")
with open(path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print("wrote", path, f"viewBox 0 0 {W} {H}")


# --------------------------------------------------------------------------
# geometry checks
# --------------------------------------------------------------------------
def _ovl(a, b, slack=1.0):
    return (a[1] < b[3] - slack and b[1] < a[3] - slack
            and a[2] < b[4] - slack and b[2] < a[4] - slack)


clashes = 0
for i in range(len(TEXT_BOXES)):
    a = TEXT_BOXES[i]
    for j in range(i + 1, len(TEXT_BOXES)):
        b = TEXT_BOXES[j]
        if a[0] != b[0]:
            continue
        if _ovl(a, b):
            clashes += 1
            print(f"  TEXT/TEXT [{a[0]}] {a[5]!r} <-> {b[5]!r}")

for a in TEXT_BOXES:
    for b in SHAPE_BOXES:
        if a[0] != b[0]:
            continue
        if b[5] in ("tissue", "e window") and (a[1] >= b[1] and a[3] <= b[3]
                                                 and a[2] >= b[2] and a[4] <= b[4]):
            continue
        if _ovl(a, b, slack=1.5):
            clashes += 1
            print(f"  TEXT/SHAPE [{a[0]}] {a[5]!r} <-> {b[5]!r}")

# containment: every text must sit inside its own panel frame
for p, x0, y0, x1, y1, t in TEXT_BOXES:
    if p not in PANELS:
        continue
    px, py, pw, ph = PANELS[p]
    if x0 < px + 2 or x1 > px + pw - 2 or y0 < py + 2 or y1 > py + ph - 2:
        clashes += 1
        print(f"  OUTSIDE [{p}] {t!r} box=({x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}) "
              f"panel=({px:.0f},{py:.0f},{px+pw:.0f},{py+ph:.0f})")
for p, x0, y0, x1, y1, t in SHAPE_BOXES:
    if p not in PANELS:
        continue
    px, py, pw, ph = PANELS[p]
    if x0 < px + 2 or x1 > px + pw - 2 or y0 < py + 2 or y1 > py + ph - 2:
        clashes += 1
        print(f"  SHAPE OUTSIDE [{p}] {t!r} box=({x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f})")

print("panel D hotspot: %d of %d cells inside" % (n_in, len(placed)))
print("collisions:", clashes)
