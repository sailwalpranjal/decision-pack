# Run the five interviews and fill in the findings

**Labels:** type:chore, priority:P0, area:docs

## Problem

Everything in the PRD rests on an assumption nobody has tested: that product managers and analysts who explain metric gaps want a decision pack and not just a chart. `docs/research/findings.md` contains only a TODO.

## Acceptance criteria

- [ ] Five people who explained a metric movement in the last three months are interviewed using `docs/research/interview-guide.md`.
- [ ] One row per interview is added to `docs/research/findings.md` within an hour of the conversation, from notes taken at the time. No invented quotes.
- [ ] The PRD's "Risks" and the roadmap's "After v0.4" section are updated to say what the interviews changed, or that they changed nothing.
- [ ] If nobody splits a gap between drivers, the roadmap leads with the segment scan instead of the bridge.
