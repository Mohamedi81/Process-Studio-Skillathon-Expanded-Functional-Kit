---
name: expanded-functional-kit
description: Expands a To-Be agentic process blueprint (for example a product-innovation launch blueprint with atomic steps, autonomy zones, human-in-the-loop specs, agents and MCP tools) into a functional requirements kit. Produces an industry data dictionary covering screens and flow (XLSX), rich human-in-the-loop wireframes in the customer's look and feel (HTML plus a Figma-importable SVG), a deterministic BPMN 2.0 file with explicit plug-in points where agentic steps attach, integration mapping sheets for screens and flow (XLSX), and reporting requirements with report wireframes (HTML). Use when the user wants to expand a blueprint into functional requirements, wireframes, data dictionary, BPMN, integration mapping or reporting requirements.
allowed-tools: run_skill_script read_wiki_page write_temp_file read_temp_file save_output_text save_output_file
---

# Expanded Functional Kit

Input: a To-Be blueprint (steps with DETERMINISTIC or AI type, autonomy zones, HITL specification, agents, tools, systems of record, KPIs). Optional: customer look and feel (CSS, HTML of the existing application, brand colours, screenshots described in the context).

Outputs, every run, all built from ONE spec so they stay consistent:
- `data-dictionary.xlsx`: entities, fields, enumerations, screen fields, flow data, HITL contracts, traceability.
- `wireframes.html`: one rich wireframe per screen, with its use cases, flow step, HITL contract, data and integrations.
- `figma-wireframes.svg`: every screen and report as named, editable SVG groups. Drag it onto a Figma canvas.
- `process.bpmn`: BPMN 2.0 with lanes and diagram. Deterministic steps are service or rule tasks, human review steps are user tasks, agentic steps are service tasks with a plug-in point (agent, MCP tool, integration call, fallback).
- `integration-mapping.xlsx`: integration register, UI field to JSON path mapping, flow calls, request and response fields, agentic plug-in points, error and fallback.
- `reporting-requirements.html`: each report with its wireframe, use cases and screens served, KPI formulas, dimensions, refresh and access.

Never write code. You write one JSON file and bundled scripts render every deliverable.

## Do not ask questions
Work from what you were given. Use these defaults and report them in your final message:
- Look and feel: harvested from any CSS, HTML or brand material in the context. Take the primary colour, nav bar colour, text and surface colours, font and corner radius, and record where they came from in `theme.source`. If only screenshots are available, read the colours and layout from them and say that you estimated them. If nothing exists, omit `theme` (a neutral enterprise theme is used) and say so.
- Industry: from the blueprint. Use its vocabulary for entities, fields and enumerations.
- Roles: the human roles in the HITL specification. Screens exist for human decisions only. Deterministic steps get no screen.
- Anything not in the blueprint (field formats, example values, record IDs, figures, protocols, latency) is illustrative or assumed. Say "illustrative" or "assumed" in the text. Never present an invented figure as sourced.

## Steps
1. **Read** the blueprint and any look-and-feel material fully. Use `read_wiki_page` for wiki pages.
2. **Harvest** silently, in this order:
   - Steps: each atomic step with type (DETERMINISTIC or AI), zone, rule or agent, system touched.
   - Roles and agents: they become `lanes`.
   - Human touchpoints: each HITL row becomes a `human` step plus a `hitl_review` screen. Each AMBER or RED step hands over directly to its human step.
   - Systems and tools: each MCP tool or system call becomes an `integrations` entry with `kind` deterministic or agentic.
   - Ontology: core entities and their attributes become `entities` with fields the screens and reports use.
   - KPIs, target outcome and observability: they become `reports`.
3. **Design** (see `references/kit-spec-schema.md` for the rules):
   - Deterministic backbone as `steps`, gateways for decisions, parallel gateways for fan-out and join. Agentic steps are plug-in points.
   - One screen per human decision. Use the `hitl_panel` component for every AMBER or RED review: proposal, evidence with citations, confidence, SLA, override reasons, actions.
   - Every screen field is mapped in `mappings` to an integration field (`json_path`) and a dictionary field (`ref`). No unmapped screen, no orphan integration.
   - 3 to 5 reports. Each serves named use cases and wireframes, has KPI formulas, and includes one report on HITL acceptance and override rates.
4. **Write the spec**: author `kit-spec.json` and save it with `write_temp_file`. Keep strings short. Do not repeat blueprint prose.
5. **Build** each deliverable with `run_skill_script`, one call each, `--input kit-spec.json`:
   - `build_data_dictionary.py` with `--output data-dictionary.xlsx`
   - `build_wireframes.py` with `--output wireframes.html`
   - `build_figma_svg.py` with `--output figma-wireframes.svg`
   - `build_bpmn.py` with `--output process.bpmn`
   - `build_integration_mapping.py` with `--output integration-mapping.xlsx`
   - `build_reporting.py` with `--output reporting-requirements.html`

   The first script that runs validates the spec. If it fails, the error lists every issue. Fix `kit-spec.json`, save it again and re-run. Repeat until it passes. All six scripts then pass.
6. **Deliver**: save all six files with `save_output_file`. Reply with a short summary: number of roles, screens, flow steps (how many deterministic, agentic, human), integrations (how many agentic plug-in points), reports; which look and feel was used and where it came from; the defaults and assumptions used; which figures are illustrative; and how to import the SVG into Figma.

## Rules
- **No emojis or pictograph glyphs** anywhere. The build fails on them. Use words.
- Every agentic step needs a direct hand-over to a human step and `integration_ids` with `kind: agentic` and an `mcp_tool`. Deterministic steps need a `rule` and zone GREEN.
- RED-zone panels never offer "approve" or "cleared" as the agent's verdict. The agent proposes, the named role decides.
- Reuse the blueprint's IDs (ATS, AGN, TOL, DPS) in names so the kit traces back to it.
- Text in wireframes is plain text. Do not put HTML or SVG in any field.
- If the source numbers are from a sample or old period, say so in `meta.illustrative_note`.

## Example
`examples/drinkit-innovation-launch/` holds a complete `kit-spec.json` and its six outputs. Learn the structure from them. Never copy their content, names or numbers.
