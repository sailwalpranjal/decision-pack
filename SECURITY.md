# Security policy

## Supported versions

Only the latest commit on the default branch. There are no tagged releases yet.

## Reporting a vulnerability

Please email pranjalsailwal09@gmail.com with the subject line "decision-pack security". Include what you found, how to reproduce it, and the version or commit.

I will reply within a week to confirm I have seen it. This is a one-person project, so I cannot promise a fix timeline, but I will tell you where it stands. Please do not open a public issue until we have talked.

## Scope

The spec evaluator (`core/expr.py`) and the HTTP API, which accept formulas and uploads from users. Anything that lets a spec run arbitrary code or read files from the server is in scope and urgent.
