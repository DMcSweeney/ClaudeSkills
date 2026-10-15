# Review policy

<!-- Copy to the repo root as REVIEW-POLICY.md and fill in. The risk-review skill reads it on
     every review. Where a section is missing or left as the example, the strict default applies.
     Keep it short: rules here are applied literally. -->

## Data this software handles

<!-- What sensitive data flows through the code, and its class. Examples:
     - Patient health records (special-category data under UK/EU GDPR)
     - Staff names and email addresses (personal data)
     - API credentials for <service> -->

**Strict default:** treat every record the software processes as sensitive personal data.

## Sensitive fields

<!-- Field/column/variable names that carry sensitive data, so the reviewer can trace them.
     e.g. `patient_id`, `nhs_number`, `dob`, `postcode`, `email`, `free_text_notes` -->

**Strict default:** anything named like an identifier, contact detail, date of birth, address,
health/clinical term, free-text note, image, or credential.

## Where sensitive data must never go

**Strict default:**
- logs (any level), metrics, traces, error messages, exception text, `repr`/`__str__`
- third-party services, analytics, crash reporters, LLM/AI APIs
- URLs or query strings
- temp files, caches or exports outside an approved location, or without cleanup
- test fixtures, docs or examples (synthetic data only)
- version control

<!-- Add project-specific destinations, and any approved exceptions with the reason. -->

## Paths the reviewer must never read

<!-- One glob per line, in this fenced block. A trailing slash means a whole directory.
     These are added to the built-in defaults (.env*, keys, data/, *.csv, *.parquet, *.db, ...). -->

```never-read
```

## Libraries

<!-- Approved for sensitive work, and banned (with reasons). e.g.
     Banned: pickle for anything crossing a trust boundary (arbitrary code execution) -->

## Required gates

**Strict default:** secrets scan, Python static analysis (when Python changes), and dependency
audit (when a pinned manifest exists) must run. A required gate that couldn't run is a red flag.

## SQL dialect

<!-- e.g. postgres, sqlite, bigquery. Default: ansi -->

## Retention and deletion

<!-- How long data may be kept, and where deletion must happen. -->

## Extra rules

<!-- Anything else the reviewer should enforce literally. -->
