# Field functions

## Contents

- Functions
- Write a formula
- Where formulas work
- Dates and time zones
- Null results and volatile values
- Test a formula
- Fix validation errors
- Runtime errors

Node inputs accept four functions inside the same `{{ }}` used for references.
Puente evaluates them in the backend; there are no other functions, no
operators, and no Python. Examples use the instant `2026-10-06T14:03:27-03:00`.

```text
{{ now() }}                                             -> 2026-10-06T14:03:27-03:00
{{ format_date(now(); 'DD/MM/YYYY HH:mm') }}            -> 06/10/2026 14:03
{{ format_date(today(); 'dddd D [de] MMMM') }}          -> martes 6 de octubre
{{ format_date(gmail_1.headers.date; 'DD/MM/YYYY') }}   -> 06/10/2026
{{ format_date(sheet_1['Fecha de pedido']; 'DD/MM') }}  -> 06/10
Pedido {{ uuid() }} creado el {{ format_date(now(); 'DD/MM/YYYY') }}
```

## Functions

| Function | Returns | Examples |
|---|---|---|
| `now([zona])` | Current instant as ISO 8601 with offset, no microseconds | `now()` -> `2026-10-06T14:03:27-03:00`; `now('UTC')` -> `2026-10-06T17:03:27+00:00` |
| `today([zona])` | Midnight of the current day in the zone, ISO 8601 | `today()` -> `2026-10-06T00:00:00-03:00`; `today('Asia/Tokyo')` -> `2026-10-07T00:00:00+09:00` |
| `format_date(fecha; formato; [zona]; [idioma])` | Text | `format_date(now(); 'HH:mm'; 'UTC')` -> `17:03`; `format_date(now(); 'dddd, MMMM D'; null; 'en')` -> `Tuesday, October 6` |
| `uuid()` | 36-character lowercase UUID v4 text | `uuid()` -> `2f1e6a4b-8c3d-4e5f-9a7b-1c2d3e4f5a6b` |

- `zona` is an exact, case-sensitive IANA name: `UTC` and `America/Bogota` are valid; `utc` is not.
- `idioma` is `'es'` (default) or `'en'`. Spanish names are lowercase: `martes`, `oct`.
- A `null` or `''` `zona` or `idioma` uses the default, so `now('')` equals `now()`.
- All `now()` and `today()` calls in one node share the same instant.

### `formato` tokens

Moment-style tokens. Text inside `[...]` is copied literally, and any
character that is not an ASCII letter (space, `/`, `-`, `:`, `,`, `.`) is
copied too. Every run of one repeated letter must be exactly one token; `dd`,
`yyyy`, `YYY`, an unclosed `[`, an empty format, or loose words such as `hrs`
fail with `invalid_format`.

| Token | Meaning | `es` / `en` |
|---|---|---|
| `YYYY`, `YY` | Year | `2026`, `26` |
| `MMMM`, `MMM` | Month name, abbreviated | `octubre`/`October`, `oct`/`Oct` |
| `MM`, `M` | Month number | `10`, `10` |
| `DD`, `D` | Day of month | `06`, `6` |
| `dddd`, `ddd` | Weekday name, abbreviated | `martes`/`Tuesday`, `mar`/`Tue` |
| `d` | ISO weekday, 1 = Monday ... 7 = Sunday (Moment uses Sunday = 0) | `2` |
| `HH`, `H` | Hour 00-23, 0-23 | `14`, `14` |
| `hh`, `h` | Hour 01-12, 1-12 | `02`, `2` |
| `mm`, `m` | Minutes | `03`, `3` |
| `ss`, `s` | Seconds | `27`, `27` |
| `SSS` | Milliseconds | `000` |
| `A`, `a` | AM/PM, am/pm | `PM`, `pm` |
| `Z`, `ZZ` | Offset with and without colon | `-03:00`, `-0300` |
| `X`, `x` | Epoch seconds, milliseconds | `1791306207`, `1791306207000` |

`'DD/MM [hrs]'` -> `06/10 hrs`; `'YYYY-MM-DD[T]HH:mm:ssZ'` -> `2026-10-06T14:03:27-03:00`.
`mm` is minutes: `'DD/mm/YYYY'` gives `06/03/2026` plus a `format_minutes_hint` warning.

## Write a formula

| Rule | Correct | Wrong |
|---|---|---|
| Separate arguments with `;` | `format_date(now(); 'DD/MM')` | `format_date(now(), 'DD/MM')` |
| Quote text, preferably with single quotes | `format_date(now(); 'DD/MM/YYYY')` | `format_date(now(); DD/MM/YYYY)` |
| Write paths without braces inside a function | `format_date(pedido_1.fecha; 'DD')` | `format_date({{pedido_1.fecha}}; 'DD')` |
| Use `['Key']` for keys with spaces or symbols | `format_date(sheet_1['Fecha de pedido']; 'DD/MM')` | `format_date(sheet_1.Fecha de pedido; 'DD/MM')` |
| Use lowercase function names | `now()` | `Now()` |
| Always add parentheses | `{{ now() }}` | `{{ now }}` (read as a path) |

- A `{{ }}` is a formula only when it starts with a catalog function name and
  `(`. Anything else is an ordinary reference, so `{{sheet_1.Fecha de pedido}}`
  still works outside a function.
- Paths inside a formula use `.key`, `[0]`, and `['key']` (double quotes are
  also accepted). They resolve against the same context as references: node
  context keys, `SET_VARIABLES` variables, `_request`, `_trigger`, keys of the
  initial payload, and inside an iterator body `<iterator_key>.value`,
  `.index`, and `.key`.
- Arguments can also be numbers, `true`, `false`, `null`, or another call.
- Text and formulas can be mixed in one field, with several `{{ }}`.
- There are no operators (`+ - * /`, comparisons, `and`/`or`); compare in
  `IF_ELSE` or `SWITCH`. There is no escape for a literal `{{`.
- Limits: 2,000 characters per formula and 10 nested calls.

## Where formulas work

- Every string inside a node's `inputs`, including nested objects and lists,
  `IF_ELSE`/`SWITCH` condition values (`conditions[0].left`), HTTP headers, and
  JSON body text. In a JSON body keep the JSON valid: use single quotes inside
  the formula, for example
  `{"fecha": "{{ format_date(now(); 'DD/MM/YYYY') }}", "id": "{{ uuid() }}"}`.
- Not evaluated: the top-level `code` input (it still interpolates plain
  references), the top-level `script_code` (use Python `datetime` and `uuid`
  there), the `html` input of `pdf.create_from_html`, and trigger node inputs.
- `now`, `today`, and `uuid` are rejected in the inputs of an `ITERATOR` node
  (`volatile_function_in_iterator`). Nodes inside the iterator body may use
  them. To iterate over a computed date, compute it in an earlier node and
  reference that result.

## Dates and time zones

`fecha` accepts, in this order:

- the result of `now()` or `today()`;
- ISO text: `2026-10-06`, `2026-10-06T14:03:00`, `2026-10-06 14:03:00`, with or without an offset or `Z`;
- RFC 2822 text, such as Gmail's `headers.date` (`Tue, 6 Oct 2026 14:03:00 -0300`); without a zone it is read as UTC;
- epoch seconds (10 digits) or milliseconds (13 digits), as a number or text.

Anything else fails with `invalid_date`, including `06/10/2026` (`DD/MM/YYYY`
text is not read; supply `YYYY-MM-DD`), booleans, and other numbers such as a
row number. `null` returns `null`.

- The default zone is always `America/Santiago`. Only the `zona` argument
  changes it; a schedule trigger's timezone does not.
- A date without an offset is read in `zona`, or in `America/Santiago` when
  `zona` is absent: `format_date('2026-10-06T09:00'; 'HH:mm'; 'Asia/Tokyo')`
  -> `09:00`.
- `format_date` converts the date to `zona` before formatting and never keeps
  the input's zone: `format_date(today('Asia/Tokyo'); 'D')` -> `6` (Tokyo
  midnight seen from Santiago), while `format_date(now(); 'D'; 'Asia/Tokyo')`
  -> `7`.

## Null results and volatile values

| Situation | Field value |
|---|---|
| Formula fills the whole field (ignoring outer spaces) | The result as text; `null` stays `null` |
| Formula inside other text, result not null | Inserted as text |
| Formula inside other text, result `null` | `""` in that place, plus an `expression_null` warning on the step |

Inside a formula, a path to a missing field, a missing root, or a skipped node
is `null`. `{{ format_date(pedido_1.no_existe; 'DD') }}` gives `null`;
`Fecha: {{ format_date(pedido_1.no_existe; 'DD') }}` gives `"Fecha: "`.

`now`, `today`, and `uuid` change on every run. `uuid()` returns a new value
on every call and every node retry, so never use it as an idempotency key,
deduplication key, or secret.

## Test a formula

Both endpoints accept the Studio key (`X-API-Key`, permission
`resource:workflow:read`). They read only: they do not save, run, or schedule a
workflow, so they are not execution endpoints.

```http
GET /workflows/functions
```

Returns `{registry_version, default_timezone, functions: [...]}` with each
function's `name`, `syntax`, `arguments`, `examples`, and `volatile`. Prefer it
over this file if they differ.

```http
POST /workflows/expressions/evaluate
Content-Type: application/json

{"value": "Hoy es {{ format_date(now(); 'DD/MM') }} para {{ pedido_1.cliente }}",
 "variables": {"pedido_1": {"cliente": "Ana"}}}
```

```json
{"status": "ok", "result": "Hoy es 06/10 para Ana", "missing_references": [],
 "errors": [], "timezone_used": "America/Santiago", "volatile": true, "warnings": []}
```

| `status` | Meaning | Next step |
|---|---|---|
| `ok` | Evaluated; `result` follows the null rules above | Use the formula |
| `pending` | A root in `value` is absent from `variables`; nothing was evaluated | Add sample data for each root in `missing_references`, or accept it if only runtime data is missing |
| `error` | Syntax, validation, or evaluation error | Fix it using `errors[].code` and `hint` |

Send only the roots that `value` uses, with realistic sample values. Bodies
over 262,144 bytes return `413`. Preview formulas with dates from data
before saving, because `invalid_date` is detected only at runtime or in the
preview.

## Fix validation errors

Puente validates every formula on `POST /workflows/` and when activating with
`PUT /workflows/{scenario_id}/status`:

- `POST` with `status: "draft"`: errors are downgraded and returned in the
  response's `validation_warnings`. The draft is saved; fix them before
  proposing activation.
- `POST` with `active` or `inactive`, and activation through `PUT`: errors
  return `422` and nothing changes.

```json
{"detail": {"errors": [{"code": "syntax_error", "message": "No se esperaba ',' en la fórmula.",
  "node": "si_4", "edge": null, "field": "conditions[0].left", "start": 20, "end": 21,
  "hint": "Separa los argumentos con ;"}], "warnings": []}}
```

`node` is the context key, `field` the input path (`body`, `headers[0].value`),
and `start`/`end` the UTF-16 span inside that field. Fix every listed item in
the complete definition, preview it, and save once more. Graph and schedule
items share the list but have no `field`.

| Code | Severity | Fix |
|---|---|---|
| `syntax_error` | Error | Follow `hint`: `,` -> `;`; quote text such as `'DD/MM/YYYY'`; remove operators; close quotes and parentheses |
| `function_name_case` | Error | Use the lowercase name: `now()` |
| `nested_reference` | Error | Remove `{{ }}` around paths inside the function |
| `invalid_argument_count` | Error | Match the signature in `hint`; `format_date` takes 2 to 4 arguments |
| `expression_too_long` | Error | Keep each formula under 2,000 characters; split it across fields or nodes |
| `expression_too_deep` | Error | Use at most 10 nested calls |
| `invalid_timezone` | Error | Use an exact IANA name such as `America/Santiago` or `UTC` |
| `invalid_language` | Error | Use `'es'` or `'en'` |
| `invalid_format` | Error | Use tokens from the table; `DD` not `dd`, `YYYY` not `yyyy`, literal words in `[ ]`, close `[` |
| `volatile_function_in_iterator` | Error | Move `now`/`today`/`uuid` to an earlier node or into the iterator body |
| `unknown_function` | Warning | A misspelled function was read as a path; use the name in `hint` |
| `missing_parentheses` | Warning | Write `now()` instead of `now` |
| `unknown_reference` | Warning | Fix a misspelled context key (`hint` suggests one). It is expected for webhook payload keys; then no change is needed |
| `format_minutes_hint` | Warning | `mm` is minutes; use `MM` for the month, or ignore when minutes are intended |

## Runtime errors

An invalid value found while running (for example `invalid_date`) fails the
node; `on_error` applies as for any failed node. The failed step's `error` is:

```json
{"name": "ExpressionError", "value": "No se pudo interpretar la fecha '06/10/2026'.",
 "code": "invalid_date", "hint": "El formato DD/MM/AAAA aún no se puede leer; usa AAAA-MM-DD",
 "node": "enviar_correo_3", "field": "body.texto", "function": "format_date",
 "argument_index": 0, "received": "06/10/2026"}
```

`argument_index` is zero-based and `received` is truncated to 80 characters.
Inside an iterator, `item_index` identifies the item. Fix the source data or
the formula and preview it with sample data; the error does not clear on a
retry with the same data. `expression_null` warnings appear in the step's
`expression_warnings`.
