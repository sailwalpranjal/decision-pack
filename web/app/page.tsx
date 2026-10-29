"use client";

import { useState } from "react";
import { fileUrl, getResult, getStatus, startRun, type Result } from "../lib/api";

const money = (x: number | null, unit: string) =>
  x === null ? "n/a" : unit === "$" ? `$${x.toFixed(2)}` : `${x.toFixed(2)}${unit ? " " + unit : ""}`;
const pct = (x: number | null) => (x === null ? "n/a" : `${(x * 100).toFixed(1)}%`);
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function Home() {
  const [spec, setSpec] = useState<File | null>(null);
  const [data, setData] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!spec || !data) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const run = await startRun(spec, data);
      setRunId(run.id);
      for (;;) {
        const status = await getStatus(run.id);
        if (status.status === "failed") throw new Error(status.error ?? "the run failed");
        if (status.status === "done") break;
        await sleep(400);
      }
      setResult(await getResult(run.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <h1>decision-pack</h1>
      <p className="muted">
        Upload a spec (YAML, with the hypothesis tree inline) and a CSV. You get the driver bridge, the
        hypothesis tree and sized recommendations. It describes observational data; it does not show causes.
      </p>

      <form onSubmit={submit}>
        <label>
          Spec (.yaml)
          <input type="file" accept=".yaml,.yml" onChange={(e) => setSpec(e.target.files?.[0] ?? null)} />
        </label>
        <label>
          Data (.csv)
          <input type="file" accept=".csv" onChange={(e) => setData(e.target.files?.[0] ?? null)} />
        </label>
        <button type="submit" disabled={!spec || !data || busy}>
          {busy ? "Running..." : "Run analysis"}
        </button>
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
      </form>

      {result && runId && (
        <section aria-live="polite">
          <h2>{result.title}</h2>
          <p>
            {result.metric.label}: {money(result.metric.baseline, result.metric.unit)} for {result.groups.baseline},{" "}
            {money(result.metric.comparison, result.metric.unit)} for {result.groups.comparison}. Gap{" "}
            {money(result.metric.gap, result.metric.unit)}
            {result.metric.ratio !== null && ` (${result.metric.ratio.toFixed(2)}x)`}, 95% interval{" "}
            {money(result.metric.gap_ci[0], result.metric.unit)} to {money(result.metric.gap_ci[1], result.metric.unit)}.
          </p>
          {result.warnings.map((w) => (
            <p key={w} className="warn">
              {w}
            </p>
          ))}

          <h2>Waterfall</h2>
          <img src={fileUrl(runId, "waterfall.svg")} alt="Waterfall of the gap split by factor" />
          <table>
            <thead>
              <tr>
                <th>Factor</th>
                <th className="num">Shapley</th>
                <th className="num">Share</th>
                <th className="num">Sequential</th>
              </tr>
            </thead>
            <tbody>
              {result.bridge.factors.map((f) => (
                <tr key={f}>
                  <td>{f.replaceAll("_", " ")}</td>
                  <td className="num">{money(result.bridge.shapley[f], result.metric.unit)}</td>
                  <td className="num">{pct(result.bridge.shapley_shares[f])}</td>
                  <td className="num">{money(result.bridge.sequential[f], result.metric.unit)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {result.tree && (
            <>
              <h2>Hypothesis tree</h2>
              <img src={fileUrl(runId, "tree.svg")} alt="Hypothesis tree coloured by status" />
              {result.tree.mece_problems.map((p) => (
                <p key={p.node_id} className="error">
                  {p.node_id}: {p.message}
                </p>
              ))}
              <table>
                <tbody>
                  {result.tree.results.map((n) => (
                    <tr key={n.node_id}>
                      <td>
                        <span className={`pill ${n.status}`}>{n.status}</span>
                      </td>
                      <td>{n.statement}</td>
                      <td className="muted">{n.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {result.recommendations.length > 0 && (
            <>
              <h2>Recommendations</h2>
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Recommendation</th>
                    <th className="num">Base</th>
                    <th className="num">Low to high</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {result.recommendations.map((r) => (
                    <tr key={r.id}>
                      <td>{r.rank}</td>
                      <td>
                        {r.title}
                        <div className="muted">{r.rationale}</div>
                      </td>
                      <td className="num">{Math.round(r.base).toLocaleString()}</td>
                      <td className="num">
                        {Math.round(r.low).toLocaleString()} to {Math.round(r.high).toLocaleString()}
                      </td>
                      <td>{r.arithmetic}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          <p className="links">
            <a href={fileUrl(runId, "memo")}>Memo (Markdown)</a>
            <a href={fileUrl(runId, "deck.pptx")}>Deck (PPTX)</a>
          </p>
        </section>
      )}
    </main>
  );
}
