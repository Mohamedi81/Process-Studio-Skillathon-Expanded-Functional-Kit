#!/usr/bin/env python3
"""Render the reporting requirements pack (HTML) from kit-spec.json.

Each report shows its wireframe, the use cases and screens it serves, the KPI
definitions with formulas and sources, dimensions, filters, refresh and access.

Usage: python3 build_reporting.py --input kit-spec.json --output reporting-requirements.html
Exit 0: output written. Exit 1: every spec problem printed to stderr.
"""
import kit_common as kc
import kit_html as kh
import kit_svg as ks

DEFAULT_OUTPUT_NAME = "reporting-requirements.html"


def build(spec, out_path):
    th = kc.theme_of(spec)
    meta = spec["meta"]
    lanes = {l["id"]: l["name"] for l in spec["lanes"]}
    ucs = kc.index_by(spec["use_cases"])
    screens = kc.index_by(spec["screens"])
    refs = kc.entity_refs(spec)

    summary = kh.table(["Report", "Question it answers", "Audience", "Use cases", "Wireframes it serves", "Refresh"], [
        [r["id"] + " " + r["title"], r["question"], lanes[r["lane"]], ", ".join(r["use_case_ids"]), ", ".join(r["screen_ids"]), r["refresh"]]
        for r in spec["reports"]])
    body = ['<nav class="index">%s</nav>' % "".join('<a href="#%s">%s</a>' % (kc.esc(r["id"]), kc.esc(r["title"])) for r in spec["reports"]),
            '<section class="card"><h3>Report catalogue</h3><div class="side">%s</div></section>' % summary]
    for r in spec["reports"]:
        frame = ks.report_as_screen(r, spec)
        svg, w, h = ks.screen_frame(frame, th, lanes[r["lane"]], th["brand_name"])
        kpi_rows = []
        for k in r["kpis"]:
            kpi_rows.append([k["name"], k["definition"], kh.raw("<code>%s</code>" % kc.esc(k["formula"])), k["unit"], k.get("target", "-"),
                             ", ".join(k.get("refs", []) or []) or "-", k["source"]])
        uc_rows = [[u, ucs[u]["title"], ucs[u]["success_measure"]] for u in r["use_case_ids"]]
        sc_rows = [[s, screens[s]["title"]] for s in r["screen_ids"]]
        dims = kh.table(["Item", "Value"], [
            ["Dimensions", ", ".join(r["dimensions"])], ["Filters", ", ".join(r.get("filters", [])) or "-"],
            ["Refresh", r["refresh"]], ["Access", r["access"]], ["Export", ", ".join(r.get("exports", [])) or "-"],
            ["Alerts", "; ".join(r.get("alerts", [])) or "-"], ["Drill-down", r.get("drill_down", "-")]])
        side = ("<h4>Business question</h4><p>%s</p><h4>Use cases served</h4>%s<h4>Wireframes served</h4>%s<h4>Report definition</h4>%s"
                % (kc.esc(r["question"]), kh.table(["ID", "Use case", "Success measure"], uc_rows), kh.table(["Screen", "Title"], sc_rows), dims))
        data_rows = []
        for k in r["kpis"]:
            for rf in k.get("refs", []) or []:
                e, f = refs[rf]
                data_rows.append([k["name"], rf, f["label"], e.get("system_of_record", "")])
        full = ('<section class="card" id="%s"><h3>%s <small>%s | %s</small></h3><div class="grid"><div class="shot">'
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="%s">%s</svg></div><div class="side">%s</div></div>'
                '<div class="side" style="border-top:1px solid %s"><h4>KPI definitions</h4>%s<h4>Data lineage (dictionary fields behind the KPIs)</h4>%s</div></section>'
                % (kc.esc(r["id"]), kc.esc(r["title"]), kc.esc(r["id"]), kc.esc(lanes[r["lane"]]), w, h, kc.esc(th["font"]), svg, side, th["border"],
                   kh.table(["KPI", "Definition", "Formula", "Unit", "Target", "Dictionary fields", "Source"], kpi_rows),
                   kh.table(["KPI", "Ref", "Field", "System of record"], data_rows) if data_rows else "<p>No dictionary fields declared.</p>"))
        body.append(full)
    note = "Look and feel: %s. %s" % (th["source"], meta.get("illustrative_note", "Report figures on wireframes are illustrative; targets not found in the source are marked assumed."))
    out_path.write_text(kh.page("%s: reporting requirements" % meta["title"], "%s | %s" % (meta["industry"], meta["blueprint_name"]), th, "".join(body), note), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(kc.run(build))
