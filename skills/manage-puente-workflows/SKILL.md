---
name: manage-puente-workflows
description: Manage Puente workflow definitions and connection-backed workflow integrations with a Puente Studio credential. Use when an external Puente Studio user needs to configure Gmail or Google Sheets connections and nodes, reuse or authorize an integration account, diagnose failed or stuck workflows from supplied error details, inspect workflows, create a draft or complete new version, connect nodes and edges, or change a saved workflow version's status. Disclose automatic Puente webhook and scheduling side effects, require explicit activation confirmation, and never call workflow run endpoints.
---

# Manage Puente Workflows

Manage saved workflow definitions for the team attached to the configured Studio credential. Do not directly call workflow execution, trigger, webhook, schedule, or deletion endpoints. Account for lifecycle side effects performed automatically by the Puente API during definition writes.

## Diagnose a workflow error

For a failed or stuck workflow, read [references/troubleshooting.md](references/troubleshooting.md), then the matching entry in [references/errors.md](references/errors.md). Explain the message, likely cause, user action, and retry conditions. Distinguish API responses and saved step errors from internal log messages.

Interpret supplied error details without credentials. Load configuration only when a supported definition or integration request is necessary. A Studio key does not grant access to the JWT-protected execution-detail route. Do not call execution routes or rerun workflows through this skill.

## Read configuration

For supported API requests, use already-exported `BASE_URL` and `STUDIO_KEY` values or read them from the current project's ignored `.env` file. Never read configuration from the installed marketplace or plugin-cache directory. Stop the API operation if either value is missing or still contains a placeholder. You can still explain supplied error details.

Authenticate every request with:

```http
X-API-Key: <STUDIO_KEY>
```

Never print the key, place it in a URL, write it into generated source code, or include it in reports.

## Load the contract

Read [references/api.md](references/api.md) before preparing a workflow-definition request. Read [references/nodes.md](references/nodes.md) before creating or changing `nodes`, `edges`, node inputs, or cross-node references.

For any connection-backed integration, first read [references/integrations.md](references/integrations.md). Then read only the selected provider reference: [references/gmail.md](references/gmail.md) for Gmail or [references/google-sheets.md](references/google-sheets.md) for Google Sheets. Do not load every provider reference when only one integration is involved. Use only the public HTTP methods and paths documented in those references.

## Choose an operation

- List saved workflows: call `GET /workflows/`.
- Inspect a version or stable group: call `GET /workflows/?all_versions=true` and filter the returned definitions by `id` or `scenario_group_id`.
- Discover valid node types: call `GET /workflows/integrations`.
- List or select integration connections: use [references/integrations.md](references/integrations.md), then the selected provider reference.
- Connect Gmail or build a Gmail node: read [references/integrations.md](references/integrations.md), then [references/gmail.md](references/gmail.md).
- Connect Google Sheets or build a Sheets node: read [references/integrations.md](references/integrations.md), then [references/google-sheets.md](references/google-sheets.md).
- Create a workflow: call `POST /workflows/` with a complete JSON definition and acknowledged automatic service effects.
- Update a definition: call `POST /workflows/` with the stable `scenario_group_id`, a complete JSON definition, and acknowledged automatic service effects.
- Change saved status: call `PUT /workflows/{scenario_id}/status` with the latest version `id` (`is_latest=true`); an older version returns `409`. Activating requires separate explicit confirmation.
- Delete or run a workflow: state that the operation is outside this skill and do nothing. Deleting the current version of an active workflow with several versions returns `409`; it must be deactivated first.

## Before changing a definition

1. Inspect the current saved definition through `GET /workflows/?all_versions=true`.
2. Validate every `node_id` through `GET /workflows/integrations`; never invent node types. When the request involves node-level code, inspect `GET /openapi.json` too: `script_code` is a persisted `WorkflowNode` field, not an integration `inputs` field.
3. Preserve the complete `nodes` and `edges` arrays when creating a new version.
4. Default new definitions and versions to `draft` unless the user explicitly requests another saved status.
5. Explain that `POST /workflows/` automatically generates or inherits Puente synchronous-webhook metadata. This can expose a fixed Puente webhook endpoint even while the workflow remains a draft. Saving an active definition with a `trigger.schedule` node also creates or updates its schedule.
6. Obtain explicit user confirmation of those effects before sending a create/version request.
7. If any create/version payload uses `status: "active"`, obtain separate explicit confirmation of activation.
8. Show the intended HTTP method, path, and JSON body without sending it when the requested change is ambiguous or needs confirmation.
9. Send the mutation once. If the response is interrupted, read the saved state instead of retrying automatically.
10. Read the saved definition back and verify identifiers, version, team, and status.

This is the concrete behavior previously described as “guard writes”: inspect, preview when needed, write once, and verify. It is an agent safety procedure, not an API feature.

## Preserve version semantics

Treat `scenario_group_id` as the stable workflow identity and `id` as one saved version.

- Omit `scenario_group_id` to create a new workflow at version 1.
- Include the existing `scenario_group_id` to create the next version.
- Send every node and edge on each new version; never send a partial patch.
- Save both identifiers from the response.
- Expect the new version to have `is_latest=true`.

The Studio credential is bound to one team. Omit `equipo_id` to use that team. Never attempt another team ID.

## Build workflow URLs

Treat the configured API origin as the source of truth. The only supported
origins for user-facing webhook links are:

- Production: `https://api.puente.xyz`
- Staging: `https://staging.puente.xyz`

After a successful create or version write and read-back:

1. Use `sync_webhook_id` to build the Puente webhook endpoint as
   `{api_origin}/workflows/webhook/{sync_webhook_id}`.
2. Prefer that derived endpoint over the response's legacy `webhook_url`.
3. Never rewrite the endpoint to another webhook host or report a webhook
   subdomain. If the configured origin is not one of the two supported origins,
   do not invent or expose an external webhook URL.
4. Distinguish the webhook endpoint from the workflow editor URL. They serve
   different purposes.
5. For production only, build the frontend editor URL as
   `https://app.puente.xyz/workflows/{scenario_group_id}/edit` and show it as a
   clickable link. The UUID is the stable `scenario_group_id`, not the saved
   version `id`.
6. For staging, report the Puente staging webhook endpoint when available, but
   do not invent a staging frontend host or substitute the production editor
   URL unless a current public contract documents that mapping.

If `sync_webhook_id` or `scenario_group_id` is absent, state that the
corresponding URL could not be derived instead of guessing.

## Distinguish management from execution

Do not directly call workflow execution, trigger, webhook, cron, schedule, or run endpoints. The Puente API manages schedules from definition writes, including those made with a Studio credential, so no separate cron call is needed.

Definition management can still change runtime eligibility:

- Creating or versioning causes the automatic webhook and metadata behavior described above.
- Saving `status: "active"` does not execute immediately, but it enables existing external triggers or synchronous webhooks to execute that workflow. Saving or activating a definition with a `trigger.schedule` node creates or updates its schedule; see the schedule rules in [references/api.md](references/api.md).

Require explicit user confirmation for every transition or create/version payload that saves an active status. Never describe activation as inert metadata.

## Protected table values in workflows

The `Puente -> Query / Leer Datos` node may expose the real values of columns
created with `encrypt_at_rest: true`, but only when its **live catalog** exposes
the optional boolean input `decrypt_encrypted_fields` and the workflow author
explicitly sets it to `true`.

- The default is `false`: a table query receives the opaque `kms:v1:...`
  ciphertext, exactly like the Studio table API.
- With `true`, the backend reads the permitted table rows, then decrypts only
  protected columns included by the query's `fields` projection. The stored
  table row remains encrypted.
- The real values become normal workflow output: later nodes may use them and
  authorized workflow-history readers may see them. This is intentional, so
  explain it and obtain explicit confirmation before saving a definition that
  enables it.
- Do not claim this protects a value from a later HTTP, agent, webhook, or
  integration node. Such a node can intentionally disclose normal workflow
  output.
- Keep the projection and `limit` narrow. More than 1,000 protected non-null
  cells, KMS unavailability, or one invalid ciphertext fails the entire query
  node with `Failed to decrypt`; no partial result is available.
- Protected columns remain unavailable for filters, sorting, grouping,
  aggregation, and Top-N even when decryption is enabled. The system creates a
  metadata-only audit event and does not put the plaintext in application logs.

Never use this as an excuse to invent a Studio table-reveal endpoint or to
place plaintext inside published application code. The Studio table API,
public table APIs, and ordinary table reads remain ciphertext-only.

## Python code nodes

The live integration catalog controls a node's `inputs` object. It does not
describe every persisted `WorkflowNode` field. In the public OpenAPI contract,
`script_code` is a top-level field on `WorkflowNode`, so an empty
`input_schema` for `core.python_code` does **not** mean that the Python node
cannot receive a script.

For a requested Python step, validate `core.python_code` through the live
catalog, validate `script_code` through `GET /openapi.json`, and save the code
as the node's top-level `script_code` field—not inside `inputs`. Do not invent
runtime variables, output paths, or interpolation syntax: derive those from a
documented public contract, an existing saved workflow, or user-provided
details.

## Report results

Report the HTTP outcome and these non-secret fields:

- `id`
- `scenario_group_id`
- `version`
- `is_latest`
- `status`
- `equipo_id`
- `sync_webhook_id` when returned
- `schedule.state`, with `reason` or `error_code` when present, after `POST /workflows/` or `PUT /workflows/{scenario_id}/status`

After a successful complete workflow create, also report:

- The Puente webhook endpoint derived from the configured API origin and
  `sync_webhook_id`, when both are valid.
- The production frontend editor URL derived from `scenario_group_id` when the
  configured origin is `https://api.puente.xyz`.

Label these links clearly so the user is not given a webhook endpoint when they
ask to open the workflow project in the frontend.

Preserve API error status and detail. Do not expose request headers or credentials.
