# Walk data schema

The walk page (`templates/walk.html`) renders entirely from the JSON block with `id="walk-data"` plus two static mermaid blocks: `SYSTEM MAP` and `DETAIL MAP`. Replace all three; touch nothing else except the `<title>`.

```jsonc
{
  "kind": "blueprint" | "as-built",
  "batch": { "id": "B02", "name": "Checkout reliability" },
  "headline": "One sentence: what this batch does for the system, in plain words",
  "purpose": "1-2 sentences for a manager: the problem it solves and who or what benefits. No file names, IDs or jargon.",
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
  "domains": [                          // every node on the system map, in its order
    { "id": "payments",                 // the domain id from ARCHITECTURE.md (node id on the system map, subgraph id on the detail map)
      "name": "Payments",
      "colour": "blue" | "green" | "amber" | "rose" | "slate" | "sand",  // from ARCHITECTURE.md; never invent
      "change": "modified" | "new" | "removed" | "untouched" }
  ],
  "floorplan_caption": "One or two sentences: what the reader should see on the maps",
  "stops": [
    {
      "id": "s1",                       // [A-Za-z0-9_-] only; stable across re-publishes
      "title": "Payments service",      // the component, as a person would name it
      "component": "services/payments", // path or module
      "domain": "payments",             // a domains[].id; "" for Housekeeping
      "node": "pay",                    // this stop's node id on the detail map; "" if none
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
      "caught": [                      // as-built only: risk-inspector findings fixed during the loop
        { "title": "One line", "severity": "critical" | "high" | "medium" | "low",
          "pass": "data" | "security" | "correctness" | "design" | "efficiency" | "readability" }
      ],
      "diff": "unified diff text for this stop's files (as-built only; \"\" for blueprint)"
    }
  ]
}
```

## Rules

- **Risk-inspector findings** map to flags and `caught` entries by the table in the `risk-inspector` skill. Keep `caught` titles free of sensitive values, like everything else.
- **Level follows category.** `deviation`, `security`, `blast-radius` and `unresolved` are always `red`. `debt` is always `yellow`. Never downgrade a red to keep the count low.
- **Inefficiencies are `debt`.** Wasted work, duplicated logic, extra queries or calls, cost or performance you'd notice at scale: raise each one as a yellow `debt` flag whose title names the inefficiency ("Each webhook opens its own HTTP connection"). Don't drop them because they seem minor.
- **Plain language first.** `headline`, `purpose`, stop titles, feature names and flag titles are written for a manager who knows the system but not the code. IDs, paths and branch names go only in their own fields; the page shows them small and grey.
- **Flag ids are stable.** On a re-publish, a flag whose substance didn't change keeps its id, so the reviewer's mark on it survives. A flag whose substance changed gets a new id (e.g. `s2-deviation-2`), so it must be marked again. Delete acks for removed flags.
- **Stop ids are stable too** (comment threads anchor to stops).
- **`diff`** is `git diff <base>...HEAD -- <paths for this stop>`. If a stop's diff exceeds ~400 lines, keep the most important hunks and end with a line `# … N more lines in <paths>`.
- **Strings are plain text.** The page sets them via `textContent`; markdown and HTML are not rendered.
- **No secrets** in any field, including diffs (redact keys/tokens to `***`).
- **Example data:** leave `"example"` out (or `false`) on real walks.

## Maps (mermaid)

The page has two maps. Their look comes from the page (colours follow light/dark mode), driven by `domains`, the node ids and four class names, so don't add `style` lines or extra `classDef` colours.

Start each map's mermaid block with this line, which sets the larger text size the page is designed for (on the system map it is the only line added above the verbatim copy):

```
%%{init: {"themeVariables": {"fontSize": "17px"}, "flowchart": {"padding": 12}}}%%
```

### System map: the same picture on every walk

Copy the **Domain map** from `ARCHITECTURE.md` **verbatim**: same nodes, order, labels and edges. Consistency between walks is the point. The page colours each domain node from `domains[].colour` and outlines it by `domains[].change`. The only edits allowed:

- A **new domain** this batch adds: append its node and edges at the end. In `domains`, give it the next unused colour from the palette (see the `architecture-map` skill) and `change: "new"`. It shows with a purple dashed outline.
- A **removed domain**: keep its node, with `change: "removed"`.
- New dependencies between domains: append them as dotted edges labelled `new: …`.

If `ARCHITECTURE.md` has no Domain map yet (it predates it), run `architecture-map` to upgrade it first. If there's no `ARCHITECTURE.md` at all, draw the domain map from the code and say so in `floorplan_caption`.

### Detail map: where in those domains things changed

Built from the **Structure overview** in `ARCHITECTURE.md`:

- Keep a `subgraph` for each touched domain, with the domain id as the subgraph id and the domain name as its label: `subgraph payments[Payments]`. The page tints each subgraph in its domain's colour.
- Inside it, keep the touched components plus enough neighbours to show where things connect. Direct neighbours in other domains come with their own subgraph. Reuse the canonical node ids. Aim for 5-15 nodes.
- Prefix each stop's node label with its stop number, `"1 · Payments service"`, and set that stop's `node` to the node id.
- Mark change type with these class names only: `modified` (teal), `added` (purple, dashed), `removed` (red, dotted), using the `classDef` lines in the example below exactly (they're the fallback colours if the page's own styling can't reach the diagram). Untouched nodes get no class and show grey with a dark border.
- New connections are dotted (`-.->`) with a label starting `new:`; removed ones get a label starting `removed:`. Label every edge whose meaning isn't obvious (`writes`, `publishes`, `POST`).
- Node ids are snake_case with no hyphens (the page finds nodes by id).

```
%%{init: {"themeVariables": {"fontSize": "17px"}, "flowchart": {"padding": 12}}}%%
flowchart LR
  subgraph orders[Orders]
    api[Orders API]
  end
  subgraph payments[Payments]
    pay["1 · Payments service"]
  end
  subgraph platform[Platform]
    bus["2 · payment.settled event"]
  end
  api -->|charge| pay
  pay -.->|"new: publishes"| bus
  classDef modified fill:#D3ECE8,stroke:#0F7B74,stroke-width:3px;
  classDef added fill:#E9E1F8,stroke:#6B45B8,stroke-width:3px,stroke-dasharray:6 4;
  classDef removed fill:#F8E3E0,stroke:#B93228,stroke-width:2px,stroke-dasharray:2 3;
  class pay modified;
  class bus added;
```

Both maps are clickable on the page: a numbered node jumps to its stop, and a domain jumps to its first stop.

## Database (written by the page, read by Claude)

| Path | Written when | Shape |
|---|---|---|
| `acks/<flag id>` | Reviewer marks a red flag | `{verdict: "ok" \| "change", note, by, at}` |
| `review/state` | Reviewer finishes | `{verdict: "approved" \| "changes_requested", changes: [flag ids], note, by, at}` |

Read with `ArtifactData` (`list` on `acks`, `get` on `review/state`). Before re-publishing a walk for another round, `delete` `review/state` (and the acks of flags that changed id) so the page opens for review again.
