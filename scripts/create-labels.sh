#!/usr/bin/env bash
# Creates the labels described in docs/project-board.md.
# Run from the repo root after `gh auth login`. --force makes it safe to re-run.
set -euo pipefail

gh label create "type:bug" --color d73a4a --description "Something is broken" --force
gh label create "type:feature" --color 1d76db --description "New capability or change in behaviour" --force
gh label create "type:docs" --color 0075ca --description "Documentation only" --force
gh label create "type:chore" --color cfd3d7 --description "Tooling, CI, dependencies" --force
gh label create "priority:P0" --color b60205 --description "Do now" --force
gh label create "priority:P1" --color d93f0b --description "Do next" --force
gh label create "priority:P2" --color fbca04 --description "Do later" --force
gh label create "needs-triage" --color ededed --description "Not yet reviewed" --force
gh label create "needs-info" --color d876e3 --description "Waiting for more detail from the reporter" --force
gh label create "blocked" --color 000000 --description "Cannot move until something else lands" --force
gh label create "area:bridge" --color 5319e7 --description "Touches bridge" --force
gh label create "area:stats" --color 5319e7 --description "Touches stats" --force
gh label create "area:segments" --color 5319e7 --description "Touches segments" --force
gh label create "area:tree" --color 5319e7 --description "Touches tree" --force
gh label create "area:sizing" --color 5319e7 --description "Touches sizing" --force
gh label create "area:report" --color 5319e7 --description "Touches report" --force
gh label create "area:api" --color 5319e7 --description "Touches api" --force
gh label create "area:web" --color 5319e7 --description "Touches web" --force
gh label create "area:cases" --color 5319e7 --description "Touches cases" --force
gh label create "area:docs" --color 5319e7 --description "Touches docs" --force
