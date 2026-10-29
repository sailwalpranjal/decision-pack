# Test the web page in a browser

**Labels:** type:chore, priority:P1, area:web

## Problem

The web page is type-checked and built in CI, but nothing loads it. A regression in the upload, the polling loop or the rendering would go unnoticed.

## Acceptance criteria

- [ ] A Playwright test starts the API and the Next.js server, uploads a spec with an inline tree and the funnel CSV, waits for the run, and asserts the page shows the gap (`$48.02`), the waterfall image and the three recommendations.
- [ ] A second test uploads a bad spec and asserts the readable error message is shown.
- [ ] The tests run in the `web` CI job.
