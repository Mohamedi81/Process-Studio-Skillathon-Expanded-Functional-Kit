#!/usr/bin/env python3
"""Render a deterministic BPMN 2.0 file (with BPMNDI diagram) from kit-spec.json.

Deterministic steps become service tasks (or business rule tasks when they only
apply a rule), human review steps become user tasks, gateways stay gateways, and
every agentic step becomes a service task carrying an explicit plug-in point: an
extension element with the agent, MCP tool and integration call, plus a text
annotation on the diagram. The file opens in bpmn.io, Signavio, Camunda Modeler
and Celonis Process Designer.

Usage: python3 build_bpmn.py --input kit-spec.json --output process.bpmn
Exit 0: output written. Exit 1: every spec problem printed to stderr.
"""
import xml.etree.ElementTree as ET

import kit_common as kc

DEFAULT_OUTPUT_NAME = "process.bpmn"

NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
    "bioc": "http://bpmn.io/schema/bpmn/biocolor/1.0",
    "color": "http://www.omg.org/spec/BPMN/non-normative/color/1.0",
    "ef": "https://expanded-functional-kit.example/schema/1.0",
}
for _p, _u in NS.items():
    ET.register_namespace(_p, _u)

COL_W = 230
SLOT_H = 150
LANE_MIN = 160
POOL_X, POOL_Y = 40, 40
LABEL_W = 30
LEFT_PAD = 70

COLORS = {  # fill, stroke
    "deterministic": ("#e8f5e9", "#2e7d32"),
    "agentic_AMBER": ("#fff3cd", "#b26a00"),
    "agentic_RED": ("#fde8e8", "#c62828"),
    "human": ("#e3f2fd", "#1565c0"),
    "gateway": ("#ffffff", "#424242"),
    "start": ("#ffffff", "#2e7d32"),
    "end": ("#ffffff", "#c62828"),
}


def q(prefix, tag):
    return "{%s}%s" % (NS[prefix], tag)


def sub(parent, prefix, tag, **attrs):
    return ET.SubElement(parent, q(prefix, tag), {k: str(v) for k, v in attrs.items() if v is not None})


def node_size(step):
    t = step["type"]
    if t in ("start", "end"):
        return 36, 36
    if t == "gateway":
        return 50, 50
    return 130, 80


def layers(spec):
    """Longest-path layering with back edges (loops) removed. Returns (layer, back_edges)."""
    steps = kc.index_by(spec["steps"])
    starts = [s["id"] for s in spec["steps"] if s["type"] == "start"]
    state, back, order = {}, set(), []

    def dfs(n):
        state[n] = 1
        for nx in steps[n].get("next", []) or []:
            t = nx["to"]
            if state.get(t) == 1:
                back.add((n, t))
            elif t not in state:
                dfs(t)
        state[n] = 2
        order.append(n)

    for s in starts:
        if s not in state:
            dfs(s)
    layer = {n: 0 for n in steps}
    for n in reversed(order):
        for nx in steps[n].get("next", []) or []:
            if (n, nx["to"]) not in back:
                layer[nx["to"]] = max(layer[nx["to"]], layer[n] + 1)
    return layer, back


def documentation(step, spec_integ):
    bits = [step.get("description", "")]
    if step.get("rule"):
        bits.append("Rule: %s" % step["rule"])
    if step.get("zone"):
        bits.append("Autonomy zone: %s" % step["zone"])
    if step.get("sla"):
        bits.append("SLA: %s" % step["sla"])
    if step.get("reads"):
        bits.append("Reads: %s" % ", ".join(step["reads"]))
    if step.get("writes"):
        bits.append("Writes: %s" % ", ".join(step["writes"]))
    for iid in step.get("integration_ids", []) or []:
        i = spec_integ[iid]
        bits.append("Integration %s: %s %s" % (iid, i["system"], i["operation"]))
    return "\n".join(b for b in bits if b)


def build(spec, out_path):
    steps = kc.index_by(spec["steps"])
    integ = kc.index_by(spec["integrations"])
    lanes = spec["lanes"]
    layer, back = layers(spec)

    # ---- slots: stack nodes that share (lane, layer)
    slot = {}
    counts = {}
    for s in spec["steps"]:
        key = (s["lane"], layer[s["id"]])
        slot[s["id"]] = counts.get(key, 0)
        counts[key] = slot[s["id"]] + 1
    lane_slots = {l["id"]: 1 for l in lanes}
    for (lane, _), n in counts.items():
        lane_slots[lane] = max(lane_slots[lane], n)
    lane_h = {lid: max(LANE_MIN, n * SLOT_H) for lid, n in lane_slots.items()}
    lane_y, y = {}, POOL_Y
    for l in lanes:
        lane_y[l["id"]] = y
        y += lane_h[l["id"]]
    pool_h = y - POOL_Y
    max_layer = max(layer.values())
    pool_w = LABEL_W + LEFT_PAD + (max_layer + 1) * COL_W + 40

    box = {}  # id -> (x, y, w, h)
    ann = {}
    for s in spec["steps"]:
        w, h = node_size(s)
        cx = POOL_X + LABEL_W + LEFT_PAD + layer[s["id"]] * COL_W
        slot_top = lane_y[s["lane"]] + slot[s["id"]] * SLOT_H
        cy = slot_top + (SLOT_H / 2 + 14 if s["type"] == "agentic" else lane_h[s["lane"]] / 2 if lane_slots[s["lane"]] == 1 else SLOT_H / 2)
        box[s["id"]] = (cx - w / 2, cy - h / 2, w, h)
        if s["type"] == "agentic":
            ann[s["id"]] = (cx - 90, cy - h / 2 - 54, 180, 44)

    # ---- model
    defs = ET.Element(q("bpmn", "definitions"), {
        "id": "Definitions_1", "targetNamespace": "https://expanded-functional-kit.example/bpmn",
        "exporter": "expanded-functional-kit", "exporterVersion": "1.0"})
    collab = sub(defs, "bpmn", "collaboration", id="Collaboration_1")
    sub(collab, "bpmn", "participant", id="Participant_1", name=spec["meta"]["title"], processRef="Process_1")
    proc = sub(defs, "bpmn", "process", id="Process_1", name=spec["meta"]["title"], isExecutable="false")
    doc = sub(proc, "bpmn", "documentation")
    doc.text = ("%s | Industry: %s | Blueprint: %s. Green = deterministic, amber/red = agentic plug-in point, blue = human review."
                % (spec["meta"]["title"], spec["meta"]["industry"], spec["meta"]["blueprint_name"]))
    laneset = sub(proc, "bpmn", "laneSet", id="LaneSet_1")
    for l in lanes:
        ln = sub(laneset, "bpmn", "lane", id="Lane_%s" % l["id"], name=l["name"])
        for s in spec["steps"]:
            if s["lane"] == l["id"]:
                sub(ln, "bpmn", "flowNodeRef").text = "Node_%s" % s["id"]

    incoming, outgoing, flows = {}, {}, []
    for s in spec["steps"]:
        for k, nx in enumerate(s.get("next", []) or []):
            fid = "Flow_%s_%s" % (s["id"], nx["to"])
            flows.append((fid, s["id"], nx["to"], nx.get("condition")))
            outgoing.setdefault(s["id"], []).append(fid)
            incoming.setdefault(nx["to"], []).append(fid)

    for s in spec["steps"]:
        t = s["type"]
        nid = "Node_%s" % s["id"]
        name = s["name"] if t != "gateway" else (s.get("name") or "")
        if t == "start":
            el = sub(proc, "bpmn", "startEvent", id=nid, name=name)
        elif t == "end":
            el = sub(proc, "bpmn", "endEvent", id=nid, name=name)
        elif t == "gateway":
            el = sub(proc, "bpmn", "exclusiveGateway" if s["gateway"] == "xor" else "parallelGateway", id=nid, name=name)
        elif t == "human":
            el = sub(proc, "bpmn", "userTask", id=nid, name="%s: %s" % (s["id"], name))
        elif t == "agentic":
            el = sub(proc, "bpmn", "serviceTask", id=nid, name="%s: %s" % (s["id"], name), implementation="##WebService")
        else:
            tag = "businessRuleTask" if s.get("rule") and not s.get("integration_ids") else "serviceTask"
            el = sub(proc, "bpmn", tag, id=nid, name="%s: %s" % (s["id"], name))
        if t not in ("start", "end", "gateway"):
            d = sub(el, "bpmn", "documentation")
            d.text = documentation(s, integ)
        if t in ("deterministic", "agentic", "human") and (s.get("integration_ids") or t == "human" or s.get("zone")):
            ext = sub(el, "bpmn", "extensionElements")
            if s.get("zone"):
                sub(ext, "ef", "step", id=s["id"], type=t, zone=s.get("zone"), sla=s.get("sla"), rule=s.get("rule"))
            for iid in s.get("integration_ids", []) or []:
                i = integ[iid]
                if t == "agentic":
                    sub(ext, "ef", "agenticPlugPoint", integrationId=iid, agent=s.get("agent"), mcpTool=i.get("mcp_tool"),
                        system=i["system"], operation=i["operation"], protocol=i["protocol"], zone=s.get("zone"),
                        fallback=s.get("fallback") or i.get("fallback"), reviewScreens=",".join(s.get("screen_ids", []) or []))
                else:
                    sub(ext, "ef", "integrationCall", integrationId=iid, system=i["system"], operation=i["operation"],
                        protocol=i["protocol"], direction=i["direction"])
            for sc in s.get("screen_ids", []) or []:
                sub(ext, "ef", "screen", id=sc)
        for fid in incoming.get(s["id"], []):
            sub(el, "bpmn", "incoming").text = fid
        for fid in outgoing.get(s["id"], []):
            sub(el, "bpmn", "outgoing").text = fid
    for fid, a, b, cond in flows:
        sub(proc, "bpmn", "sequenceFlow", id=fid, sourceRef="Node_%s" % a, targetRef="Node_%s" % b, name=cond)
    for sid, _ in ann.items():
        s = steps[sid]
        i = integ[s["integration_ids"][0]]
        ta = sub(proc, "bpmn", "textAnnotation", id="Ann_%s" % sid)
        sub(ta, "bpmn", "text").text = "PLUG-IN POINT %s | %s | %s" % (s.get("agent"), i.get("mcp_tool"), s.get("zone"))
        sub(proc, "bpmn", "association", id="Assoc_%s" % sid, sourceRef="Node_%s" % sid, targetRef="Ann_%s" % sid, associationDirection="None")

    # ---- diagram
    diagram = sub(defs, "bpmndi", "BPMNDiagram", id="Diagram_1")
    plane = sub(diagram, "bpmndi", "BPMNPlane", id="Plane_1", bpmnElement="Collaboration_1")

    def shape(eid, x, y, w, h, fill=None, stroke=None, horizontal=None, label=None):
        attrs = {"id": "Shape_%s" % eid, "bpmnElement": eid}
        if horizontal:
            attrs["isHorizontal"] = "true"
        if fill:
            attrs["{%s}fill" % NS["bioc"]] = fill
            attrs["{%s}stroke" % NS["bioc"]] = stroke
            attrs["{%s}background-color" % NS["color"]] = fill
            attrs["{%s}border-color" % NS["color"]] = stroke
        sh = ET.SubElement(plane, q("bpmndi", "BPMNShape"), attrs)
        ET.SubElement(sh, q("dc", "Bounds"), {"x": "%.0f" % x, "y": "%.0f" % y, "width": "%.0f" % w, "height": "%.0f" % h})
        if label:
            lb = ET.SubElement(sh, q("bpmndi", "BPMNLabel"))
            ET.SubElement(lb, q("dc", "Bounds"), {"x": "%.0f" % label[0], "y": "%.0f" % label[1], "width": "%.0f" % label[2], "height": "27"})

    shape("Participant_1", POOL_X, POOL_Y, pool_w, pool_h, horizontal=True)
    for l in lanes:
        shape("Lane_%s" % l["id"], POOL_X + LABEL_W, lane_y[l["id"]], pool_w - LABEL_W, lane_h[l["id"]], horizontal=True)
    for s in spec["steps"]:
        x, y_, w, h = box[s["id"]]
        t = s["type"]
        if t == "agentic":
            f, st = COLORS["agentic_" + s.get("zone", "AMBER")]
        else:
            f, st = COLORS[t]
        lab = None
        if t in ("start", "end"):
            lab = (x - 40, y_ + h + 4, w + 80)
        elif t == "gateway":
            lab = (x - 30, y_ - 30, w + 60)
        shape("Node_%s" % s["id"], x, y_, w, h, f, st, label=lab)
    for sid, (x, y_, w, h) in ann.items():
        shape("Ann_%s" % sid, x, y_, w, h)

    def edge(eid, pts):
        e = ET.SubElement(plane, q("bpmndi", "BPMNEdge"), {"id": "Edge_%s" % eid, "bpmnElement": eid})
        for px, py in pts:
            ET.SubElement(e, q("di", "waypoint"), {"x": "%.0f" % px, "y": "%.0f" % py})

    for fid, a, b, cond in flows:
        ax, ay, aw, ah = box[a]
        bx, by, bw, bh = box[b]
        if (a, b) in back or layer[b] <= layer[a]:
            low = max(ay + ah, by + bh) + 26
            edge(fid, [(ax + aw / 2, ay + ah), (ax + aw / 2, low), (bx + bw / 2, low), (bx + bw / 2, by + bh)])
        else:
            sx, sy, tx, ty = ax + aw, ay + ah / 2, bx, by + bh / 2
            if abs(sy - ty) < 1:
                edge(fid, [(sx, sy), (tx, ty)])
            else:
                mx = tx - 40
                edge(fid, [(sx, sy), (mx, sy), (mx, ty), (tx, ty)])
    for sid, (x, y_, w, h) in ann.items():
        ax, ay, aw, ah = box[sid]
        edge("Assoc_%s" % sid, [(ax + aw / 2, ay), (x + w / 2, y_ + h)])

    if hasattr(ET, "indent"):
        ET.indent(defs, space="  ")
    xml = ET.tostring(defs, encoding="unicode", xml_declaration=False)
    out_path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + xml + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(kc.run(build))
