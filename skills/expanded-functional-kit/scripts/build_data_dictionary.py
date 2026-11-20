#!/usr/bin/env python3
"""Render the industry data dictionary workbook (screens and flow) from kit-spec.json.

Sheets: Read Me, Entities, Data Dictionary, Enumerations, Screen Fields, Flow Data,
HITL Contracts, Use Cases, Traceability. Every row traces to a screen, a flow step
or both, so the dictionary serves the wireframes and the BPMN.

Usage: python3 build_data_dictionary.py --input kit-spec.json --output data-dictionary.xlsx
Exit 0: output written. Exit 1: every spec problem printed to stderr.
"""
import kit_common as kc
import kit_xlsx as kx

DEFAULT_OUTPUT_NAME = "data-dictionary.xlsx"


def build(spec, out_path):
    th = kc.theme_of(spec)
    meta = spec["meta"]
    ents = kc.index_by(spec["entities"])
    refs = kc.entity_refs(spec)
    maps = spec["mappings"]
    steps = spec["steps"]
    screens = kc.index_by(spec["screens"])

    # reverse indexes: field ref -> screens / steps / integrations / reports
    f_screens, f_steps, f_integ, f_reports = {}, {}, {}, {}

    def add(d, k, v):
        d.setdefault(k, [])
        if v not in d[k]:
            d[k].append(v)

    for m in maps:
        add(f_screens, m["ref"], m["screen_id"])
        add(f_integ, m["ref"], m["integration_id"])
    for kind, owner, c in kc.walk_components(spec):
        refs_here = []
        if c["type"] == "table":
            refs_here = [r for r in c.get("refs", []) or [] if r]
        if c["type"] == "form":
            refs_here = [f["ref"] for f in c["fields"] if f.get("ref")]
        for r in refs_here:
            add(f_screens if kind == "screen" else f_reports, r, owner)
    for r in spec["reports"]:
        for k in r["kpis"]:
            for rf in k.get("refs", []) or []:
                add(f_reports, rf, r["id"])
    for s in steps:
        for rf in s.get("reads", []) or []:
            add(f_steps, rf, s["id"])
        for rf in s.get("writes", []) or []:
            add(f_steps, rf, s["id"])
    for i in spec["integrations"]:
        for sect in ("request", "response"):
            for p in i.get(sect, []) or []:
                if p.get("ref"):
                    add(f_integ, p["ref"], i["id"])

    wb = kx.new_book()
    kx.add_sheet(wb, "Read Me", ["Item", "Value"], [
        ["Title", meta["title"]], ["Industry", meta["industry"]], ["Blueprint", meta["blueprint_name"]],
        ["Version", meta.get("version", "v1")], ["Look and feel source", th["source"]],
        ["Entities", len(spec["entities"])], ["Fields", len(refs)], ["Screens", len(spec["screens"])],
        ["Flow steps", len(steps)], ["Integrations", len(spec["integrations"])],
        ["How to read", "Entities define the business objects. Data Dictionary defines every field once. Screen Fields shows where a field appears on a wireframe. Flow Data shows which step reads or writes it."],
        ["Illustrative data", meta.get("illustrative_note", "Examples and sample values are illustrative unless the source names them.")],
    ], th, {"Item": 26, "Value": 110})

    kx.add_sheet(wb, "Entities", ["Entity ID", "Entity", "Definition", "Owner", "Source of record", "Regulatory class", "Retention", "Fields"], [
        [e["id"], e["name"], e["definition"], e.get("owner", ""), e.get("system_of_record", ""), e.get("regulatory_class", ""),
         e.get("retention", ""), len(e["fields"])] for e in spec["entities"]], th, {"Definition": 60})

    rows = []
    for e in spec["entities"]:
        for f in e["fields"]:
            ref = "%s.%s" % (e["id"], f["name"])
            rows.append([ref, e["name"], f["name"], f["label"], f["definition"], f["type"], "Yes" if f.get("required") else "No",
                         f.get("format", ""), kx.join(f.get("allowed_values")), f.get("example", ""), f.get("validation", ""),
                         f.get("source_system", e.get("system_of_record", "")), f.get("pii", "No"), f.get("owner", e.get("owner", "")),
                         kx.join(f_screens.get(ref)), kx.join(f_steps.get(ref)), kx.join(f_integ.get(ref)), kx.join(f_reports.get(ref))])
    ws = kx.add_sheet(wb, "Data Dictionary", ["Ref", "Entity", "Field", "Label", "Definition", "Type", "Required", "Format", "Allowed values",
                                              "Example (illustrative)", "Validation rule", "Source system", "PII", "Data owner",
                                              "Screens", "Flow steps", "Integrations", "Reports"], rows, th,
                      {"Definition": 55, "Validation rule": 40})

    enum_rows = []
    for e in spec["entities"]:
        for f in e["fields"]:
            if f["type"] == "enum":
                for v in f["allowed_values"]:
                    d = f.get("value_definitions", {}) if isinstance(f.get("value_definitions"), dict) else {}
                    enum_rows.append(["%s.%s" % (e["id"], f["name"]), v, d.get(v, "")])
    kx.add_sheet(wb, "Enumerations", ["Field ref", "Allowed value", "Meaning"], enum_rows, th, {"Meaning": 70})

    sf_rows = []
    for m in maps:
        e, f = refs[m["ref"]]
        sc = screens[m["screen_id"]]
        sf_rows.append([sc["id"], sc["title"], m["ui_field"], m["ref"], f["type"], "Yes" if f.get("required") else "No",
                        m["direction"], "Read-only" if m["direction"] == "read" else "Editable", m.get("transform", "")])
    kx.add_sheet(wb, "Screen Fields", ["Screen", "Screen title", "UI field label", "Dictionary ref", "Type", "Required", "Direction", "Behaviour", "Transform / display rule"], sf_rows, th)

    fd = []
    for s in steps:
        for rf in s.get("reads", []) or []:
            fd.append([s["id"], s["name"], s["type"], s.get("zone", ""), "READS", rf, refs[rf][1]["label"]])
        for rf in s.get("writes", []) or []:
            fd.append([s["id"], s["name"], s["type"], s.get("zone", ""), "WRITES", rf, refs[rf][1]["label"]])
    kx.add_sheet(wb, "Flow Data", ["Step", "Step name", "Type", "Zone", "Access", "Dictionary ref", "Field label"], fd, th, zone_col=3)

    hr = []
    for sc in spec["screens"]:
        for c in sc["components"]:
            if c["type"] == "hitl_panel":
                hr.append([sc["id"], sc["title"], c["agent"], c["zone"], c.get("reviewer", ""), c.get("sla", ""),
                           kx.join([a if isinstance(a, str) else a.get("label", "") for a in c["actions"]]),
                           kx.join(c.get("override_reasons")), c.get("on_sla_breach", "")])
    kx.add_sheet(wb, "HITL Contracts", ["Screen", "Title", "Agent", "Zone", "Reviewer role", "Review SLA", "Decision actions", "Override reason codes", "On SLA breach"], hr, th, zone_col=3)

    lanes = {l["id"]: l["name"] for l in spec["lanes"]}
    kx.add_sheet(wb, "Use Cases", ["Use case", "Title", "Role", "Goal", "Success measure", "Screens", "Flow steps"], [
        [u["id"], u["title"], lanes.get(u["lane"], u["lane"]), u["goal"], u["success_measure"], kx.join(u["screen_ids"]), kx.join(u.get("step_ids"))] for u in spec["use_cases"]], th,
        {"Goal": 50, "Success measure": 40})

    tr = []
    for u in spec["use_cases"]:
        for scid in u["screen_ids"]:
            sts = [s["id"] for s in steps if scid in (s.get("screen_ids") or [])]
            ints = sorted({m["integration_id"] for m in maps if m["screen_id"] == scid})
            reps = [r["id"] for r in spec["reports"] if scid in r["screen_ids"]]
            tr.append([u["id"], scid, kx.join(sts), kx.join(ints), kx.join(reps)])
    kx.add_sheet(wb, "Traceability", ["Use case", "Screen", "Flow steps", "Integrations", "Reports"], tr, th)
    wb.save(str(out_path))


if __name__ == "__main__":
    raise SystemExit(kc.run(build))
