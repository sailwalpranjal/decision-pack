# decision-pack web

A single page that talks to the API: upload a spec and a CSV, watch the job, read the waterfall, the tree and the recommendations.

```bash
# terminal 1, from the repo root
decisionpack serve                 # http://127.0.0.1:8000

# terminal 2
cd web
npm install
npm run dev                        # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` if the API is somewhere else. The spec must carry its hypothesis tree inline under `tree:`; the API refuses `tree_file` because the server does not read files you point it at. `cases/funnel-lab/spec.yaml` and `tree.yaml` show both forms.
