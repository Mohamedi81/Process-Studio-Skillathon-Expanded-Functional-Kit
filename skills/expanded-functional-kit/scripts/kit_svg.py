#!/usr/bin/env python3
"""SVG layout engine for wireframes (helper module, not an entry script).

Draws every wireframe component as plain SVG primitives (rect, text, line,
circle, path, g). Figma imports these as editable layers. The same chart
functions are reused by the HTML renderer.
"""
import math

from kit_common import cell, esc, shade, tint, tone_color, zone_tone

FRAME_W = 1280
TOP_H = 56
SIDE_W = 220
PAD = 24
GAP = 16
CONTENT_W = FRAME_W - SIDE_W - 2 * PAD  # 1012


# --------------------------------------------------------------- primitives
def R(x, y, w, h, fill="none", stroke=None, rx=0, sw=1):
    s = ' stroke="%s" stroke-width="%s"' % (stroke, sw) if stroke else ""
    return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%s" fill="%s"%s/>' % (x, y, w, h, rx, fill, s)


def T(x, y, s, size=13, fill="#161616", weight="400", anchor="start", font=None):
    return ('<text x="%.1f" y="%.1f" font-size="%s" font-weight="%s" fill="%s" text-anchor="%s"%s>%s</text>'
            % (x, y, size, weight, fill, anchor, ' font-family="%s"' % esc(font) if font else "", esc(s)))


def L(x1, y1, x2, y2, stroke="#e0e0e0", sw=1, dash=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"%s/>' % (x1, y1, x2, y2, stroke, sw, d)


def G(inner, gid=None, tx=0, ty=0):
    i = ' id="%s"' % esc(gid) if gid else ""
    t = ' transform="translate(%.1f %.1f)"' % (tx, ty) if (tx or ty) else ""
    return "<g%s%s>%s</g>" % (i, t, inner)


def wrap(text, width_px, size=13):
    """Greedy word wrap using an average glyph width of 0.53 em."""
    cpl = max(8, int(width_px / (size * 0.53)))
    lines, cur = [], ""
    for word in str(text).split():
        if len(cur) + len(word) + (1 if cur else 0) <= cpl:
            cur = (cur + " " + word).strip()
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def clip(s, width_px, size=12):
    cpl = max(3, int(width_px / (size * 0.53)))
    s = str(s)
    return s if len(s) <= cpl else s[: cpl - 1] + "..."


def pill(x, y, text, color, size=11, anchor="start"):
    w = max(34, len(text) * size * 0.58 + 16)
    if anchor == "end":
        x = x - w
    return R(x, y, w, 20, tint(color, 0.85), tint(color, 0.45), 10) + \
        T(x + w / 2, y + 14, text, size, shade(color, 0.35), "600", "middle"), w


def button(x, y, label, style, th, size=13):
    w = max(80, len(label) * size * 0.6 + 28)
    if style == "primary":
        return R(x, y, w, 34, th["primary"], None, th["radius"]) + T(x + w / 2, y + 22, label, size, "#ffffff", "600", "middle"), w
    if style == "danger":
        return R(x, y, w, 34, th["danger"], None, th["radius"]) + T(x + w / 2, y + 22, label, size, "#ffffff", "600", "middle"), w
    return R(x, y, w, 34, th["surface"], th["primary"], th["radius"]) + T(x + w / 2, y + 22, label, size, th["primary"], "600", "middle"), w


def norm_actions(items):
    out = []
    n = len(items)
    for i, a in enumerate(items):
        if isinstance(a, dict):
            out.append((a.get("label", ""), a.get("style") or ("primary" if i == n - 1 else "secondary")))
        else:
            out.append((str(a), "primary" if i == n - 1 else "secondary"))
    return out


# ------------------------------------------------------------- components
def d_banner(c, w, th):
    tone = c.get("tone", "blue")
    col = tone_color(th, tone)
    return R(0, 0, w, 44, tint(col, 0.88), tint(col, 0.5), th["radius"]) + R(0, 0, 5, 44, col, None, 2) + \
        T(18, 27, clip(c["text"], w - 36, 13), 13, th["text"]), 44


def d_stepper(c, w, th):
    items = c["items"]
    active = c.get("active", 0)
    n = len(items)
    step = w / n
    out = []
    for i, it in enumerate(items):
        label = it if isinstance(it, str) else it.get("label", "")
        cx = step * i + step / 2
        if i > 0:
            out.append(L(step * (i - 1) + step / 2 + 14, 16, cx - 14, 16, th["primary"] if i <= active else th["border"], 2))
        col = th["success"] if i < active else th["primary"] if i == active else th["border"]
        out.append('<circle cx="%.1f" cy="16" r="12" fill="%s"/>' % (cx, col if i <= active else th["surface"]))
        if i > active:
            out.append('<circle cx="%.1f" cy="16" r="12" fill="none" stroke="%s" stroke-width="2"/>' % (cx, th["border"]))
        out.append(T(cx, 20.5, str(i + 1), 12, "#ffffff" if i <= active else th["muted"], "700", "middle"))
        out.append(T(cx, 48, clip(label, step - 8, 11), 11, th["text"] if i <= active else th["muted"], "600" if i == active else "400", "middle"))
    return "".join(out), 56


def d_tabs(c, w, th):
    out = [L(0, 35, w, 35, th["border"])]
    x = 0
    for i, t in enumerate(c["items"]):
        label = t if isinstance(t, str) else t.get("label", "")
        tw = len(label) * 7.4 + 32
        act = i == c.get("active", 0)
        out.append(T(x + tw / 2, 22, label, 13, th["primary"] if act else th["muted"], "600" if act else "400", "middle"))
        if act:
            out.append(R(x, 32, tw, 3, th["primary"]))
        x += tw
    return "".join(out), 36


def d_kpis(c, w, th):
    items = c["items"]
    n = len(items)
    cw = (w - 12 * (n - 1)) / n
    out = []
    for i, k in enumerate(items):
        x = i * (cw + 12)
        col = tone_color(th, k.get("tone", "blue"))
        out.append(R(x, 0, cw, 84, th["surface"], th["border"], th["radius"]))
        out.append(R(x, 0, cw, 4, col, None, 2))
        out.append(T(x + 14, 28, clip(k.get("label", ""), cw - 28, 11), 11, th["muted"], "600"))
        out.append(T(x + 14, 58, clip(k.get("value", ""), cw - 28, 26), 26, th["text"], "700"))
        if k.get("delta"):
            out.append(T(x + 14, 76, clip(k["delta"], cw - 28, 11), 11, col, "600"))
    return "".join(out), 84


def d_table(c, w, th):
    hdr, rows = c["headers"], c["rows"]
    n = len(hdr)
    cw = w / n
    rh = 32
    out = [R(0, 0, w, 34 + rh * len(rows), th["surface"], th["border"], th["radius"]),
           R(0, 0, w, 34, tint(th["primary"], 0.92), None, th["radius"])]
    for i, h in enumerate(hdr):
        out.append(T(12 + i * cw, 22, clip(h, cw - 16, 11), 11, th["muted"], "700"))
    for r, row in enumerate(rows):
        y = 34 + r * rh
        out.append(L(0, y, w, y, th["border"]))
        for i, raw in enumerate(row):
            txt, tone = cell(raw)
            x = 12 + i * cw
            if tone:
                p, _ = pill(x, y + 6, clip(txt, cw - 30, 11), tone_color(th, tone))
                out.append(p)
            else:
                out.append(T(x, y + 21, clip(txt, cw - 16, 12), 12, th["text"]))
    return "".join(out), 34 + rh * len(rows)


def d_filters(c, w, th):
    out, x = [], 0
    for it in c["items"]:
        label = it if isinstance(it, str) else it.get("label", "")
        bw = max(110, len(label) * 7 + 44)
        out.append(R(x, 4, bw, 36, th["surface"], th["border"], th["radius"]))
        out.append(T(x + 12, 27, label, 12, th["muted"]))
        out.append(T(x + bw - 16, 27, "v", 11, th["muted"], "400", "middle"))
        x += bw + 10
    return "".join(out), 44


def d_actions(c, w, th):
    acts = norm_actions(c["items"])
    out, total = [], 0
    widths = []
    for label, style in acts:
        b, bw = button(0, 0, label, style, th)
        widths.append(bw)
    x = w - (sum(widths) + 10 * (len(acts) - 1))
    for (label, style), bw in zip(acts, widths):
        b, _ = button(x, 7, label, style, th)
        out.append(b)
        x += bw + 10
    return "".join(out), 48


def d_form(c, w, th):
    fields = c["fields"]
    colw = (w - 40) / 2
    out, y, col = [], 16, 0
    row_h = 0
    body = []
    for f in fields:
        t = f.get("type", "text")
        full = t == "textarea"
        if full and col == 1:
            col, y = 0, y + row_h
            row_h = 0
        x = 20 + col * (colw + 0)
        fw = (w - 40) if full else colw - 16
        lab = f["label"] + (" *" if f.get("required") else "")
        body.append(T(x, y + 12, clip(lab, fw, 11), 11, th["muted"], "600"))
        if t == "checkbox":
            body.append(R(x, y + 20, 16, 16, th["surface"], th["border"], 3))
            if f.get("value") in (True, "true", "Yes"):
                body.append(T(x + 8, y + 33, "x", 12, th["primary"], "700", "middle"))
            body.append(T(x + 24, y + 33, clip(f.get("value_label", ""), fw - 30, 12), 12, th["text"]))
            h = 48
        elif t == "textarea":
            body.append(R(x, y + 20, fw, 64, th["surface"], th["border"], th["radius"]))
            for i, ln in enumerate(wrap(f.get("value", ""), fw - 20, 12)[:3]):
                body.append(T(x + 10, y + 40 + i * 16, ln, 12, th["text"]))
            h = 96
        else:
            ro = t == "readonly"
            body.append(R(x, y + 20, fw, 32, "#f4f4f4" if ro else th["surface"], th["border"], th["radius"]))
            body.append(T(x + 10, y + 41, clip(f.get("value", ""), fw - 40, 12), 12, th["text"] if f.get("value") else "#a8a8a8"))
            if t in ("select", "date"):
                body.append(T(x + fw - 14, y + 41, "v" if t == "select" else "[ ]", 11, th["muted"], "400", "middle"))
            h = 60
        row_h = max(row_h, h)
        if full:
            col, y, row_h = 0, y + row_h, 0
        else:
            col += 1
            if col == 2:
                col, y, row_h = 0, y + row_h, 0
    if col == 1:
        y += row_h
    total = y + 12
    out.append(R(0, 0, w, total, th["surface"], th["border"], th["radius"]))
    return "".join(out + body), total


def d_hitl(c, w, th):
    zone = c["zone"]
    zc = tone_color(th, zone_tone(zone))
    pad = 20
    inner = w - 2 * pad - 6
    body, y = [], 20
    p, pw = pill(pad + 6, y - 6, "%s ZONE" % zone, zc)
    body.append(p)
    body.append(T(pad + 6 + pw + 10, y + 8, "Agent proposal: " + c["agent"], 13, th["text"], "700"))
    if c.get("confidence") is not None:
        body.append(T(w - pad, y + 8, "Confidence %s" % c["confidence"], 12, th["muted"], "600", "end"))
    y += 36
    body.append(T(pad + 6, y, "PROPOSAL", 10, th["muted"], "700"))
    y += 18
    for ln in wrap(c["proposal"], inner, 13):
        body.append(T(pad + 6, y, ln, 13, th["text"], "600"))
        y += 18
    ev = c.get("evidence") or []
    if ev:
        y += 8
        body.append(T(pad + 6, y, "EVIDENCE AND CITATIONS", 10, th["muted"], "700"))
        y += 8
        for e in ev:
            lines = wrap(e, inner - 18, 12)
            body.append('<circle cx="%.1f" cy="%.1f" r="2.5" fill="%s"/>' % (pad + 10, y + 11, th["muted"]))
            for ln in lines:
                y += 16
                body.append(T(pad + 20, y, ln, 12, th["text"]))
            y += 4
    meta = []
    if c.get("sla"):
        meta.append("Review SLA: %s" % c["sla"])
    if c.get("reviewer"):
        meta.append("Reviewer: %s" % c["reviewer"])
    if meta:
        y += 22
        body.append(T(pad + 6, y, "   |   ".join(meta), 12, th["muted"]))
    if c.get("override_reasons"):
        y += 22
        body.append(T(pad + 6, y, "OVERRIDE REASON (required when you change the proposal)", 10, th["muted"], "700"))
        body.append(R(pad + 6, y + 8, 340, 32, th["surface"], th["border"], th["radius"]))
        body.append(T(pad + 16, y + 29, clip(" / ".join(c["override_reasons"]), 300, 12), 12, th["muted"]))
        y += 40
    y += 18
    acts = norm_actions(c["actions"])
    widths = [button(0, 0, a, s, th)[1] for a, s in acts]
    x = w - pad - (sum(widths) + 10 * (len(acts) - 1))
    for (label, style), bw in zip(acts, widths):
        b, _ = button(x, y, label, style, th)
        body.append(b)
        x += bw + 10
    y += 34 + 18
    frame = R(0, 0, w, y, th["surface"], th["border"], th["radius"]) + R(0, 0, 6, y, zc, None, 3) + \
        R(6, 0, w - 6, 44, tint(zc, 0.9), None, 0)
    return frame + "".join(body), y


def d_bar(c, w, th):
    items = c["items"]
    mx = max(i["value"] for i in items) or 1
    lw, vw = 150, 64
    bw = w - lw - vw - 40
    out = [R(0, 0, w, 24 + 28 * len(items), th["surface"], th["border"], th["radius"])]
    for i, it in enumerate(items):
        y = 18 + i * 28
        col = tone_color(th, it.get("tone", "blue"))
        out.append(T(14, y + 14, clip(it["label"], lw - 10, 12), 12, th["text"]))
        out.append(R(14 + lw, y + 2, bw, 16, "#f0f0f0", None, 3))
        out.append(R(14 + lw, y + 2, max(2, bw * it["value"] / mx), 16, col, None, 3))
        out.append(T(14 + lw + bw + 10, y + 14, str(it.get("display", it["value"])), 12, th["text"], "600"))
    return "".join(out), 24 + 28 * len(items)


def d_line(c, w, th):
    items = c["items"]
    h = 190
    left, bottom, top = 50, 34, 20
    vals = [i["value"] for i in items]
    lo, hi = min(0, min(vals)), max(vals) * 1.15 or 1
    pw, ph = w - left - 24, h - top - bottom
    out = [R(0, 0, w, h, th["surface"], th["border"], th["radius"])]
    for k in range(5):
        y = top + ph * k / 4
        out.append(L(left, y, left + pw, y, th["border"], 1, "3 3"))
        out.append(T(left - 8, y + 4, "%g" % round(hi - (hi - lo) * k / 4, 1), 10, th["muted"], "400", "end"))
    pts = []
    for i, it in enumerate(items):
        x = left + (pw * i / max(1, len(items) - 1))
        y = top + ph * (1 - (it["value"] - lo) / (hi - lo))
        pts.append((x, y))
        out.append(T(x, h - 14, clip(it["label"], pw / len(items), 10), 10, th["muted"], "400", "middle"))
    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.5"/>' % (" ".join("%.1f,%.1f" % p for p in pts), th["primary"]))
    for x, y in pts:
        out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (x, y, th["primary"]))
    if c.get("target") is not None:
        ty = top + ph * (1 - (c["target"] - lo) / (hi - lo))
        out.append(L(left, ty, left + pw, ty, th["danger"], 1.5, "5 4"))
        out.append(T(left + pw, ty - 5, "Target %s" % c["target"], 10, th["danger"], "700", "end"))
    return "".join(out), h


def d_donut(c, w, th):
    items = c["items"]
    total = sum(i["value"] for i in items) or 1
    r, cx, cy = 52, 80, 80
    circ = 2 * math.pi * r
    out = [R(0, 0, w, 160, th["surface"], th["border"], th["radius"])]
    off = 0.0
    for it in items:
        frac = it["value"] / total
        col = tone_color(th, it.get("tone", "blue"))
        out.append('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="22" stroke-dasharray="%.2f %.2f" stroke-dashoffset="%.2f" transform="rotate(-90 %d %d)"/>'
                   % (cx, cy, r, col, frac * circ, circ - frac * circ, -off, cx, cy))
        off += frac * circ
    out.append(T(cx, cy + 5, str(c.get("center", total)), 16, th["text"], "700", "middle"))
    for i, it in enumerate(items):
        y = 28 + i * 24
        out.append(R(176, y - 10, 12, 12, tone_color(th, it.get("tone", "blue")), None, 2))
        out.append(T(196, y, clip("%s  (%s)" % (it["label"], it.get("display", it["value"])), w - 210, 12), 12, th["text"]))
    return "".join(out), 160


def d_timeline(c, w, th):
    items = c["items"]
    out = [R(0, 0, w, 24 + 40 * len(items), th["surface"], th["border"], th["radius"])]
    for i, it in enumerate(items):
        y = 26 + i * 40
        col = tone_color(th, it.get("tone", "blue"))
        if i < len(items) - 1:
            out.append(L(24, y + 8, 24, y + 40 - 8, th["border"], 2))
        out.append('<circle cx="24" cy="%d" r="7" fill="%s"/>' % (y, col))
        out.append(T(44, y + 4, clip(it["label"], w - 60, 13), 13, th["text"], "600"))
        if it.get("detail"):
            out.append(T(44, y + 20, clip(it["detail"], w - 60, 11), 11, th["muted"]))
    return "".join(out), 24 + 40 * len(items)


def d_text(c, w, th):
    lines = wrap(c["text"], w - 32, 13)
    h = 28 + 18 * len(lines)
    out = [R(0, 0, w, h, th["surface"], th["border"], th["radius"])]
    for i, ln in enumerate(lines):
        out.append(T(16, 26 + i * 18, ln, 13, th["text"]))
    return "".join(out), h


DRAW = {"banner": d_banner, "stepper": d_stepper, "tabs": d_tabs, "kpis": d_kpis, "table": d_table,
        "filters": d_filters, "actions": d_actions, "form": d_form, "hitl_panel": d_hitl,
        "bar_chart": d_bar, "line_chart": d_line, "donut_chart": d_donut, "timeline": d_timeline, "text": d_text}
TITLED = {"table", "form", "bar_chart", "line_chart", "donut_chart", "timeline", "text", "hitl_panel"}


def draw_component(c, w, th):
    """Return (svg, height) with origin at the component's top-left."""
    svg, h = DRAW[c["type"]](c, w, th)
    if c.get("title") and c["type"] in TITLED:
        svg = T(0, 14, c["title"], 14, th["text"], "700") + G(svg, None, 0, 24)
        h += 24
    return svg, h


def layout_components(comps, th, width=CONTENT_W):
    """Flow components on a 12-column grid. Returns (svg, total_height)."""
    out, y, row, used = [], 0, [], 0

    def flush():
        nonlocal y, row, used
        if not row:
            return
        rh = 0
        x = 0
        for c, span in row:
            cw = (width - GAP * 11) / 12 * span + GAP * (span - 1)
            svg, h = draw_component(c, cw, th)
            out.append(G(svg, None, x, y))
            x += cw + GAP
            rh = max(rh, h)
        y += rh + GAP
        row, used = [], 0

    for c in comps:
        span = c.get("span", 12)
        if used + span > 12:
            flush()
        row.append((c, span))
        used += span
    flush()
    return "".join(out), max(0, y - GAP)


def screen_frame(screen, th, lane_name, brand, header_note=None):
    """One full application screen as an SVG group. Returns (svg, width, height)."""
    content, ch = layout_components(screen["components"], th)
    head_h = 72
    total_h = max(720, TOP_H + PAD + head_h + ch + PAD + 12)
    out = [R(0, 0, FRAME_W, total_h, th["bg"], th["border"], 0)]
    out.append(R(0, 0, FRAME_W, TOP_H, th["nav_bg"]))
    out.append(T(24, 35, brand, 17, th["nav_text"], "700"))
    out.append(R(FRAME_W - 24 - max(34, len(lane_name) * 6.4 + 16), 18, max(34, len(lane_name) * 6.4 + 16), 20,
                 tint(th["nav_bg"], 0.2), None, 10))
    out.append(T(FRAME_W - 24 - max(34, len(lane_name) * 6.4 + 16) / 2, 32, lane_name, 11, th["nav_text"], "600", "middle"))
    out.append(R(0, TOP_H, SIDE_W, total_h - TOP_H, th["surface"], th["border"]))
    for i, item in enumerate(screen["nav"]):
        y = TOP_H + 16 + i * 40
        act = item == screen["active_nav"]
        if act:
            out.append(R(0, y, SIDE_W, 40, tint(th["primary"], 0.9)))
            out.append(R(0, y, 4, 40, th["primary"]))
        out.append(T(24, y + 25, clip(item, SIDE_W - 40, 13), 13, th["primary"] if act else th["text"], "600" if act else "400"))
    x0, y0 = SIDE_W + PAD, TOP_H + PAD
    out.append(T(x0, y0 + 22, screen["title"], 24, th["text"], "700"))
    out.append(T(x0, y0 + 44, clip(screen["purpose"], CONTENT_W - 220, 13), 13, th["muted"]))
    st = screen.get("status")
    if st:
        p, _ = pill(x0 + CONTENT_W, y0 + 4, st["text"], tone_color(th, st.get("tone", "blue")), 12, "end")
        out.append(p)
    out.append(G(content, "components", x0, y0 + head_h))
    return "".join(out), FRAME_W, total_h


def report_as_screen(report, spec):
    """Wrap a report in an application frame so it can be drawn like a screen."""
    screens = {x["id"]: x for x in spec.get("screens", [])}
    base = screens.get((report.get("screen_ids") or [None])[0], {})
    nav = list(report.get("nav") or base.get("nav") or ["Home"])
    if "Reports" not in nav:
        nav.append("Reports")
    return {"id": report["id"], "title": report["title"], "purpose": report["question"], "nav": nav,
            "active_nav": "Reports", "components": report["components"],
            "status": {"text": "Report", "tone": "blue"}}
