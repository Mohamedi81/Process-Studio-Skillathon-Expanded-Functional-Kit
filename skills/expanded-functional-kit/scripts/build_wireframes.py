#!/usr/bin/env python3
"""Render the rich HTML wireframe pack from kit-spec.json.

Usage: python3 build_wireframes.py --input kit-spec.json --output wireframes.html
Exit 0: output written. Exit 1: every spec problem printed to stderr.
"""
import kit_common as kc
import kit_html as kh
import kit_svg as ks

DEFAULT_OUTPUT_NAME = "wireframes.html"


def side_panel(spec, screen, lane_names):
    scid = screen["id"]
    steps = [s for s in spec["steps"] if scid in (s.get("screen_ids") or [])]
    ucs = [u for u in spec["use_cases"] if scid in u.get("screen_ids", [])]
    maps = [m for m in spec["mappings"] if m["screen_id"] == scid]
    integ = kc.index_by(spec["integrations"])
    out = []
    out.append("<h4>Role and purpose</h4><p><b>%s</b>. %s</p>" % (kc.esc(lane_names.get(screen["lane"], screen["lane"])), kc.esc(screen["purpose"])))
    out.append("<h4>Use cases</h4>" + kh.table(["ID", "Use case", "Success measure"],
               [[u["id"], u["title"], u["success_measure"]] for u in ucs]))
    out.append("<h4>Opened by flow step</h4>" + kh.table(["Step", "Type", "Zone", "SLA"],
               [[s["id"] + " " + s["name"], kh.raw(kh.tag(s["type"], "blue")),
                 kh.raw(kh.tag(s.get("zone", "-"), kc.zone_tone(s.get("zone", "")))), s.get("sla", "-")] for s in steps]))
    for c in screen["components"]:
        if c["type"] == "hitl_panel":
            out.append("<h4>Human-in-the-loop contract</h4>" + kh.table(["Item", "Value"], [
                ["Agent", c["agent"]], ["Zone", kh.raw(kh.tag(c["zone"], kc.zone_tone(c["zone"])))],
                ["Reviewer", c.get("reviewer", "-")], ["Review SLA", c.get("sla", "-")],
                ["Actions", ", ".join(a if isinstance(a, str) else a.get("label", "") for a in c["actions"])],
                ["Override reasons", ", ".join(c.get("override_reasons", [])) or "-"]]))
    out.append("<h4>Data on this screen</h4>" + kh.table(["UI field", "Entity field", "Direction"],
               [[m["ui_field"], m["ref"], m["direction"]] for m in maps]))
    seen = []
    for m in maps:
        if m["integration_id"] not in seen:
            seen.append(m["integration_id"])
    out.append("<h4>Integrations behind it</h4>" + kh.table(["ID", "Integration", "Kind", "System"],
               [[i, integ[i]["name"], kh.raw(kh.tag(integ[i]["kind"], "amber" if integ[i]["kind"] == "agentic" else "green")), integ[i]["system"]] for i in seen]))
    if screen.get("notes"):
        out.append("<h4>Design notes</h4>" + "".join("<p>%s</p>" % kc.esc(n) for n in screen["notes"]))
    return "".join(out)


def build(spec, out_path):
    th = kc.theme_of(spec)
    meta = spec["meta"]
    lane_names = {l["id"]: l["name"] for l in spec["lanes"]}
    brand = th["brand_name"]
    rows = []
    for s in spec["steps"]:
        rows.append([s["id"], s["name"], kh.raw(kh.tag(s["type"], "blue")), lane_names.get(s["lane"], ""),
                     kh.raw(kh.tag(s.get("zone", "-"), kc.zone_tone(s.get("zone", "")))),
                     ", ".join(s.get("screen_ids", []) or []) or "-",
                     ", ".join(s.get("integration_ids", []) or []) or "-"])
    body = ['<nav class="index">%s</nav>' % "".join('<a href="#%s">%s</a>' % (kc.esc(s["id"]), kc.esc(s["title"])) for s in spec["screens"])]
    body.append('<section class="card"><h3>Flow overview <small>deterministic backbone, agentic plug-in points and human review screens</small></h3><div class="side">%s</div></section>'
                % kh.table(["Step", "Name", "Type", "Role or agent lane", "Zone", "Screens", "Integrations"], rows))
    by_lane = {}
    for sc in spec["screens"]:
        by_lane.setdefault(sc["lane"], []).append(sc)
    for lane in spec["lanes"]:
        scs = by_lane.get(lane["id"], [])
        if not scs:
            continue
        body.append('<h2 class="lane">%s</h2>' % kc.esc(lane["name"]))
        for sc in scs:
            svg, w, h = ks.screen_frame(sc, th, lane["name"], brand)
            body.append('<section class="card" id="%s"><h3>%s <small>%s | /%s</small></h3><div class="grid"><div class="shot">'
                        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="%s">%s</svg></div><div class="side">%s</div></div></section>'
                        % (kc.esc(sc["id"]), kc.esc(sc["title"]), kc.esc(sc["id"]), kc.esc(sc["url_path"]), w, h, kc.esc(th["font"]), svg, side_panel(spec, sc, lane_names)))
    note = "Look and feel: %s (brand: %s). %s" % (th["source"], brand, meta.get("illustrative_note", "Record IDs, names and figures on screens are illustrative."))
    out_path.write_text(kh.page("%s: wireframes" % meta["title"], "%s | %s | %s" % (meta["industry"], meta["blueprint_name"], meta.get("version", "v1")), th, "".join(body), note), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(kc.run(build))
