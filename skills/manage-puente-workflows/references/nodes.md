# Puente workflow nodes

## Contents

- Public source of truth
- Discover node types
- Catalog response
- Saved node shape
- Python script nodes
- Inputs and references
- Edges
- Safe authoring

## Public source of truth

External Puente Studio users discover nodes through the authenticated public API:

```http
GET /workflows/integrations
X-API-Key: <STUDIO_KEY>
```

Use exported `BASE_URL` and `STUDIO_KEY` values or read them from the current project's ignored `.env`. Send the Studio Key as `X-API-Key`. No backend repository, database access, user login, or bearer token is required.

The integrations response is the source of truth for:

- currently available `node_id` values;
- the node `type` and display `category`;
- supported inputs, defaults, options, and required fields;
- node catalog versions and display metadata.

The public `GET /openapi.json` contract is the source of truth for the
persisted `WorkflowNode` and `ScenarioCreate` shapes. Its top-level
`x-puente-integration-actions` map publishes action contracts keyed by
`node_id`. Each entry can include:

- `action_name`: human-readable action name;
- `mutates`: whether the action writes provider state;
- `manual_execution_allowed`: whether the editor may execute the node by itself;
- `input_schema`: exact runtime-validation JSON Schema;
- `output_schema`: fields the action publishes to downstream workflow context;
- `vue_input_schema`: editor-oriented input controls and reference support.

Use OpenAPI for output fields and top-level node fields such as `script_code`.
`manual_execution_allowed` is metadata, not permission for this management
skill to call a non-public execution endpoint.

Never depend on internal backend code, migrations, database rows, private templates, or hard-coded node lists. Never invent a `node_id` or an input field.

## Discover node types

Node types are dynamic. Read them from the current integrations response instead of maintaining a fixed list in this skill.

For example, an external user may retrieve and summarize the public response with standard HTTP and JSON tools:

```bash
curl -fsS "${BASE_URL%/}/workflows/integrations" \
  -H "Accept: application/json" \
  -H "X-API-Key: $STUDIO_KEY" |
  jq 'sort_by(.type, .category, .app_name) | group_by(.type) | map({type: .[0].type, nodes: map({node_id, app_name, action_name, category})})'
```

Choose a node by its `node_id`, `app_name`, `action_name`, `type`, and `category`. Do not infer unsupported behavior from the type name alone. Read its `input_schema` before constructing `inputs`. When OpenAPI has an `x-puente-integration-actions[node_id]` entry, require the same `node_id` to exist in both surfaces before authoring the node; use the authenticated catalog as the saved/selectable node authority and the OpenAPI extension for runtime and output detail.

## Catalog response

Each public catalog item has this shape:

```json
{
  "node_id": "<catalog-node-id>",
  "app_name": "<application name>",
  "action_name": "<action name>",
  "type": "<catalog type>",
  "category": "<display category>",
  "icon_url": "https://...",
  "background_color": "#FFFFFF",
  "version": 1,
  "input_schema": [
    {
      "name": "<input-name>",
      "type": "string",
      "label": "<display label>",
      "required": true
    }
  ]
}
```

Common `input_schema` metadata includes:

- `name`: exact key to place in the saved node's `inputs` object;
- `type`: expected input kind;
- `required`: whether a value is required;
- `default`: value to use when the user has not supplied one;
- `options`: allowed choices for dropdown-like inputs;
- `label` and `description`: user-facing guidance;
- conditional display metadata when one field depends on another.

Only use fields present in the returned schema. Integration inputs are exact contracts, and extra fields can be rejected. Internal implementation fields are intentionally unavailable through this interface.

## Saved node shape

Create a new saved node from public catalog data with:

```json
{
  "label": "selected_action",
  "node_id": "<node_id-from-integrations>",
  "inputs": {
    "<schema-field-name>": "<user-supplied-value>"
  },
  "script_code": null,
  "on_error": "stop",
  "position": {"x": 400, "y": 0},
  "index_position": 1
}
```

| Field | External contract |
|---|---|
| `label` | Stable name used to identify this node inside the workflow. |
| `node_id` | Exact identifier returned by `integrations`. |
| `inputs` | Object constructed only from the selected node's current `input_schema`. |
| `script_code` | Optional top-level persisted node field documented by `GET /openapi.json`; it is not an `inputs` key. Use it for the script of a catalog node whose `node_type` is `CODE`, such as `core.python_code` or `core.headless_browser`. |
| `on_error` | Use `stop` by default. Use `continue` only when the user explicitly wants later nodes to proceed after failure. |
| `position` | Optional visual-editor coordinates. |
| `index_position` | Optional canvas index used with the label to identify the node in references and edges. |

For an existing workflow version, preserve the complete saved node objects returned by the API and change only the fields required by the user's requested definition update.

## Code nodes

Code nodes are the catalog entries whose `node_type` is `CODE`:
`core.python_code` runs plain Python and `core.headless_browser` runs Python
with Playwright and Chromium. Confirm the node in the live catalog and the
top-level `script_code` field in `GET /openapi.json` before saving. The
catalog's `input_schema` controls only `inputs`; it can be empty while the node
still accepts `script_code`. When the catalog returns a `code_template`, use it
as the starting script.

Place the source string in `script_code`, not in `inputs`. Puente injects
three variables before the script runs:

| Variable | Content |
| --- | --- |
| `inputs` | The node's resolved `inputs` object |
| `variables` | Outputs of earlier nodes and the trigger, by context key |
| `contexto` | `{**variables, **inputs}` |

Read earlier nodes with the same key a reference would use:
`contexto["consulta_sql_3"]["filas"]` instead of `{{consulta_sql_3.filas}}`.
Triggers use only their name, such as `contexto["webhook"]`. Never write
`{{ }}` inside `script_code`: it is not resolved there, and in other code
inputs resolved values are inserted without quotes, which can break or inject
code. Print only the final JSON with `print(json.dumps(...))`; send debugging
output to `sys.stderr`. Do not write credentials into the script.

Before saving any code node, run the bundled checker with the node's
`node_id`:

```bash
python3 <skill-directory>/scripts/check_code_node.py script.py --node-id core.python_code
```

For `core.headless_browser`, follow [headless-browser.md](headless-browser.md).

## Inputs and references

Build every `inputs` key from `input_schema`. Ask the user for missing required values; do not fabricate credentials, URLs, table IDs, model selections, recipient identifiers, or other operational data.

A later node can reference an earlier node's output with the workflow context-key syntax:

```text
{{context_key.field}}
{{context_key.items[0].id}}
```

The context key is:

- `label` when `index_position` is `null`;
- `label_index_position` when an index exists.

Examples:

```text
label="start", index_position=null -> start
label="selected_action", index_position=1 -> selected_action_1
```

When the whole input value is one reference, the referenced value can remain an object, array, number, boolean, or string. Embedded references become text.

The integrations catalog describes saved/selectable inputs; formal action outputs are published separately in `GET /openapi.json` under `x-puente-integration-actions[node_id].output_schema`. Cross-check the `node_id` in both surfaces before using those fields. When no output schema is published for an action, do not guess output field names; use references already present in a saved workflow or output behavior documented through another approved public Puente interface.

Keep labels and indexes unique and stable. If either changes, update every corresponding reference and edge.

## Querying protected table fields

For the catalog node displayed as **Puente -> Query / Leer Datos**, inspect the
live `input_schema`. When it contains `decrypt_encrypted_fields`, it is an
optional boolean that defaults to `false`.

Use `decrypt_encrypted_fields: true` only after the workflow author confirms
that the workflow needs the real value of a column created with
`encrypt_at_rest: true`. The backend decrypts protected fields only after the
allowed table query has returned rows, and only for fields included in the
node's `fields` projection. The ciphertext remains stored in the table.

The result is normal workflow context, so later nodes can reference it through
the usual context-key syntax and authorized readers can see it in workflow
execution history. Do not describe that as masked data: a subsequent HTTP,
agent, webhook, or integration node may deliberately disclose it.

Keep `fields` and `limit` as small as the workflow needs. A query cannot use a
protected field for filters, sorting, grouping, aggregation, or Top-N. The
node rejects more than 1,000 protected non-null cells and fails the whole node
with `Failed to decrypt` when any selected protected value cannot be
decrypted. Do not rely on partial rows.

This input does not change the Studio table API or a published application's
table API: those ordinary reads continue to return `kms:v1:...` ciphertext.

## Edges

Edges use workflow context keys, not catalog `node_id` values:

```json
{
  "source": "start",
  "target": "selected_action_1"
}
```

Preserve the complete `edges` array when versioning. When adding a connection, use the exact source and target context keys. When a node label or `index_position` changes, update its edge endpoints.

Do not use edges to invent branching, looping, or execution behavior that is not represented by nodes returned from the integrations API.

## Safe authoring

1. Request `GET /workflows/integrations` and use its returned catalog.
2. Select only a returned `node_id`.
3. When OpenAPI publishes `x-puente-integration-actions[node_id]`, cross-check
   the same ID and read its runtime input/output schemas and action metadata.
4. Build `inputs` only from the exact action contract. For a Python script,
   separately validate the top-level `script_code` field in `GET /openapi.json`.
5. Ask for every missing required operational value.
6. Default `on_error` to `stop`.
7. Keep new or changed workflows in `draft` unless activation is explicitly requested and confirmed.
8. Show the complete method, path, and JSON payload before sending a create/version request when confirmation is needed.
9. Preserve complete saved nodes and edges when creating a new version.
10. Never call workflow execution, trigger, webhook, schedule, or deletion endpoints.
