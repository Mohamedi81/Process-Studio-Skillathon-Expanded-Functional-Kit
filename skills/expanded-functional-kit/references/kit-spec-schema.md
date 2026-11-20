# kit-spec.json schema

One JSON file drives all six scripts. Top-level keys, all required except `theme`:
`meta`, `theme`, `lanes`, `entities`, `integrations`, `steps`, `screens`, `mappings`, `use_cases`, `reports`.
JSON only: no comments in the real file, escape double quotes inside strings. No emojis.

## meta
```
"meta": { "title": "...", "industry": "...", "blueprint_name": "<source file name>", "version": "v1",
          "illustrative_note": "Record IDs and figures on screens are illustrative.",
          "integration_note": "Protocols marked assumed in the blueprint remain assumptions." }
```
Required: `title`, `industry`, `blueprint_name`.

## theme (customer look and feel)
Harvest from CSS custom properties, the most used hex colours, the font stack and the corner radius of the supplied HTML. Say where in `source`.
```
"theme": { "brand_name": "...", "source": "Harvested from <file>: <what>", "font": "<CSS font stack>", "font_figma": "<first font>",
           "primary": "#0052cc", "primary_dark": "#0747a6", "nav_bg": "#0052cc", "nav_text": "#ffffff",
           "bg": "#f4f5f7", "surface": "#ffffff", "text": "#172b4d", "muted": "#6b778c", "border": "#dfe1e6",
           "success": "#006644", "warning": "#f6c900", "danger": "#ff5630", "radius": 4 }
```
All colours are `#rrggbb`. Every key is optional; missing keys take a neutral default. Screenshots only: estimate colours from the image and say "estimated from screenshot" in `source`.

## lanes
`{ "id": "pmi", "name": "Innovation Project Manager (PM-I)", "kind": "role|agent|system" }`. One per human role, agent, and one `system` lane for the deterministic rule engine.

## entities
```
{ "id": "IDEA", "name": "Idea", "definition": "...", "owner": "...", "system_of_record": "...", "regulatory_class": "...", "retention": "...",
  "fields": [ { "name": "idea_id", "label": "Idea ID", "definition": "...", "type": "id", "required": true,
                "format": "IDX-YYYY-nnn", "example": "IDX-2026-041", "validation": "...", "pii": "No",
                "allowed_values": ["..."], "value_definitions": {"value": "meaning"} } ] }
```
Field `type`: id, string, text, integer, decimal, currency, percentage, date, datetime, boolean, enum, url, json. An `enum` needs `allowed_values`. A field is referenced everywhere as `ENTITYID.field_name`, for example `IDEA.idea_id`.
Use the blueprint's ontology and data products for entities, owners, systems of record, classes and retention.

## integrations
```
{ "id": "INT_DUP", "name": "...", "kind": "deterministic|agentic", "system": "...", "operation": "...",
  "pattern": "rest_api|mcp_tool|event|file|batch|database", "protocol": "...", "direction": "read|write|both",
  "auth": "...", "latency": "...", "mcp_tool": "TOL2 ...", "fallback": "...", "idempotency": "...", "constraints": "...",
  "request":  [ { "field": "idea_id", "ref": "IDEA.idea_id", "type": "string", "required": true, "description": "..." } ],
  "response": [ { "field": "matches[].similarity", "ref": "DUP.similarity", "type": "decimal" } ],
  "errors": [ { "code": "MODEL_TIMEOUT", "detection": "...", "response": "...", "fallback": "..." } ] }
```
Required: `name`, `kind`, `system`, `operation`, `pattern`, `protocol`, `direction`, `auth`, `latency`. `agentic` needs `mcp_tool`. `field` is the JSON path used in `mappings`. Every integration must be used by a step.

## steps (the deterministic flow)
```
{ "id": "S02", "name": "ATS2 Detect duplicate and related ideas", "type": "start|end|deterministic|agentic|human|gateway",
  "lane": "agn1", "description": "...", "next": [ {"to": "S03"} ], "zone": "GREEN|AMBER|RED",
  "integration_ids": ["INT_DUP"], "reads": ["IDEA.title"], "writes": ["DUP.relation"] }
```
- `deterministic`: needs `rule` (the codified rule) and zone GREEN. Optional `integration_ids`.
- `agentic`: needs `agent`, zone AMBER or RED, `integration_ids` (all `kind: agentic`), and a `next` that includes a `human` step. Add `input_contract`, `output_contract`, `fallback`.
- `human`: needs `screen_ids` and `sla`. Zone is the zone of the step it reviews.
- `gateway`: needs `gateway: "xor"` (every `next` has a `condition`) or `"and"` (parallel fan-out or join). A non-gateway step has exactly one `next`; use a gateway to split.
- `start` and `end` have no `next` on `end`. Every step must be reachable from a start. Loops are allowed (a `next` may point backwards).

## screens
```
{ "id": "SCR_DUP", "title": "...", "purpose": "...", "lane": "pmi", "pattern": "queue|review|hitl_review|form|detail|dashboard",
  "url_path": "ideas/IDX-2026-041/duplicates", "nav": ["Ideas", "..."], "active_nav": "Ideas",
  "status": {"text": "AMBER review", "tone": "amber"}, "notes": ["design note"], "components": [ ... ] }
```
`active_nav` must be in `nav`. Every screen must be opened by a human step, belong to a use case and have mapping rows. A `hitl_review` screen needs a `hitl_panel`.

### components (12-column grid; optional `span` 1-12, default 12; optional `title`)
| type | required keys | notes |
|---|---|---|
| `banner` | `text` | `tone`: green, amber, red, blue, grey |
| `stepper` | `items` (labels) | `active` index |
| `tabs` | `items` | `active` index |
| `kpis` | `items` [{label, value, delta, tone}] | 3 to 5 tiles |
| `table` | `headers`, `rows` | cell = string or {text, tone}; optional `refs` (one dictionary ref per column, "" if none); every row same length as headers |
| `form` | `fields` [{label, type, value, ref, required}] | type: text, select, date, number, textarea, checkbox, readonly |
| `hitl_panel` | `agent`, `zone` (AMBER or RED), `proposal`, `actions` | plus `evidence` [text], `confidence`, `reviewer`, `sla`, `override_reasons` [text], `on_sla_breach`. Last action is the primary button |
| `bar_chart` | `items` [{label, value, display, tone}] | numeric `value` |
| `line_chart` | `items` [{label, value}] | optional `target` |
| `donut_chart` | `items` [{label, value, tone}] | optional `center` |
| `timeline` | `items` [{label, detail, tone}] | |
| `filters` | `items` | labels only |
| `actions` | `items` | strings or {label, style: primary|secondary|danger} |
| `text` | `text` | |

## mappings (every screen field to an integration field and a dictionary field)
`{ "screen_id": "SCR_DUP", "ui_field": "Similarity", "integration_id": "INT_DUP", "json_path": "matches[].similarity", "ref": "DUP.similarity", "direction": "read|write|both", "transform": "...", "trigger": "..." }`
- `direction read` means `json_path` must be a `response` field of that integration. `write` means a `request` field. `both` means either.
- If the integration field has a `ref`, the mapping `ref` must be equal.
- Every screen needs at least one row. Map the data fields a person reads or enters, including the decision actions.

## use_cases
`{ "id": "UC01", "title": "...", "lane": "pmi", "goal": "...", "success_measure": "...", "screen_ids": ["SCR_DUP"], "step_ids": ["S02", "S03"] }`. Every screen belongs to one use case, and every use case is served by at least one report.

## reports
```
{ "id": "RPT01", "title": "...", "lane": "pmi", "question": "...", "use_case_ids": ["UC01"], "screen_ids": ["SCR_DUP"],
  "dimensions": ["Month", "Brand"], "filters": ["Brand"], "refresh": "...", "access": "...", "exports": ["XLSX"],
  "alerts": ["..."], "drill_down": "...", "nav": ["..."],
  "components": [ ...same as screens... ],
  "kpis": [ { "name": "...", "definition": "...", "formula": "COUNT(x) / COUNT(y)", "unit": "%", "source": "...", "refs": ["IDEA.idea_id"], "target": "..." } ] }
```
Required per KPI: `name`, `definition`, `formula`, `unit`, `source`. `screen_ids` names the wireframes the report serves (drill-down targets). Mark targets not in the blueprint "assumed".

## What the scripts check
Unknown or duplicate IDs, unreachable steps, agentic steps without a human hand-over, XOR gateways without conditions, orphan screens, screens without mappings or use case, mappings whose `json_path` is not an integration field, unused integrations, use cases without a report, bad hex colours, table rows with the wrong width, and emojis. All problems are listed at once.
