# Persist API jobs so results survive a restart

**Labels:** type:feature, priority:P1, area:api

## Problem

`api/app.py` keeps jobs in a dict and the pack files in a temporary folder. A restart loses every job, and the oldest are evicted after 100.

## Acceptance criteria

- [ ] Jobs are stored in SQLite (path from an environment variable); the pack folder is under a configured data directory.
- [ ] `GET /runs/{id}` works after the process restarts, with a test that stops and recreates the app.
- [ ] Eviction becomes an age-based cleanup (default 7 days) instead of a count.
- [ ] The README limits section stops saying jobs live in memory.
