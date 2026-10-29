export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type JobState = "queued" | "running" | "done" | "failed";

export interface RunStatus {
  id: string;
  status: JobState;
  error: string | null;
}

export interface Recommendation {
  rank: number;
  id: string;
  title: string;
  rationale: string;
  impact_unit: string;
  low: number;
  base: number;
  high: number;
  score: number;
  arithmetic: string;
}

export interface TreeNodeResult {
  node_id: string;
  statement: string;
  status: "supported" | "refuted" | "untested";
  detail: string;
}

export interface Result {
  title: string;
  observational: boolean;
  metric: {
    label: string;
    unit: string;
    baseline: number;
    comparison: number;
    gap: number;
    ratio: number | null;
    gap_ci: (number | null)[];
  };
  groups: { baseline: string; comparison: string };
  bridge: {
    factors: string[];
    shapley: Record<string, number>;
    shapley_shares: Record<string, number | null>;
    sequential: Record<string, number>;
  };
  tree: { results: TreeNodeResult[]; mece_problems: { node_id: string; message: string }[] } | null;
  recommendations: Recommendation[];
  warnings: string[];
}

async function failure(res: Response): Promise<Error> {
  try {
    const body = await res.json();
    return new Error(typeof body.detail === "string" ? body.detail : `request failed (${res.status})`);
  } catch {
    return new Error(`request failed (${res.status})`);
  }
}

export async function startRun(spec: File, data: File): Promise<RunStatus> {
  const form = new FormData();
  form.append("spec", spec);
  form.append("data", data);
  const res = await fetch(`${API_URL}/runs`, { method: "POST", body: form });
  if (!res.ok) throw await failure(res);
  return res.json();
}

export async function getStatus(id: string): Promise<RunStatus> {
  const res = await fetch(`${API_URL}/runs/${id}`);
  if (!res.ok) throw await failure(res);
  return res.json();
}

export async function getResult(id: string): Promise<Result> {
  const res = await fetch(`${API_URL}/runs/${id}/result`);
  if (!res.ok) throw await failure(res);
  return res.json();
}

export const fileUrl = (id: string, name: string) => `${API_URL}/runs/${id}/${name}`;
