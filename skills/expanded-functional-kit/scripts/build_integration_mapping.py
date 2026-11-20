#!/usr/bin/env python3
"""Render the integration mapping workbook (screens and flow) from kit-spec.json.

Sheets: Read Me, Integration Register, Screen Mapping, Flow Calls, Request Fields,
Response Fields, Agentic Plug-in Points, Error and Fallback. The Screen Mapping
sheet maps every UI field to a JSON path of an integration and a dictionary field.

Usage: python3 build_integration_mapping.py --input kit-spec.json --output integration-mapping.xlsx
Exit 0: output written. Exit 1: every spec problem printed to stderr.
"""
import kit_common as kc
import kit_xlsx as kx

DEFAULT_OUTPUT_NAME = "integration-mapping.xlsx"


def build(spec, out_path):
    th = kc.theme_of(spec)
    meta = spec["meta"]
    integ = kc.index_by(spec["integrations"])
    screens = kc.index_by(spec["screens"])
    steps = kc.index_by(spec["steps"])
    refs = kc.entity_refs(spec)
    used_by = {}
    for s in spec["steps"]:
        for i in s.get("integration_ids", []) or []:
            used_by.setdefault(i, []).append(s["id"])
    screens_of = kc.screen_integrations(spec)
    on_screens = {}
    for sc, ids in screens_of.items():
        for i in ids:
            on_screens.setdefault(i, []).append(sc)

    wb = kx.new_book()
    kx.add_sheet(wb, "Read Me", ["Item", "Value"], [
        ["Title", meta["title"]], ["Industry", meta["industry"]], ["Blueprint", meta["blueprint_name"]],
        ["Integrations", len(integ)], ["Deterministic calls", sum(1 for i in integ.values() if i["kind"] == "deterministic")],
        ["Agentic plug-in calls", sum(1 for i in integ.values() if i["kind"] == "agentic")],
        ["Mapping rows", len(spec["mappings"])],
        ["How to read", "Integration Register lists each call once. Screen Mapping binds each UI field to a JSON path and a dictionary field. Flow Calls binds calls to BPMN steps. Agentic Plug-in Points are where agent orchestration attaches to the deterministic backbone."],
        ["Assumptions", meta.get("integration_note", "Protocols, authentication and latency not stated in the source are assumptions to confirm with the integration team.")],
    ], th, {"Item": 26, "Value": 110})

    kx.add_sheet(wb, "Integration Register", ["ID", "Name", "Kind", "System", "Operation", "Pattern", "Protocol", "Direction", "Authentication",
                                              "Latency", "Idempotency / lock handling", "MCP tool", "Used by steps", "Shown on screens", "Constraints"], [
        [i["id"], i["name"], i["kind"], i["system"], i["operation"], i["pattern"], i["protocol"], i["direction"], i["auth"], i["latency"],
         i.get("idempotency", ""), i.get("mcp_tool", ""), kx.join(used_by.get(i["id"])), kx.join(on_screens.get(i["id"])), i.get("constraints", "")]
        for i in spec["integrations"]], th, {"Constraints": 50, "Operation": 36})

    kx.add_sheet(wb, "Screen Mapping", ["Screen", "Screen title", "UI field", "Integration", "System", "Direction", "JSON path", "Dictionary ref", "Type",
                                        "Transform / display rule", "Trigger"], [
        [m["screen_id"], screens[m["screen_id"]]["title"], m["ui_field"], m["integration_id"], integ[m["integration_id"]]["system"],
         m["direction"], m["json_path"], m["ref"], refs[m["ref"]][1]["type"], m.get("transform", ""), m.get("trigger", "On screen load" if m["direction"] == "read" else "On action")]
        for m in spec["mappings"]], th, {"JSON path": 40, "Transform / display rule": 40})

    fc = []
    for s in spec["steps"]:
        for iid in s.get("integration_ids", []) or []:
            i = integ[iid]
            fc.append([s["id"], s["name"], s["type"], s.get("zone", ""), iid, i["name"], i["kind"], i["system"], i["operation"],
                       kx.join(s.get("reads")), kx.join(s.get("writes")), kx.join(s.get("screen_ids"))])
    kx.add_sheet(wb, "Flow Calls", ["Step", "Step name", "Type", "Zone", "Integration", "Call", "Kind", "System", "Operation", "Reads", "Writes", "Review screens"], fc, th, zone_col=3)

    for sheet, sect in (("Request Fields", "request"), ("Response Fields", "response")):
        rows = []
        for i in spec["integrations"]:
            for p in i.get(sect, []) or []:
                rf = p.get("ref")
                rows.append([i["id"], i["name"], p["field"], p.get("type", ""), "Yes" if p.get("required") else "No", p.get("description", ""),
                             rf or "", refs[rf][1]["label"] if rf in refs else ""])
        kx.add_sheet(wb, sheet, ["Integration", "Call", "Parameter / JSON path", "Type", "Required", "Description", "Dictionary ref", "Dictionary label"], rows, th, {"Description": 50})

    ag = []
    for s in spec["steps"]:
        if s["type"] != "agentic":
            continue
        nxt = [steps[n["to"]]["id"] + " " + steps[n["to"]]["name"] for n in s["next"]]
        for iid in s["integration_ids"]:
            i = integ[iid]
            ag.append([s["id"], s["name"], s["agent"], s["zone"], iid, i["mcp_tool"], i["system"], i["operation"], i["protocol"],
                       s.get("input_contract", ""), s.get("output_contract", ""), s.get("fallback") or i.get("fallback", ""), kx.join(nxt), kx.join(s.get("screen_ids"))])
    kx.add_sheet(wb, "Agentic Plug-in Points", ["Step", "Step name", "Agent", "Zone", "Integration", "MCP tool", "System", "Operation", "Protocol",
                                                "Input contract", "Output contract", "Fallback", "Hands over to (HITL)", "Review screens"], ag, th, {"Input contract": 45, "Output contract": 45}, zone_col=3)

    er = []
    for i in spec["integrations"]:
        for e in i.get("errors", []) or []:
            er.append([i["id"], i["name"], e.get("code", ""), e.get("detection", ""), e.get("response", ""), e.get("fallback", "")])
    kx.add_sheet(wb, "Error and Fallback", ["Integration", "Call", "Error code / mode", "Detection", "Automated response", "Human fallback"], er, th, {"Detection": 40, "Automated response": 45, "Human fallback": 45})
    wb.save(str(out_path))


if __name__ == "__main__":
    raise SystemExit(kc.run(build))
