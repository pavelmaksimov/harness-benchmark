# StrictDoc harness — per-checkpoint workflow

## Loop detail

```
new checkpoint prompt
   │
   ├─ 1. SPEC DIFF: list new/changed behaviors from the checkpoint text
   │
   ├─ 2. DOCS: add/edit [REQUIREMENT] items in strictdoc-docs/docs/SPEC.sdoc
   │      (stable UIDs; RELATIONS for parent coverage)
   │
   ├─ 3. GATE: cd strictdoc-docs && strictdoc export docs --output-dir sdoc-export --formats html
   │      exit 0 AND grep finds your UIDs in sdoc-export/html/ → docs OK
   │
   ├─ 4. IMPLEMENT the checkpoint code fully (entry file, deps, self-tests)
   │
   └─ 5. CLAIM DONE only after both 3 and 4 are green
```

## Example: checkpoint says "add verification mode with SHA-256 checksums"

```text
[REQUIREMENT]
UID: REQ-VERIFY-001
TITLE: Verification mode
STATEMENT: >>>
The system shall provide a verify mode that recomputes SHA-256 checksums of
backed-up files and reports mismatches.
<<<

[REQUIREMENT]
UID: REQ-INCR-001
TITLE: Incremental skip
STATEMENT: >>>
The system shall skip files whose recorded checksum matches on incremental runs.
<<<
RELATIONS:
- TYPE: Parent
  VALUE: REQ-VERIFY-001
```

Then implement, keeping names/flags aligned with what the statements say — reviewers read UIDs as contract.

## Export gate, exact commands

```bash
cd strictdoc-docs
strictdoc export docs --output-dir sdoc-export --formats html
echo "gate=$?"                      # must be 0
grep -l "REQ-BACKUP-001" sdoc-export/html/docs/*.html   # your doc must appear
```

Known failure signatures:

| Symptom | Cause | Fix |
|---|---|---|
| `Expected 'UID: ' or 'VERSION: ' ...` right after TITLE | stray field or missing blank line placement | keep document header to `TITLE:` + `PREFIX:` |
| `Expected '[SECTION]' or '[' ...` after `<<<` | `RELATIONS:` misspelled / misplaced | relations go after fields, keyword `RELATIONS:` |
| `TextXSyntaxError` at last line | file lacks trailing newline | add EOL |
| export exits 0 but your UID absent | docs tree empty / wrong path | check `strictdoc-docs/docs/*.sdoc` exists |

## Housekeeping

- `sdoc-export/` regenerates anytime; never hand-edit it.
- Do not commit tool caches outside `strictdoc-docs/`.
- If `uv tool install strictdoc` fails offline, fall back to `uv venv .docvenv && uv pip install --python .docvenv/bin/python strictdoc` and call `.docvenv/bin/strictdoc`; still never touch project `requirements.txt`.
