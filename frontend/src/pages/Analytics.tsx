import { useEffect, useState } from "react";
import {
  api,
  pct,
  f2,
  f3,
  type AnalyticsOut,
  type PropertiesBreakdownOut,
} from "../api";
import {
  Badge,
  Card,
  ErrorNote,
  Icon,
  SectionTitle,
  Stat,
  Spinner,
} from "../components/ui";
import { useStore } from "../store";

export default function Analytics() {
  const { activeProject, projects, setActiveProject } = useStore();
  const [includeSeeded, setIncludeSeeded] = useState(true);
  const [data, setData] = useState<AnalyticsOut | null>(null);
  const [propsData, setPropsData] = useState<PropertiesBreakdownOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.analytics({
        project_id: activeProject ? activeProject.id : null,
        include_seeded: includeSeeded,
      }),
      api.propertiesBreakdown({
        project_id: activeProject ? activeProject.id : null,
        include_seeded: includeSeeded,
      }),
    ])
      .then(([analyticsRes, propsRes]) => {
        setData(analyticsRes);
        setPropsData(propsRes);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [activeProject, includeSeeded]);

  return (
    <div className="max-w-6xl mx-auto space-y-lg py-md">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-md">
        <div>
          <SectionTitle hint="Empirical model calibration, scaffold expansion, and hit-rate progression across rounds">
            Campaign & Calibration Analytics
          </SectionTitle>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Project filter */}
          <label className="flex items-center gap-2">
            <span className="font-label-bold text-xs text-on-surface-variant uppercase">
              Scope:
            </span>
            <select
              className="border border-outline-variant rounded bg-surface-container-lowest px-2 py-1 font-body-md text-body-md text-on-surface"
              value={activeProject ? activeProject.id : ""}
              onChange={(e) => {
                const val = e.target.value;
                if (!val) setActiveProject(null);
                else {
                  const found = projects.find((p) => p.id === Number(val));
                  if (found) setActiveProject(found);
                }
              }}
            >
              <option value="">Lab-Wide (All Campaigns)</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>

          {/* Seeded Data Toggle */}
          <label className="flex items-center gap-2 px-3 py-1 bg-surface-container-lowest border border-outline-variant rounded cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeSeeded}
              onChange={(e) => setIncludeSeeded(e.target.checked)}
              className="rounded text-primary focus:ring-0"
            />
            <span className="font-body-sm text-body-sm text-on-surface">
              Include Public Benchmarks
            </span>
          </label>
        </div>
      </div>

      {error && <ErrorNote>{error}</ErrorNote>}

      {/* Methodological Transparency Note */}
      <Card className="p-md bg-surface-container-low border-outline-variant/60 flex items-start gap-3">
        <Icon name="info" className="text-primary mt-0.5" size={20} />
        <div className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
          <strong className="text-on-surface">Calibration & Negative Exclusion:</strong>{" "}
          Observed wet-lab outcomes calibrate predicted probabilities and trigger institutional
          exclusion of dead scaffolds across campaigns. Empirical small-sample results do not retrain
          foundation ESM2 embeddings. Calibration points require a minimum of{" "}
          <span className="font-bold text-primary">n ≥ 3</span> assays per bucket to prevent
          spurious rate estimation.
        </div>
      </Card>

      {loading && !data ? (
        <div className="py-xl flex justify-center">
          <Spinner label="Computing calibration and chemotype trajectories…" />
        </div>
      ) : data && data.n_experiments === 0 ? (
        <Card className="p-xl text-center text-on-surface-variant space-y-3">
          <Icon name="analytics" className="text-outline text-5xl mx-auto" />
          <h3 className="font-headline-sm text-headline-sm text-on-surface">
            No Experimental Results Recorded
          </h3>
          <p className="font-body-md text-body-md text-outline max-w-md mx-auto">
            {activeProject
              ? `No wet-lab assays recorded yet for campaign '${activeProject.name}'.`
              : "No wet-lab assays recorded in this research unit yet."}
          </p>
          <div className="font-body-sm text-body-sm text-outline">
            Record assays on the Candidate screen or execute shortlist selections to populate calibration curves.
          </div>
        </Card>
      ) : data ? (
        <>
          {/* Top High-Level Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-md">
            <Stat
              label="Total Selections"
              value={data.n_runs}
              sub={activeProject ? "In this campaign" : "Across lab"}
            />
            <Stat
              label="Assays Logged"
              value={data.n_experiments}
              sub={includeSeeded ? "Lab + Seeded DBAASP" : "In-house wet-lab only"}
            />
            <Stat
              label="Overall Hit Rate"
              value={data.overall_hit_rate != null ? pct(data.overall_hit_rate) : "N/A"}
              tone={
                data.overall_hit_rate != null && data.overall_hit_rate >= 0.5
                  ? "good"
                  : "default"
              }
              sub={
                data.overall_hit_rate != null
                  ? `${Math.round(data.overall_hit_rate * data.n_experiments)} confirmed hits`
                  : "Pending results"
              }
            />
            <Stat
              label="Scaffolds Explored"
              value={
                data.cumulative_chemotypes.length > 0
                  ? data.cumulative_chemotypes[data.cumulative_chemotypes.length - 1]
                  : 0
              }
              tone="good"
              sub="Unique chemotype clusters"
            />
          </div>

          {/* Hero Chart: Model Calibration */}
          <Card className="p-lg space-y-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-outline-variant pb-md">
              <div>
                <h3 className="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2">
                  <Icon name="straighten" className="text-primary" />
                  Model Calibration Curve
                </h3>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
                  Predicted P(active) vs. observed wet-lab hit rate. A well-calibrated classifier tracks the diagonal.
                </p>
              </div>
              <Badge className="bg-surface-container-high text-on-surface-variant">
                5 Probability Bins
              </Badge>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-lg items-center">
              {/* SVG Calibration Plot */}
              <div className="lg:col-span-7 flex justify-center py-2">
                <svg
                  viewBox="0 0 420 340"
                  className="w-full max-w-[420px] h-auto select-none bg-surface-container-lowest rounded-lg border border-outline-variant/50 p-2"
                >
                  <defs>
                    <linearGradient id="calibGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#005ea5" stopOpacity="0.2" />
                      <stop offset="100%" stopColor="#005ea5" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Grid Lines */}
                  {[0, 0.2, 0.4, 0.6, 0.8, 1.0].map((v) => {
                    const y = 280 - v * 240;
                    const x = 50 + v * 330;
                    return (
                      <g key={v}>
                        <line
                          x1="50"
                          y1={y}
                          x2="380"
                          y2={y}
                          stroke="#e8eff1"
                          strokeWidth="1"
                        />
                        <line
                          x1={x}
                          y1="40"
                          x2={x}
                          y2="280"
                          stroke="#e8eff1"
                          strokeWidth="1"
                        />
                        {/* Axis Labels */}
                        <text
                          x="42"
                          y={y + 4}
                          textAnchor="end"
                          fontSize="10"
                          fill="#707784"
                          fontFamily="Inter"
                        >
                          {v.toFixed(1)}
                        </text>
                        <text
                          x={x}
                          y="298"
                          textAnchor="middle"
                          fontSize="10"
                          fill="#707784"
                          fontFamily="Inter"
                        >
                          {v.toFixed(1)}
                        </text>
                      </g>
                    );
                  })}

                  {/* Ideal Reference Diagonal (y = x) */}
                  <line
                    x1="50"
                    y1="280"
                    x2="380"
                    y2="40"
                    stroke="#a2c9ff"
                    strokeWidth="2"
                    strokeDasharray="5 4"
                  />

                  {/* Connecting line between valid observed points */}
                  {(() => {
                    const validPoints = data.calibration
                      .filter((b) => b.observed_hit_rate != null)
                      .map((b) => {
                        const midPred = (b.predicted_lower + b.predicted_upper) / 2.0;
                        const x = 50 + midPred * 330;
                        const y = 280 - (b.observed_hit_rate as number) * 240;
                        return { x, y };
                      });

                    if (validPoints.length >= 2) {
                      const d = validPoints
                        .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
                        .join(" ");
                      return <path d={d} fill="none" stroke="#005ea5" strokeWidth="2.5" />;
                    }
                    return null;
                  })()}

                  {/* Plotted Calibration Points */}
                  {data.calibration.map((bucket, i) => {
                    const midPred = (bucket.predicted_lower + bucket.predicted_upper) / 2.0;
                    const x = 50 + midPred * 330;

                    if (bucket.observed_hit_rate != null) {
                      const y = 280 - bucket.observed_hit_rate * 240;
                      return (
                        <g key={i}>
                          <circle
                            cx={x}
                            cy={y}
                            r="6"
                            fill="#005ea5"
                            stroke="#ffffff"
                            strokeWidth="2"
                          />
                          <text
                            x={x}
                            y={y - 10}
                            textAnchor="middle"
                            fontSize="11"
                            fontWeight="600"
                            fill="#005ea5"
                            fontFamily="Inter"
                          >
                            {pct(bucket.observed_hit_rate)}
                          </text>
                        </g>
                      );
                    } else if (bucket.n > 0) {
                      // Underpowered bucket indicator
                      return (
                        <g key={i}>
                          <circle
                            cx={x}
                            cy="280"
                            r="4"
                            fill="#c0c7d4"
                            stroke="#707784"
                            strokeDasharray="2 2"
                          />
                          <text
                            x={x}
                            y="268"
                            textAnchor="middle"
                            fontSize="9"
                            fill="#707784"
                            fontFamily="Inter"
                          >
                            n={bucket.n} (&lt;3)
                          </text>
                        </g>
                      );
                    }
                    return null;
                  })}

                  {/* Axis Title */}
                  <text
                    x="215"
                    y="322"
                    textAnchor="middle"
                    fontSize="11"
                    fontWeight="600"
                    fill="#404752"
                    fontFamily="Inter"
                  >
                    Predicted P(active) Bin
                  </text>
                  <text
                    x="-160"
                    y="16"
                    textAnchor="middle"
                    fontSize="11"
                    fontWeight="600"
                    fill="#404752"
                    fontFamily="Inter"
                    transform="rotate(-90)"
                  >
                    Observed Hit Rate
                  </text>
                </svg>
              </div>

              {/* Calibration Bins Table */}
              <div className="lg:col-span-5 space-y-sm">
                <div className="font-label-bold text-xs text-on-surface-variant uppercase mb-2">
                  Reliability Table by Probability Decile
                </div>
                <div className="divide-y divide-outline-variant/60 border border-outline-variant rounded-lg overflow-hidden bg-surface-container-lowest">
                  {data.calibration.map((b, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 flex items-center justify-between text-body-sm"
                    >
                      <div className="flex items-center gap-2">
                        <span className="mono font-code-md text-xs font-semibold text-on-surface">
                          [{b.predicted_lower.toFixed(1)} – {b.predicted_upper.toFixed(1)}]
                        </span>
                        <span className="text-outline text-xs">({b.n} tested)</span>
                      </div>

                      <div>
                        {b.observed_hit_rate != null ? (
                          <Badge className="bg-secondary-container text-on-secondary-container">
                            {pct(b.observed_hit_rate)}
                          </Badge>
                        ) : b.n > 0 ? (
                          <span className="text-outline text-xs italic">
                            Insufficient Data (n&lt;3)
                          </span>
                        ) : (
                          <span className="text-outline text-xs">No assays</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="text-[11px] text-outline pt-1">
                  * Dotted line indicates perfect diagonal calibration. Points above indicate conservative predictions; points below indicate optimism.
                </div>
              </div>
            </div>
          </Card>

          {/* Dual Panel: Hit Rate per Round & Cumulative Chemotypes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
            {/* Round-by-Round Hit Rate */}
            <Card className="p-md space-y-md">
              <div className="flex items-center justify-between border-b border-outline-variant pb-2">
                <h4 className="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2">
                  <Icon name="trending_up" className="text-primary" />
                  Hit Rate Progression
                </h4>
                <Badge className="bg-surface-container-high text-on-surface-variant">
                  {data.rounds.length} Selection Rounds
                </Badge>
              </div>

              {data.rounds.length === 0 ? (
                <div className="py-lg text-center text-outline font-body-sm">
                  No selection rounds recorded yet.
                </div>
              ) : (
                <div className="space-y-sm">
                  {data.rounds.map((r, i) => (
                    <div
                      key={r.run_id}
                      className="p-3 bg-surface-container-low rounded border border-outline-variant/60 flex items-center justify-between"
                    >
                      <div>
                        <div className="font-label-bold text-xs text-on-surface">
                          Round #{i + 1} (Run ID: {r.run_id})
                        </div>
                        <div className="font-body-sm text-xs text-outline">
                          {r.n_tested > 0
                            ? `${r.n_hits} active hits / ${r.n_tested} tested`
                            : "Awaiting wet-lab assay logging"}
                        </div>
                      </div>

                      <div>
                        {r.hit_rate != null ? (
                          <Badge
                            className={
                              r.hit_rate >= 0.5
                                ? "bg-secondary-container text-on-secondary-container"
                                : "bg-primary-fixed text-on-primary-fixed-variant"
                            }
                          >
                            {pct(r.hit_rate)}
                          </Badge>
                        ) : (
                          <span className="text-outline text-xs">Unassayed</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Cumulative Chemotype Coverage */}
            <Card className="p-md space-y-md">
              <div className="flex items-center justify-between border-b border-outline-variant pb-2">
                <h4 className="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2">
                  <Icon name="hub" className="text-secondary" />
                  Cumulative Scaffold Exploration
                </h4>
                <span className="text-xs text-outline font-body-sm">
                  Cosine Threshold = 0.10
                </span>
              </div>

              {data.cumulative_chemotypes.length === 0 ? (
                <div className="py-lg text-center text-outline font-body-sm">
                  No scaffolds recorded yet.
                </div>
              ) : (
                <div className="space-y-md">
                  <p className="font-body-sm text-xs text-on-surface-variant">
                    Number of distinct structural chemotype families explored as the campaign progresses:
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {data.cumulative_chemotypes.map((count, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 bg-surface-container-low rounded border border-outline-variant/60 text-center"
                      >
                        <div className="text-[11px] font-label-bold text-on-surface-variant uppercase">
                          After Round {idx + 1}
                        </div>
                        <div className="font-headline-md text-secondary font-bold mt-0.5">
                          {count}
                        </div>
                        <div className="text-[10px] text-outline">Distinct Chemotypes</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>

          {/* Property Distributions: Confirmed Hits vs Misses */}
          {propsData && (propsData.hits.n > 0 || propsData.misses.n > 0) && (
            <Card className="p-lg space-y-md">
              <div className="border-b border-outline-variant pb-2 flex items-center justify-between">
                <div>
                  <h3 className="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2">
                    <Icon name="biotech" className="text-primary" />
                    Biophysical Properties: Hits vs. Misses
                  </h3>
                  <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
                    Empirical distributions of confirmed active candidates versus inactive/toxic variants.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
                {/* Active Hits Panel */}
                <div className="p-md bg-secondary/5 rounded-lg border border-secondary/20 space-y-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-label-bold text-sm text-secondary uppercase flex items-center gap-1.5">
                      <Icon name="check_circle" size={16} />
                      Confirmed Active Hits
                    </span>
                    <Badge className="bg-secondary-container text-on-secondary-container">
                      n = {propsData.hits.n}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-2 text-center">
                    <div className="bg-surface-container-lowest p-2 rounded border border-outline-variant/40">
                      <div className="text-[10px] font-label-bold text-outline uppercase">
                        Mean Net Charge
                      </div>
                      <div className="font-headline-sm text-on-surface mt-0.5">
                        {propsData.hits.mean_charge != null ? `+${f2(propsData.hits.mean_charge)}` : "—"}
                      </div>
                    </div>
                    <div className="bg-surface-container-lowest p-2 rounded border border-outline-variant/40">
                      <div className="text-[10px] font-label-bold text-outline uppercase">
                        Mean μH (Moment)
                      </div>
                      <div className="font-headline-sm text-on-surface mt-0.5">
                        {propsData.hits.mean_uH != null ? f3(propsData.hits.mean_uH) : "—"}
                      </div>
                    </div>
                    <div className="bg-surface-container-lowest p-2 rounded border border-outline-variant/40">
                      <div className="text-[10px] font-label-bold text-outline uppercase">
                        Mean Length
                      </div>
                      <div className="font-headline-sm text-on-surface mt-0.5">
                        {propsData.hits.mean_length != null ? `${propsData.hits.mean_length} aa` : "—"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Inactive / Toxic Misses Panel */}
                <div className="p-md bg-error/5 rounded-lg border border-error/20 space-y-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-label-bold text-sm text-error uppercase flex items-center gap-1.5">
                      <Icon name="cancel" size={16} />
                      Inactive / Toxic Misses
                    </span>
                    <Badge className="bg-error-container text-on-error-container">
                      n = {propsData.misses.n}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-2 text-center">
                    <div className="bg-surface-container-lowest p-2 rounded border border-outline-variant/40">
                      <div className="text-[10px] font-label-bold text-outline uppercase">
                        Mean Net Charge
                      </div>
                      <div className="font-headline-sm text-on-surface mt-0.5">
                        {propsData.misses.mean_charge != null ? `+${f2(propsData.misses.mean_charge)}` : "—"}
                      </div>
                    </div>
                    <div className="bg-surface-container-lowest p-2 rounded border border-outline-variant/40">
                      <div className="text-[10px] font-label-bold text-outline uppercase">
                        Mean μH (Moment)
                      </div>
                      <div className="font-headline-sm text-on-surface mt-0.5">
                        {propsData.misses.mean_uH != null ? f3(propsData.misses.mean_uH) : "—"}
                      </div>
                    </div>
                    <div className="bg-surface-container-lowest p-2 rounded border border-outline-variant/40">
                      <div className="text-[10px] font-label-bold text-outline uppercase">
                        Mean Length
                      </div>
                      <div className="font-headline-sm text-on-surface mt-0.5">
                        {propsData.misses.mean_length != null ? `${propsData.misses.mean_length} aa` : "—"}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          )}
        </>
      ) : null}
    </div>
  );
}
