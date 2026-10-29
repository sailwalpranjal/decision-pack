# Let the web page take a spec that points at a tree file

**Labels:** type:feature, priority:P2, area:web

## Problem

The API refuses `tree_file` (it must not read server files), so the case specs cannot be uploaded as they are; the tree has to be pasted inline. That is a rough edge for exactly the first thing a new user tries.

## Acceptance criteria

- [ ] The web page accepts an optional second YAML file for the tree and sends it as an extra form part.
- [ ] The API merges an uploaded tree into the spec before validation, and still refuses `tree_file`.
- [ ] `cases/funnel-lab/spec.yaml` and `tree.yaml` run through the page unchanged.
- [ ] A test covers the new form part.
