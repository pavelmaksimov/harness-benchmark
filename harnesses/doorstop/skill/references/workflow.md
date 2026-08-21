# Doorstop harness — command reference (verified on doorstop 3.2)

## Global flags that matter

| Flag | Meaning |
|---|---|
| `-j .` | project root — **always pass it explicitly**; the built-in default is `/tmp` |
| `-q` / `-v` | quiet / verbose |
| `-f` | force without server |
| `-T <program>` | editor override for `add --edit`-style flows (we never edit interactively) |

Environment: export `EDITOR=true` in every shell before any doorstop call.

## Commands

```bash
export EDITOR=true
cd doorstop-docs            # or use -j doorstop-docs from anywhere

# documents
doorstop -j . create REQ reqs           # first/parent document
doorstop -j . create TST tsts -p REQ    # child document REQUIRES parent
doorstop -j . delete TST                # remove a document dir

# items
doorstop -j . add REQ                   # creates reqs/REQ00N.yml; fill text: via file edit
doorstop -j . remove REQ2               # remove an item file

# traceability
doorstop -j . link TST1 REQ1            # child -> parent link
doorstop -j . unlink TST1 REQ1
doorstop -j . clear TST1 REQ1           # absolve suspect links

# validation & output
doorstop -j .                           # validate whole tree (exit 0 = structurally OK)
doorstop -j . publish all publish-md -m --index   # markdown export into doorstop-docs/publish-md/
```

## Item YAML contract

Filename IS the UID (`reqs/REQ001.yml`). Keep fields; write requirement text into `text: |`. Example linked pair:

```yaml
# reqs/REQ001.yml
active: true
derived: false
header: ''
level: 1.0
links: []
normative: true
ref: ''
reviewed: null
text: |
  The system shall read backup job definitions from a YAML config file.
```

```yaml
# tsts/TST001.yml after `link TST1 REQ1`
links:
- type: req
  uid: REQ001
text: |
  Verify by running the CLI against a sample config and asserting job execution.
```

## Validation gate, exact sequence

```bash
cd doorstop-docs && doorstop -j .
echo "gate=$?"                          # must be 0
grep -rL '^text: ' --include='REQ*.yml' . | grep -v tsts && echo "EMPTY TEXT ITEMS" || echo "ITEMS_OK"
ls reqs/*.yml >/dev/null 2>&1 && echo "TREE_OK" || echo "TREE_MISSING"
```

## Failure signatures (all hit in practice)

| Symptom | Cause | Fix |
|---|---|---|
| `ERROR: The document name is already in use (/tmp/doorstop/reqs)` | forgot `-j .`; default root `/tmp` reused stale docs | always `-j .`; clean `/tmp/doorstop` if polluted |
| `fatal: not a git repository` | no VCS at project root | `git init -q .` once at workspace root |
| `ERROR: no parent specified for TST` | second document created without `-p` | `create TST tsts -p REQ` |
| `WARNING: REQ: REQ001: no text` on validation | item left with empty text | fill `text:` before claiming done |
| hangs waiting for editor | `EDITOR` unset and an edit flow triggered | `export EDITOR=true` everywhere |

## Housekeeping

- `publish-md/` regenerates anytime; never hand-edit it.
- Item files are plain YAML — bulk edits with your normal file tools are fine and preferred over interactive commands.
