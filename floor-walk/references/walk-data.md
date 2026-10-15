# Walk data schema

The walk page (`templates/walk.html`) renders entirely from the JSON block with `id="walk-data"` plus the static mermaid block under `FLOOR PLAN`. Replace both; touch nothing else except the `<title>`.

```jsonc
{
  "kind": "blueprint" | "as-built",
  "batch": { "id": "B02", "name": "Checkout reliability" },
  "headline": "One sentence: what this batch does for the system, in plain words",
  "repo": "owner/name",                 // optional
  "branch": "batch/b02-checkout-reliability",  // as-built; for blueprint, the branch that will be created
  "base": "main",
  "generated_at": "YYYY-MM-DD",
  "blueprint_url": "https://claude.ai/...",   // as-built only: link back to the blueprint walk, else ""
  "features": [
    { "id": "F004", "name": "Idempotent payment retries",
      "status": "planned" | "built" | "deviated" | "dropped",
      "note": "optional one line, e.g. why it was dropped" }
  ],
  "floorplan_caption": "One or two sentences: what the reader should see in the floor plan",
  "stops": [
    {
      "id": "s1",                       // [A-Za-z0-9_-] only; stable across re-publishes
      "title": "Payments service",      // the component, as a person would name it
      "component": "services/payments", // path or module
      "change": "new" | "modified" | "removed" | "unchanged",
      "features": ["F004"],
      "what": "1-2 sentences. Blueprint: what will change. As-built: what changed.",
      "why": "1-2 sentences tying it to the spec or the reason it was needed.",
      "ripple": ["Knock-on effect on another component or caller"],
      "decisions": [
        { "choice": "What was chosen", "alternatives": "What it was chosen over", "why": "One line" }
      ],
      "proof": [
        { "type": "test", "text": "Test name rewritten as a plain-English sentence",
          "status": "pass" | "fail" | "planned" },
        { "type": "behaviour", "text": "What was run", "before": "...", "after": "...",
          "status": "pass" | "fail" | "planned" }
      ],
      "flags": [
        { "id": "s1-blast",             // [A-Za-z0-9_-] only, unique in the walk; it is the db doc id
          "level": "red" | "yellow",
          "category": "deviation" | "security" | "blast-radius" | "unresolved" | "debt",
          "title": "One line, stated as the fact, not a question",
          "detail": "2-3 sentences: what, why it matters, what limits it" }
      ],
      "diff": "unified diff text for this stop's files (as-built only; \"\" for blueprint)"
    }
  ]
}
```

## Rules

- **Level follows category.** `deviation`, `security`, `blast-radius` and `unresolved` are always `red`. `debt` is always `yellow`. Never downgrade a red to keep the count low.
- **Flag ids are stable.** On a re-publish, a flag whose substance didn't change keeps its id, so the reviewer's mark on it survives. A flag whose substance changed gets a new id (e.g. `s2-deviation-2`), so it must be marked again. Delete acks for removed flags.
- **Stop ids are stable too** (comment threads anchor to stops).
- **`diff`** is `git diff <base>...HEAD -- <paths for this stop>`. If a stop's diff exceeds ~400 lines, keep the most important hunks and end with a line `# … N more lines in <paths>`.
- **Strings are plain text.** The page sets them via `textContent`; markdown and HTML are not rendered.
- **No secrets** in any field, including diffs (redact keys/tokens to `***`).
- **Example data:** leave `"example"` out (or `false`) on real walks.

## Floor plan (mermaid)

Start from the mermaid diagram in `ARCHITECTURE.md`. Keep the touched components plus their direct neighbours; drop the rest. Then:

```
flowchart LR
  api[Orders API] -->|charge| pay["1 · Payments service"]
  pay -.->|"new: payment.settled"| bus["2 · Event bus"]
  classDef changed stroke:#0F7B74,stroke-width:3px;
  classDef added stroke:#0F7B74,stroke-width:3px,stroke-dasharray:6 4;
  classDef removed stroke:#B93228,stroke-width:3px,stroke-dasharray:2 3;
  class pay changed;
  class bus added;
```

- Prefix each stop's node label with its stop number: `"1 · Payments service"`.
- New connections are dotted (`-.->`) with a label starting `new:`; removed ones get a label starting `removed:`.
- Label every edge whose meaning isn't obvious (`writes`, `publishes`, `POST`).
- Aim for 5-12 nodes. If there's no `ARCHITECTURE.md`, draw the neighbourhood from the code.

## Database (written by the page, read by Claude)

| Path | Written when | Shape |
|---|---|---|
| `acks/<flag id>` | Reviewer marks a red flag | `{verdict: "ok" \| "change", note, by, at}` |
| `review/state` | Reviewer finishes | `{verdict: "approved" \| "changes_requested", changes: [flag ids], note, by, at}` |

Read with `ArtifactData` (`list` on `acks`, `get` on `review/state`). Before re-publishing a walk for another round, `delete` `review/state` (and the acks of flags that changed id) so the page opens for review again.
