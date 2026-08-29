/** The core screen: build a diverse, selectivity-aware shortlist under a testing budget. */
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { f3, pct } from "../api";
import { useStore } from "../store";
import { Card, ConfidenceBadge, ErrorNote, Icon, Meter, SectionTitle, Seq, Spinner, Stat } from "../components/ui";

export default function Shortlist() {
  const {
    species, speciesMeta, pool, poolName, k, setK, theta, setTheta,
    shortlist, runShortlist, loading, error, tray, toggleTray, setFocus,
    excludeTested, setExcludeTested, penaliseTested, setPenaliseTested, user,
  } = useStore();
  const navigate = useNavigate();

  // Re-rank whenever the target, budget or theta changes -- theta must feel live.
  useEffect(() => {
    if (pool.length) void runShortlist();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [species, k, theta, pool.length, excludeTested, penaliseTested]);

  const items = shortlist?.items ?? [];
  const topSet = new Set(shortlist?.baseline_top_n ?? []);
  const onlyGreedy = items.filter((i) => !topSet.has(i.sequence)).length;
  const meanSim = items.length > 1
    ? items.slice(1).reduce((a, i) => a + i.similarity_to_nearest_selected, 0) / (items.length - 1)
    : 0;

  return (
    <>
      <div className="mb-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="font-headline-lg text-headline-lg text-on-surface mb-1">Experimental Shortlist</h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            {items.length} candidates selected from {pool.length.toLocaleString()} analysed peptides
            {" · "}<span className="italic">{poolName}</span>
          </p>
          {speciesMeta && (
            <div className="mt-2">
              <ConfidenceBadge
                confidence={speciesMeta.confidence}
                roc={speciesMeta.cv_roc_auc}
                std={speciesMeta.cv_roc_auc_std}
              />
            </div>
          )}
        </div>

        <Card className="p-md flex flex-wrap items-center gap-lg">
          <label className="flex items-center gap-2">
            <span className="font-label-bold text-label-bold text-on-surface-variant uppercase">Budget k</span>
            <input type="range" min={5} max={40} step={5} value={k}
              onChange={(e) => setK(Number(e.target.value))}
              className="w-28 accent-primary cursor-pointer" />
            <span className="mono font-code-md text-code-md bg-surface-container px-2 py-0.5 border border-outline-variant rounded w-9 text-center">{k}</span>
          </label>
          <label className="flex items-center gap-2">
            <span className="font-label-bold text-label-bold text-on-surface-variant uppercase">θ quality pull</span>
            <input type="range" min={0.2} max={3} step={0.1} value={theta}
              onChange={(e) => setTheta(Number(e.target.value))}
              className="w-28 accent-primary cursor-pointer" />
            <span className="mono font-code-md text-code-md bg-surface-container px-2 py-0.5 border border-outline-variant rounded w-11 text-center">{theta.toFixed(1)}</span>
          </label>
        </Card>
      </div>

      {user && (
        <Card className="p-md mb-lg">
          <div className="flex flex-wrap items-center gap-lg">
            <div className="font-label-bold text-label-bold text-on-surface-variant uppercase">
              Lab memory
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="accent-primary" checked={excludeTested}
                onChange={(e) => { setExcludeTested(e.target.checked); if (e.target.checked) setPenaliseTested(false); }} />
              <span className="font-body-md text-body-md">Skip peptides this lab already tested</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="accent-primary" checked={penaliseTested}
                onChange={(e) => { setPenaliseTested(e.target.checked); if (e.target.checked) setExcludeTested(false); }} />
              <span className="font-body-md text-body-md">Down-weight instead of skipping</span>
            </label>
          </div>
          {shortlist && shortlist.n_excluded > 0 && (
            <div className="mt-md bg-secondary-container text-on-secondary-container rounded-lg p-3">
              <div className="font-body-md text-body-md">
                <strong>{shortlist.n_excluded} candidate{shortlist.n_excluded === 1 ? "" : "s"} skipped</strong>
                {" "}— already tested by this lab, so the budget went elsewhere.
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {shortlist.excluded_sequences.map((sq) => (
                  <span key={sq} className="mono font-code-md text-code-md bg-surface-container-lowest/70 px-2 py-0.5 rounded border border-outline-variant">
                    {sq.length > 26 ? `${sq.slice(0, 24)}…` : sq}
                  </span>
                ))}
              </div>
            </div>
          )}
          <p className="font-body-sm text-body-sm text-on-surface-variant mt-2">
            Diversity inside one batch stops you buying twenty near-copies. Lab memory
            extends that across every round this lab has ever run, so two scientists on
            different pathogens do not pay twice for the same dead end.
          </p>
        </Card>
      )}

      <p className="font-body-sm text-body-sm text-on-surface-variant mb-lg max-w-3xl">
        θ below 1 favours diversity, above 1 favours raw quality. At high θ the selection
        converges to a plain top-N score sort — top-N is not a rival algorithm, it is this
        objective with diversity switched off.
      </p>

      {error && <div className="mb-lg"><ErrorNote>{error}</ErrorNote></div>}
      {loading && <div className="mb-lg"><Spinner label="Scoring pool and running greedy selection…" /></div>}

      {shortlist && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-md mb-lg">
            <Stat label="log det(L+I)" value={shortlist.logdet.toFixed(3)} sub="objective value achieved" />
            <Stat label="Mean redundancy" value={f3(meanSim)} sub="similarity to nearest selected" tone="good" />
            <Stat label="Unique to greedy" value={`${onlyGreedy} / ${items.length}`} sub="picks top-N would have missed" tone="warn" />
            <Stat label="Mean P(toxic)" value={pct(items.reduce((a, i) => a + i.p_toxic, 0) / (items.length || 1))} sub="lower is safer" />
          </div>

          <SectionTitle hint="Similarity-to-nearest answers “why both, and not two copies of the better one”.">
            Ranked candidates
          </SectionTitle>

          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-surface-container-low border-b border-outline-variant">
                  <tr className="font-label-bold text-label-bold text-on-surface-variant uppercase">
                    <th className="px-3 py-2">#</th>
                    <th className="px-3 py-2">Sequence</th>
                    <th className="px-3 py-2">q<sub>i</sub></th>
                    <th className="px-3 py-2">P(active)</th>
                    <th className="px-3 py-2">P(toxic)</th>
                    <th className="px-3 py-2">Sim. to nearest</th>
                    <th className="px-3 py-2">Gain</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => {
                    const novel = !topSet.has(it.sequence);
                    return (
                      <tr key={it.sequence} className="border-b border-outline-variant last:border-0 hover:bg-surface-container-low">
                        <td className="px-3 py-2 mono font-code-md text-code-md text-on-surface-variant">{it.rank}</td>
                        <td className="px-3 py-2 max-w-[16rem]">
                          <Seq className="text-on-surface">{it.sequence}</Seq>
                          {novel && (
                            <div className="font-label-bold text-label-bold text-secondary uppercase mt-0.5">
                              diversity pick
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-2 mono font-code-md text-code-md font-medium">{f3(it.q_i)}</td>
                        <td className="px-3 py-2 w-28">
                          <div className="mono font-code-md text-code-md">{pct(it.p_active)}</div>
                          <Meter value={it.p_active} tone="secondary" />
                        </td>
                        <td className="px-3 py-2 w-28">
                          <div className="mono font-code-md text-code-md">{pct(it.p_toxic)}</div>
                          <Meter value={it.p_toxic} tone="error" />
                        </td>
                        <td className="px-3 py-2 mono font-code-md text-code-md">
                          {it.rank === 1 ? <span className="text-outline">—</span> : f3(it.similarity_to_nearest_selected)}
                        </td>
                        <td className="px-3 py-2 mono font-code-md text-code-md text-on-surface-variant">{it.marginal_log_gain.toFixed(3)}</td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          <button
                            title="Open candidate"
                            className="text-primary hover:bg-surface-container rounded p-1"
                            onClick={() => { setFocus(it.sequence); navigate("/candidate"); }}
                          >
                            <Icon name="open_in_new" size={18} />
                          </button>
                          <button
                            title={tray.includes(it.sequence) ? "Remove from compare" : "Add to compare"}
                            className={`rounded p-1 ${tray.includes(it.sequence) ? "text-primary bg-surface-container-high" : "text-on-surface-variant hover:bg-surface-container"}`}
                            onClick={() => toggleTray(it.sequence)}
                          >
                            <Icon name="compare_arrows" size={18} fill={tray.includes(it.sequence)} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          <p className="font-body-sm text-body-sm text-on-surface-variant mt-md">
            Marginal gain is non-increasing down the list — that is the submodularity of the
            log-determinant objective visible in the output. Greedy is near-optimal with
            respect to that objective (1 − 1/e), not with respect to raw diversity.
          </p>
        </>
      )}
    </>
  );
}
