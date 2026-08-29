/** Typed client for the AMP Triage API.
 *
 *  Every number rendered anywhere in this app comes from here. The frontend does no
 *  science: no probability fusion, no determinants, no similarity math, no wheel
 *  geometry. If a value is not in one of these responses, it does not get displayed.
 */

const BASE = "/api";

let authToken: string | null = typeof window !== "undefined" ? localStorage.getItem("pharmamind_token") : null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (typeof window !== "undefined") {
    if (token) localStorage.setItem("pharmamind_token", token);
    else localStorage.removeItem("pharmamind_token");
  }
}

export function getAuthToken(): string | null {
  return authToken;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...headers,
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// --- shapes mirrored from src/api.py -----------------------------------------

export type Confidence = "high" | "moderate" | "low";

export interface SpeciesMetric {
  name: string;
  n_train: number;
  cv_roc_auc: number;
  cv_roc_auc_std: number;
  confidence: Confidence;
}

export interface ScoreResponse {
  sequence: string;
  species: string;
  p_active: number;
  p_toxic: number;
  q: number;
  cached: boolean;
}

export interface ShortlistItem {
  rank: number;
  sequence: string;
  q_i: number;
  /** q_i ** theta. Internal to the objective -- never render this. */
  q_i_scaled: number;
  p_active: number;
  p_toxic: number;
  marginal_log_gain: number;
  similarity_to_nearest_selected: number;
}

export interface ShortlistResponse {
  /** id of the saved run (phase 6). null if persistence was unavailable. */
  run_id: number | null;
  /** phase 8: candidates skipped because this lab already tested them */
  n_excluded: number;
  excluded_sequences: string[];
  logdet: number;
  theta: number;
  items: ShortlistItem[];
  baseline_top_n: string[];
}

// --- experiments and lab memory (phase 8) --------------------------------------

export type Outcome = "hit" | "miss" | "toxic" | "inconclusive";

export interface ExperimentOut {
  id: number;
  sequence: string;
  assay: string;
  outcome: Outcome;
  measured_value: number | null;
  unit: string | null;
  /** wet_lab | seeded_public — never blur these in the UI */
  source: string;
  project_id: number | null;
  scientist_id: number | null;
  notes: string | null;
  tested_at: string;
}

export interface RegistryEntry {
  sequence: string;
  times_selected: number;
  times_tested: number;
  best_outcome: Outcome | null;
  last_tested_at: string | null;
}

export interface LabMemorySummary {
  n_known: number;
  n_excluded: number;
  excluded: RegistryEntry[];
}

export const outcomeStyle: Record<Outcome, string> = {
  hit: "bg-secondary-container text-on-secondary-container",
  miss: "bg-surface-container-high text-on-surface-variant",
  toxic: "bg-error-container text-on-error-container",
  inconclusive: "bg-primary-fixed text-on-primary-fixed-variant",
};

// --- saved runs / history (phase 6) -------------------------------------------

export interface RunItemOut {
  rank: number;
  sequence: string;
  q_i: number;
  p_active: number;
  p_toxic: number;
  similarity_to_nearest: number;
  marginal_log_gain: number;
  is_diversity_pick: boolean;
}

export interface RunSummary {
  id: number;
  species: string;
  k: number;
  theta: number;
  logdet: number;
  pool_size: number;
  n_items: number;
  n_excluded: number;
  label: string | null;
  project_id: number | null;
  scientist_id: number | null;
  scientist_name: string | null;
  created_at: string;
}

export interface RunDetail extends RunSummary {
  items: RunItemOut[];
}

export interface ValidateResponse {
  greedy_recovered: number;
  topn_recovered: number;
  n_hidden: number;
  k: number;
  greedy_chemotypes?: number | null;
  topn_chemotypes?: number | null;
  total_clusters?: number | null;
}

export interface Properties {
  sequence: string;
  length: number;
  net_charge_pH7: number;
  isoelectric_point: number;
  hydrophobic_moment_uH: number;
  mean_hydrophobicity: number;
  hydrophobic_fraction: number;
  cationic_fraction: number;
  anionic_fraction: number;
  polar_fraction: number;
  composition: Record<string, number>;
}

export interface CompareResponse {
  sequences: string[];
  species: string;
  properties: Properties[];
  wheel_svgs: string[];
  cosine_similarity: number;
  embedding_distance: number;
  scores: Record<string, unknown>[];
}

export type StructureTier = "experimental" | "predicted" | "unavailable";

export interface Structure {
  tier: StructureTier;
  pdb_id: string | null;
  pdb_text: string | null;
  plddt: number[] | null;
  mean_plddt: number | null;
  source: string;
}

export interface EvidencePaper {
  pmid: string;
  title: string;
  journal?: string;
  abstract_excerpt?: string | null;
  url: string;
}

export interface EvidenceResponse {
  status: "success" | "empty" | "unavailable";
  match_level: "peptide" | "pathogen" | null;
  papers: EvidencePaper[];
  reason?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  label?: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// --- calls --------------------------------------------------------------------

export const api = {
  species: () => req<SpeciesMetric[]>("/species"),

  score: (sequence: string, species: string) =>
    req<ScoreResponse>("/score", {
      method: "POST",
      body: JSON.stringify({ sequence, species }),
    }),

  shortlist: (
    sequences: string[], species: string, k: number, theta: number,
    opts: { project_id?: number | null; exclude_tested?: boolean; penalise_tested?: boolean } = {},
  ) =>
    req<ShortlistResponse>("/shortlist", {
      method: "POST",
      body: JSON.stringify({ sequences, species, k, theta, ...opts }),
    }),

  validate: (species: string, k = 20) =>
    req<ValidateResponse>("/validate", {
      method: "POST",
      body: JSON.stringify({ species, k }),
    }),

  properties: (sequence: string) =>
    req<Properties>(`/properties?sequence=${encodeURIComponent(sequence)}`),

  /** Returns raw SVG markup, not JSON. */
  wheel: async (sequence: string): Promise<string> => {
    const res = await fetch(`${BASE}/wheel?sequence=${encodeURIComponent(sequence)}`);
    if (!res.ok) throw new Error(`wheel ${res.status}`);
    return res.text();
  },

  compare: (sequences: string[], species: string) =>
    req<CompareResponse>("/compare", {
      method: "POST",
      body: JSON.stringify({ sequences, species }),
    }),

  evidence: (sequence: string, species: string) =>
    req<EvidenceResponse>(
      `/evidence?sequence=${encodeURIComponent(sequence)}&species=${encodeURIComponent(species)}`,
    ),

  graph: (sequence: string, species: string) =>
    req<GraphResponse>(
      `/graph?sequence=${encodeURIComponent(sequence)}&species=${encodeURIComponent(species)}`,
    ),

  structure: (sequence: string) =>
    req<Structure>(`/structure?sequence=${encodeURIComponent(sequence)}`),

  structureCompare: (sequences: string[]) =>
    req<{ rmsd: number | null; reason?: string }>(
      `/structure/compare?sequences=${encodeURIComponent(sequences.join(","))}`,
    ),

  /** Experiments and lab memory (phase 8). */
  experiments: {
    record: (body: {
      sequence: string; assay: "MIC" | "hemolysis"; outcome: Outcome;
      measured_value?: number | null; unit?: string | null;
      project_id?: number | null; run_item_id?: number | null; notes?: string | null;
    }) => req<ExperimentOut>("/experiments", { method: "POST", body: JSON.stringify(body) }),
    list: (params: { project_id?: number; sequence?: string; limit?: number } = {}) => {
      const q = new URLSearchParams();
      if (params.project_id != null) q.set("project_id", String(params.project_id));
      if (params.sequence) q.set("sequence", params.sequence);
      if (params.limit) q.set("limit", String(params.limit));
      const qs = q.toString();
      return req<ExperimentOut[]>(`/experiments${qs ? `?${qs}` : ""}`);
    },
    remove: (id: number) => req<{ deleted: number }>(`/experiments/${id}`, { method: "DELETE" }),
  },

  labMemory: (sequences?: string[]) =>
    req<LabMemorySummary>(
      `/lab-memory${sequences?.length ? `?sequences=${encodeURIComponent(sequences.join(","))}` : ""}`,
    ),

  registry: (limit = 200) => req<RegistryEntry[]>(`/registry?limit=${limit}`),

  /** Saved runs (phase 6). Every shortlist is persisted automatically. */
  runs: {
    list: (params: { limit?: number; project_id?: number; scientist_id?: number } = {}) => {
      const q = new URLSearchParams();
      if (params.limit) q.set("limit", String(params.limit));
      if (params.project_id != null) q.set("project_id", String(params.project_id));
      if (params.scientist_id != null) q.set("scientist_id", String(params.scientist_id));
      const qs = q.toString();
      return req<RunSummary[]>(`/runs${qs ? `?${qs}` : ""}`);
    },
    get: (id: number) => req<RunDetail>(`/runs/${id}`),
    label: (id: number, label: string) =>
      req<RunSummary>(`/runs/${id}`, { method: "PATCH", body: JSON.stringify({ label }) }),
    remove: (id: number) => req<{ deleted: number }>(`/runs/${id}`, { method: "DELETE" }),
  },

  // --- Phase 7 Auth & Projects ---------------------------------------------
  auth: {
    register: (body: RegisterRequest) =>
      req<TokenResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    login: (body: LoginRequest) =>
      req<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    me: () => req<Scientist>("/auth/me"),
  },

  projects: {
    list: () => req<Project[]>("/projects"),
    mine: () => req<Project[]>("/projects/mine"),
    create: (body: ProjectCreate) =>
      req<Project>("/projects", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    get: (id: number) => req<Project>(`/projects/${id}`),
    addMember: (projectId: number, body: ProjectMemberAdd) =>
      req<{ message: string }>(`/projects/${projectId}/members`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    delete: (projectId: number) =>
      req<{ deleted: number }>(`/projects/${projectId}`, {
        method: "DELETE",
      }),
  },

  // --- Phase 9 Analytics ----------------------------------------------------
  analytics: (params: { project_id?: number | null; include_seeded?: boolean } = {}) => {
    const q = new URLSearchParams();
    if (params.project_id != null) q.set("project_id", String(params.project_id));
    if (params.include_seeded != null) q.set("include_seeded", String(params.include_seeded));
    const qs = q.toString();
    return req<AnalyticsOut>(`/analytics${qs ? `?${qs}` : ""}`);
  },

  propertiesBreakdown: (params: { project_id?: number | null; include_seeded?: boolean } = {}) => {
    const q = new URLSearchParams();
    if (params.project_id != null) q.set("project_id", String(params.project_id));
    if (params.include_seeded != null) q.set("include_seeded", String(params.include_seeded));
    const qs = q.toString();
    return req<PropertiesBreakdownOut>(`/analytics/properties-breakdown${qs ? `?${qs}` : ""}`);
  },
};

// --- Phase 9 Shapes ---------------------------------------------------------

export interface CalibrationBucket {
  predicted_lower: number;
  predicted_upper: number;
  n: number;
  observed_hit_rate: number | null;
}

export interface RoundStat {
  run_id: number;
  created_at: string;
  n_tested: number;
  n_hits: number;
  hit_rate: number | null;
}

export interface AnalyticsOut {
  project_id: number | null;
  n_runs: number;
  n_experiments: number;
  overall_hit_rate: number | null;
  calibration: CalibrationBucket[];
  rounds: RoundStat[];
  cumulative_chemotypes: number[];
}

export interface PropertyGroupStats {
  n: number;
  mean_charge: number | null;
  mean_uH: number | null;
  mean_length: number | null;
}

export interface PropertiesBreakdownOut {
  hits: PropertyGroupStats;
  misses: PropertyGroupStats;
}

// --- Phase 7 Shapes ---------------------------------------------------------

export interface Scientist {
  id: number;
  lab_id: number;
  email: string;
  full_name: string;
  role: "lead" | "scientist" | "viewer" | string;
  created_at: string;
}

export interface RegisterRequest {
  email: string;
  full_name: string;
  password: string;
  lab_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  scientist: Scientist;
}

export interface Project {
  id: number;
  lab_id: number;
  name: string;
  target_species: string;
  status: string;
  created_by?: number | null;
  is_seeded?: boolean;
  created_at: string;
  n_runs: number;
  n_members: number;
}

export interface ProjectCreate {
  name: string;
  target_species: string;
  status?: string;
}

export interface ProjectMemberAdd {
  scientist_id: number;
  role: string;
}

// --- formatting helpers (presentation only, no science) ------------------------

export const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
export const f3 = (v: number) => v.toFixed(3);
export const f2 = (v: number) => v.toFixed(2);

export const confidenceStyle: Record<Confidence, string> = {
  high: "bg-secondary-container text-on-secondary-container",
  moderate: "bg-primary-fixed text-on-primary-fixed-variant",
  low: "bg-error-container text-on-error-container",
};

export const tierStyle: Record<StructureTier, string> = {
  experimental: "bg-secondary-container text-on-secondary-container",
  predicted: "bg-primary-fixed text-on-primary-fixed-variant",
  unavailable: "bg-surface-container-high text-on-surface-variant",
};

export const tierLabel: Record<StructureTier, string> = {
  experimental: "Experimental (PDB)",
  predicted: "Predicted (ESMFold)",
  unavailable: "No structure",
};
