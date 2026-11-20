#!/usr/bin/env python3
"""Render every screen and report wireframe as one Figma-importable SVG.

Each wireframe is a named group on a shared canvas, built from plain rect, text,
line, circle and path primitives, so Figma imports editable layers. Drag the SVG
onto a Figma canvas, or use File > Place image.

Usage: python3 build_figma_svg.py --input kit-spec.json --output figma-wireframes.svg
Exit 0: output written. Exit 1: every spec problem printed to stderr.
"""
import kit_common as kc
import kit_svg as ks

DEFAULT_OUTPUT_NAME = "figma-wireframes.svg"
COLS = 2
MARGIN = 80
GUTTER = 80


def build(spec, out_path):
    th = kc.theme_of(spec)
    lane_names = {l["id"]: l["name"] for l in spec["lanes"]}
    items = [("Screen", s, lane_names[s["lane"]]) for s in spec["screens"]]
    items += [("Report", ks.report_as_screen(r, spec), lane_names[r["lane"]]) for r in spec["reports"]]
    frames = []
    for kind, sc, lane in items:
        svg, w, h = ks.screen_frame(sc, th, lane, th["brand_name"])
        frames.append((kind, sc, svg, w, h))
    rows = [frames[i:i + COLS] for i in range(0, len(frames), COLS)]
    y = MARGIN + 100
    parts = [ks.T(MARGIN, MARGIN + 20, "%s: wireframes" % spec["meta"]["title"], 30, th["text"], "700"),
             ks.T(MARGIN, MARGIN + 46, "Look and feel: %s" % th["source"], 14, th["muted"])]
    for row in rows:
        x = MARGIN
        rh = 0
        for kind, sc, svg, w, h in row:
            label = "%s %s - %s" % (kind, sc["id"], sc["title"])
            parts.append(ks.T(x, y - 12, label, 16, th["text"], "700"))
            parts.append(ks.G(svg, label, x, y))
            x += w + GUTTER
            rh = max(rh, h)
        y += rh + GUTTER + 30
    width = MARGIN * 2 + COLS * ks.FRAME_W + (COLS - 1) * GUTTER
    height = y + MARGIN
    doc = ('<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="%s">'
           '<rect width="%d" height="%d" fill="#ececec"/>%s</svg>' % (width, height, width, height, kc.esc(th["font_figma"] + ", Arial, Helvetica, sans-serif"), width, height, "".join(parts)))
    out_path.write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(kc.run(build))
