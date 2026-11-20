#!/usr/bin/env python3
"""Shared helpers for the Expanded Functional Kit scripts.

Not an entry script: it is imported by the build_*.py scripts and holds the
spec validation, theme handling and small utilities. It holds no domain content.
"""
import argparse
import html
import json
import sys
from pathlib import Path

FIELD_TYPES = {"id", "string", "text", "integer", "decimal", "currency", "percentage",
               "date", "datetime", "boolean", "enum", "url", "json"}
STEP_TYPES = {"start", "end", "deterministic", "agentic", "human", "gateway"}
ZONES = {"GREEN", "AMBER", "RED"}
TONES = {"green", "amber", "red", "blue", "grey"}
LANE_KINDS = {"role", "agent", "system"}
SCREEN_PATTERNS = {"queue", "review", "hitl_review", "form", "detail", "dashboard"}
INTEGRATION_PATTERNS = {"rest_api", "mcp_tool", "event", "file", "batch", "database"}
DIRECTIONS = {"read", "write", "both"}
FORM_FIELD_TYPES = {"text", "select", "date", "number", "textarea", "checkbox", "readonly"}

# component type -> required keys
COMP_REQUIRED = {
    "banner": ["text"],
    "stepper": ["items"],
    "tabs": ["items"],
    "kpis": ["items"],
    "table": ["headers", "rows"],
    "form": ["fields"],
    "hitl_panel": ["agent", "zone", "proposal"],
    "bar_chart": ["items"],
    "line_chart": ["items"],
    "donut_chart": ["items"],
    "timeline": ["items"],
    "text": ["text"],
    "filters": ["items"],
    "actions": ["items"],
}

DEFAULT_THEME = {
    "brand_name": "Enterprise App",
    "source": "default (no customer look and feel was supplied)",
    "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
    "font_figma": "Arial",
    "primary": "#0f62fe",
    "primary_dark": "#0043ce",
    "nav_bg": "#161616",
    "nav_text": "#ffffff",
    "bg": "#f4f4f4",
    "surface": "#ffffff",
    "text": "#161616",
    "muted": "#6f6f6f",
    "border": "#e0e0e0",
    "success": "#24a148",
    "warning": "#f1c21b",
    "danger": "#da1e28",
    "radius": 4,
}
COLOR_KEYS = ["primary", "primary_dark", "nav_bg", "nav_text", "bg", "surface", "text",
              "muted", "border", "success", "warning", "danger"]


# ---------------------------------------------------------------- small utils
def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def has_emoji(text):
    for ch in text:
        o = ord(ch)
        if (0x1F300 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF or 0x1F000 <= o <= 0x1F2FF
                or o in (0x2B50, 0x2B55, 0xFE0F, 0x200D)):
            return True
    return False


def is_hex(value):
    return (isinstance(value, str) and len(value) == 7 and value[0] == "#"
            and all(c in "0123456789abcdefABCDEF" for c in value[1:]))


def hex_rgb(h):
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def tint(h, amount):
    """Mix colour with white. amount 0..1 (1 = white)."""
    r, g, b = hex_rgb(h)
    r, g, b = [round(c + (255 - c) * amount) for c in (r, g, b)]
    return "#%02x%02x%02x" % (r, g, b)


def shade(h, amount):
    """Mix colour with black. amount 0..1 (1 = black)."""
    r, g, b = hex_rgb(h)
    r, g, b = [round(c * (1 - amount)) for c in (r, g, b)]
    return "#%02x%02x%02x" % (r, g, b)


def theme_of(spec):
    theme = dict(DEFAULT_THEME)
    theme.update({k: v for k, v in (spec.get("theme") or {}).items() if v not in (None, "")})
    return theme


def tone_color(theme, tone):
    return {"green": theme["success"], "amber": theme["warning"], "red": theme["danger"],
            "blue": theme["primary"], "grey": theme["muted"]}.get(tone, theme["muted"])


def zone_tone(zone):
    return {"GREEN": "green", "AMBER": "amber", "RED": "red"}.get(zone, "grey")


def cell(c):
    """Table cell -> (text, tone or None)."""
    if isinstance(c, dict):
        return str(c.get("text", "")), c.get("tone")
    return ("" if c is None else str(c)), None


def index_by(items, key="id"):
    return {i.get(key): i for i in (items or []) if isinstance(i, dict)}


def entity_refs(spec):
    refs = {}
    for e in spec.get("entities", []):
        for f in e.get("fields", []):
            refs["%s.%s" % (e.get("id"), f.get("name"))] = (e, f)
    return refs


def walk_components(spec):
    """Yield (kind, owner_id, component) for screens and reports."""
    for s in spec.get("screens", []):
        for c in s.get("components", []):
            yield "screen", s.get("id"), c
    for r in spec.get("reports", []):
        for c in r.get("components", []):
            yield "report", r.get("id"), c


def step_screens(spec):
    """screen id -> list of step ids that open it."""
    out = {}
    for st in spec.get("steps", []):
        for sid in st.get("screen_ids", []) or []:
            out.setdefault(sid, []).append(st.get("id"))
    return out


def screen_integrations(spec):
    """screen id -> ordered list of integration ids (from mappings)."""
    out = {}
    for m in spec.get("mappings", []):
        out.setdefault(m.get("screen_id"), [])
        if m.get("integration_id") not in out[m.get("screen_id")]:
            out[m.get("screen_id")].append(m.get("integration_id"))
    return out


def strings_in(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings_in(v)


# ----------------------------------------------------------------- validation
def validate_spec(spec):
    """Return a list of problem strings. Empty list means the spec is valid."""
    E = []
    if not isinstance(spec, dict):
        return ["spec must be a JSON object"]

    def need(cond, msg):
        if not cond:
            E.append(msg)

    def ids_of(key, label):
        items = spec.get(key)
        if not isinstance(items, list) or not items:
            E.append("'%s' must be a non-empty list" % key)
            return {}
        seen = {}
        for i, it in enumerate(items):
            if not isinstance(it, dict) or not it.get("id"):
                E.append("%s[%d] has no 'id'" % (key, i))
                continue
            if it["id"] in seen:
                E.append("duplicate %s id '%s'" % (label, it["id"]))
            seen[it["id"]] = it
        return seen

    meta = spec.get("meta") or {}
    for k in ("title", "industry", "blueprint_name"):
        need(meta.get(k), "meta.%s is missing" % k)

    theme = spec.get("theme") or {}
    for k in COLOR_KEYS:
        if k in theme and not is_hex(theme[k]):
            E.append("theme.%s must be a #rrggbb colour, got %r" % (k, theme[k]))

    lanes = ids_of("lanes", "lane")
    for lid, ln in lanes.items():
        need(ln.get("name"), "lane '%s' has no name" % lid)
        need(ln.get("kind") in LANE_KINDS, "lane '%s' kind must be one of %s" % (lid, sorted(LANE_KINDS)))

    # entities and fields
    entities = ids_of("entities", "entity")
    refs = set()
    for eid, e in entities.items():
        for k in ("name", "definition"):
            need(e.get(k), "entity '%s' has no %s" % (eid, k))
        fields = e.get("fields")
        if not isinstance(fields, list) or not fields:
            E.append("entity '%s' needs a non-empty 'fields' list" % eid)
            continue
        names = set()
        for f in fields:
            fn = f.get("name")
            if not fn:
                E.append("entity '%s' has a field without 'name'" % eid)
                continue
            if fn in names:
                E.append("entity '%s' has duplicate field '%s'" % (eid, fn))
            names.add(fn)
            refs.add("%s.%s" % (eid, fn))
            need(f.get("label"), "field %s.%s has no label" % (eid, fn))
            need(f.get("definition"), "field %s.%s has no definition" % (eid, fn))
            need(f.get("type") in FIELD_TYPES, "field %s.%s type must be one of %s" % (eid, fn, sorted(FIELD_TYPES)))
            if f.get("type") == "enum":
                need(f.get("allowed_values"), "field %s.%s is an enum and needs allowed_values" % (eid, fn))

    def check_ref(ref, where):
        if ref not in refs:
            E.append("%s: unknown entity field reference '%s'" % (where, ref))

    # integrations
    integ = ids_of("integrations", "integration")
    for iid, it in integ.items():
        for k in ("name", "system", "operation", "protocol", "auth", "latency"):
            need(it.get(k), "integration '%s' has no %s" % (iid, k))
        need(it.get("pattern") in INTEGRATION_PATTERNS, "integration '%s' pattern must be one of %s" % (iid, sorted(INTEGRATION_PATTERNS)))
        need(it.get("direction") in DIRECTIONS, "integration '%s' direction must be read, write or both" % iid)
        need(it.get("kind") in ("deterministic", "agentic"), "integration '%s' kind must be deterministic or agentic" % iid)
        if it.get("kind") == "agentic":
            need(it.get("mcp_tool"), "agentic integration '%s' needs mcp_tool" % iid)
        for sect in ("request", "response"):
            for p in it.get(sect, []) or []:
                need(p.get("field"), "integration '%s' %s has a parameter without 'field'" % (iid, sect))
                if p.get("ref"):
                    check_ref(p["ref"], "integration '%s' %s" % (iid, sect))

    # steps
    steps = ids_of("steps", "step")
    screens_decl = index_by(spec.get("screens"))
    for sid, s in steps.items():
        need(s.get("name"), "step '%s' has no name" % sid)
        need(s.get("type") in STEP_TYPES, "step '%s' type must be one of %s" % (sid, sorted(STEP_TYPES)))
        need(s.get("lane") in lanes, "step '%s' lane '%s' is not in lanes" % (sid, s.get("lane")))
        need(s.get("description") or s.get("type") == "gateway", "step '%s' has no description" % sid)
        t = s.get("type")
        if t != "end":
            nxt = s.get("next")
            if not isinstance(nxt, list) or not nxt:
                E.append("step '%s' needs a 'next' list" % sid)
                nxt = []
            for n in nxt:
                if n.get("to") not in steps:
                    E.append("step '%s' next target '%s' does not exist" % (sid, n.get("to")))
            if t != "gateway" and len(nxt) > 1:
                E.append("step '%s' has several 'next' targets: add a gateway step to split the flow" % sid)
            if t == "gateway":
                need(s.get("gateway") in ("xor", "and"), "gateway step '%s' needs gateway 'xor' or 'and'" % sid)
                if len(nxt) > 1 and s.get("gateway") == "xor":
                    for n in nxt:
                        need(n.get("condition"), "XOR gateway '%s': every next needs a 'condition'" % sid)
        for iid in s.get("integration_ids", []) or []:
            need(iid in integ, "step '%s' references unknown integration '%s'" % (sid, iid))
        if t == "deterministic":
            need(s.get("rule"), "deterministic step '%s' needs 'rule' (the codified rule)" % sid)
            need(s.get("zone", "GREEN") == "GREEN", "deterministic step '%s' must be zone GREEN" % sid)
        if t == "agentic":
            need(s.get("zone") in ("AMBER", "RED"), "agentic step '%s' zone must be AMBER or RED" % sid)
            need(s.get("agent"), "agentic step '%s' needs 'agent'" % sid)
            need(s.get("integration_ids"), "agentic step '%s' needs integration_ids (the plug-in calls)" % sid)
            for iid in s.get("integration_ids", []) or []:
                if iid in integ:
                    need(integ[iid].get("kind") == "agentic", "agentic step '%s' integration '%s' must have kind agentic" % (sid, iid))
            targets = [steps.get(n.get("to"), {}) for n in s.get("next", []) or []]
            need(any(x.get("type") == "human" for x in targets),
                 "agentic step '%s' must hand over to a human (HITL) step directly" % sid)
        if t == "human":
            need(s.get("screen_ids"), "human step '%s' needs screen_ids" % sid)
            need(s.get("sla"), "human step '%s' needs an 'sla'" % sid)
        for key in ("reads", "writes"):
            for rf in s.get(key, []) or []:
                check_ref(rf, "step '%s' %s" % (sid, key))
        for sc in s.get("screen_ids", []) or []:
            need(sc in screens_decl, "step '%s' references unknown screen '%s'" % (sid, sc))
    starts = [i for i, s in steps.items() if s.get("type") == "start"]
    ends = [i for i, s in steps.items() if s.get("type") == "end"]
    need(starts, "flow needs at least one 'start' step")
    need(ends, "flow needs at least one 'end' step")
    seen, todo = set(starts), list(starts)
    while todo:
        cur = todo.pop()
        for n in steps.get(cur, {}).get("next", []) or []:
            if n.get("to") in steps and n["to"] not in seen:
                seen.add(n["to"])
                todo.append(n["to"])
    for sid in steps:
        need(sid in seen, "step '%s' is not reachable from a start step" % sid)
    used_integ = {i for s in steps.values() for i in (s.get("integration_ids") or [])}
    for iid in integ:
        need(iid in used_integ, "integration '%s' is not used by any step" % iid)

    # screens
    screens = ids_of("screens", "screen")
    opened = step_screens(spec)
    for scid, sc in screens.items():
        for k in ("title", "purpose", "url_path"):
            need(sc.get(k), "screen '%s' has no %s" % (scid, k))
        need(sc.get("lane") in lanes, "screen '%s' lane '%s' is not in lanes" % (scid, sc.get("lane")))
        need(sc.get("pattern") in SCREEN_PATTERNS, "screen '%s' pattern must be one of %s" % (scid, sorted(SCREEN_PATTERNS)))
        need(isinstance(sc.get("nav"), list) and sc.get("nav"), "screen '%s' needs a 'nav' list" % scid)
        need(sc.get("active_nav") in (sc.get("nav") or []), "screen '%s' active_nav must be one of nav" % scid)
        need(scid in opened, "screen '%s' is not opened by any step (orphan screen)" % scid)
        comps = sc.get("components")
        need(isinstance(comps, list) and comps, "screen '%s' needs components" % scid)
        if sc.get("pattern") == "hitl_review":
            need(any(c.get("type") == "hitl_panel" for c in comps or []),
                 "screen '%s' is hitl_review and needs a hitl_panel component" % scid)

    # use cases
    ucs = ids_of("use_cases", "use case")
    covered = set()
    for uid, u in ucs.items():
        for k in ("title", "goal", "success_measure"):
            need(u.get(k), "use case '%s' has no %s" % (uid, k))
        need(u.get("lane") in lanes, "use case '%s' lane is not in lanes" % uid)
        for sc in u.get("screen_ids", []) or []:
            need(sc in screens, "use case '%s' references unknown screen '%s'" % (uid, sc))
            covered.add(sc)
        need(u.get("screen_ids"), "use case '%s' needs screen_ids" % uid)
        for st in u.get("step_ids", []) or []:
            need(st in steps, "use case '%s' references unknown step '%s'" % (uid, st))
    for scid in screens:
        need(scid in covered, "screen '%s' belongs to no use case" % scid)

    # mappings
    maps = spec.get("mappings")
    if not isinstance(maps, list) or not maps:
        E.append("'mappings' must be a non-empty list")
        maps = []
    mapped_screens = set()
    for i, m in enumerate(maps):
        w = "mappings[%d]" % i
        need(m.get("screen_id") in screens, "%s unknown screen '%s'" % (w, m.get("screen_id")))
        need(m.get("integration_id") in integ, "%s unknown integration '%s'" % (w, m.get("integration_id")))
        need(m.get("ui_field"), "%s has no ui_field" % w)
        need(m.get("json_path"), "%s has no json_path" % w)
        need(m.get("direction") in DIRECTIONS, "%s direction must be read, write or both" % w)
        if m.get("ref"):
            check_ref(m["ref"], w)
        else:
            E.append("%s has no entity field 'ref'" % w)
        it = integ.get(m.get("integration_id"))
        if it and m.get("json_path") and m.get("direction") in DIRECTIONS:
            sects = {"read": ["response"], "write": ["request"], "both": ["request", "response"]}[m["direction"]]
            params = [p for sect in sects for p in (it.get(sect) or [])]
            hit = [p for p in params if p.get("field") == m["json_path"]]
            if not hit:
                E.append("%s json_path '%s' is not a %s field of integration '%s'" % (w, m["json_path"], "/".join(sects), m["integration_id"]))
            elif hit[0].get("ref") and m.get("ref") and hit[0]["ref"] != m["ref"]:
                E.append("%s ref '%s' differs from the integration field's ref '%s'" % (w, m["ref"], hit[0]["ref"]))
        mapped_screens.add(m.get("screen_id"))
    for scid in screens:
        need(scid in mapped_screens, "screen '%s' has no integration mapping rows" % scid)

    # components
    def check_comp(c, where):
        t = c.get("type")
        if t not in COMP_REQUIRED:
            E.append("%s: unknown component type '%s' (allowed: %s)" % (where, t, sorted(COMP_REQUIRED)))
            return
        for k in COMP_REQUIRED[t]:
            if c.get(k) in (None, "", []):
                E.append("%s: %s component is missing '%s'" % (where, t, k))
        span = c.get("span", 12)
        if not isinstance(span, int) or not 1 <= span <= 12:
            E.append("%s: span must be an integer 1..12" % where)
        if t == "table":
            hdr = c.get("headers") or []
            for r in c.get("rows") or []:
                if len(r) != len(hdr):
                    E.append("%s: table row has %d cells but %d headers" % (where, len(r), len(hdr)))
                    break
            for rf in c.get("refs", []) or []:
                if rf:
                    check_ref(rf, where)
            for r in c.get("rows") or []:
                for x in r:
                    if isinstance(x, dict) and x.get("tone") and x["tone"] not in TONES:
                        E.append("%s: tone '%s' not in %s" % (where, x["tone"], sorted(TONES)))
        if t == "form":
            for f in c.get("fields") or []:
                need(f.get("label"), "%s: form field without label" % where)
                need(f.get("type", "text") in FORM_FIELD_TYPES, "%s: form field type must be one of %s" % (where, sorted(FORM_FIELD_TYPES)))
                if f.get("ref"):
                    check_ref(f["ref"], where)
        if t == "hitl_panel":
            need(c.get("zone") in ("AMBER", "RED"), "%s: hitl_panel zone must be AMBER or RED" % where)
            need(c.get("actions"), "%s: hitl_panel needs actions" % where)
        if t in ("kpis", "bar_chart", "line_chart", "donut_chart"):
            for it in c.get("items") or []:
                if t != "kpis" and not isinstance(it.get("value"), (int, float)):
                    E.append("%s: %s item '%s' needs a numeric value" % (where, t, it.get("label")))
                if it.get("tone") and it["tone"] not in TONES:
                    E.append("%s: tone '%s' not in %s" % (where, it["tone"], sorted(TONES)))

    for kind, owner, c in walk_components(spec):
        check_comp(c, "%s '%s'" % (kind, owner))

    # reports
    reports = ids_of("reports", "report")
    for rid, r in reports.items():
        for k in ("title", "question", "refresh", "access"):
            need(r.get(k), "report '%s' has no %s" % (rid, k))
        need(r.get("lane") in lanes, "report '%s' lane '%s' is not in lanes" % (rid, r.get("lane")))
        need(r.get("use_case_ids"), "report '%s' needs use_case_ids" % rid)
        for u in r.get("use_case_ids", []) or []:
            need(u in ucs, "report '%s' references unknown use case '%s'" % (rid, u))
        need(r.get("screen_ids"), "report '%s' needs screen_ids (the wireframes it serves)" % rid)
        for sc in r.get("screen_ids", []) or []:
            need(sc in screens, "report '%s' references unknown screen '%s'" % (rid, sc))
        need(r.get("dimensions"), "report '%s' needs dimensions" % rid)
        need(r.get("components"), "report '%s' needs components (its wireframe)" % rid)
        kp = r.get("kpis")
        if not isinstance(kp, list) or not kp:
            E.append("report '%s' needs a kpis list" % rid)
            kp = []
        for k in kp:
            for key in ("name", "definition", "formula", "unit", "source"):
                need(k.get(key), "report '%s' KPI '%s' has no %s" % (rid, k.get("name"), key))
            for rf in k.get("refs", []) or []:
                check_ref(rf, "report '%s' KPI '%s'" % (rid, k.get("name")))

    served = {u for r in reports.values() for u in (r.get("use_case_ids") or [])}
    for uid in ucs:
        need(uid in served, "use case '%s' is served by no report" % uid)

    for s in strings_in(spec):
        if has_emoji(s):
            E.append("emoji or pictograph found in text: %r (use words)" % s[:50])
            break
    return E


# ------------------------------------------------------------------- runner
def load_spec(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")), None
    except (OSError, ValueError) as exc:
        return None, "input is not readable JSON: %s" % exc


def run(build, validate=True):
    """Standard entry: parse --input/--output, validate, call build(spec, out_path)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    spec, err = load_spec(args.input)
    if err:
        print("FAIL: " + err, file=sys.stderr)
        return 1
    if validate:
        errors = validate_spec(spec)
        if errors:
            print("FAIL: %d issue(s) in the kit spec" % len(errors), file=sys.stderr)
            for e in errors:
                print(" - " + e, file=sys.stderr)
            return 1
    build(spec, Path(args.output))
    print("PASS: wrote %s" % args.output)
    return 0
