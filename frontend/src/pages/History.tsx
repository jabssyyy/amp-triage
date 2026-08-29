/** Phase 6b — saved runs.
 *
 *  Every shortlist the system produces is persisted automatically. Reopening one shows
 *  the scores exactly as they were when the decision was made; retraining a model does
 *  not rewrite history. That is the point of the screen, not a technicality — a
 *  scientist who synthesised twenty peptides on the strength of a shortlist needs that
 *  shortlist to still say what it said.
 */
import { useCallback, useEffect, useState } from "react";
import { api, f3, pct, type RunDetail, type RunSummary } from "../api";
import { Button, Card, ErrorNote, Icon, Placeholder, SectionTitle, Seq, Spinner } from "../components/ui";

function when(iso: string): string {
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  const mins = Math.round((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  if (mins < 1440) return `${Math.round(mins / 60)} h ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function History() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [open, setOpen] = useState<RunDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    setErr(null);
    api.runs.list({ limit: 50 })
      .then(setRuns)
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(load, [load]);

  const openRun = (id: number) => {
    setBusy(true);
    api.runs.get(id)
      .then(setOpen)
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
      .finally(() => setBusy(false));
  };

  const removeRun = async (id: number) => {
    await api.runs.remove(id).catch(() => void 0);
    if (open?.id === id) setOpen(null);
    load();
  };

  const rename = async (run: RunSummary) => {
    const label = window.prompt("Name this run", run.label ?? "");
    if (label === null) return;
    await api.runs.label(run.id, label).catch(() => void 0);
    load();
  };

  return (
    <>
      <div className="mb-lg flex justify-between items-start gap-4 flex-wrap">
        <div>
          <h1 className="font-headline-lg text-headline-lg text-on-surface mb-1">Run History</h1>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
            Every shortlist is saved automatically. Reopening one shows the scores exactly as
            they were at the time — a decision record, not a live recalculation.
          </p>
        </div>
        <Button variant="outlined" onClick={load}>
          <Icon name="refresh" size={18} /> Refresh
        </Button>
      </div>

      {err && <div className="mb-lg"><ErrorNote>{err}</ErrorNote></div>}
      {!runs && !err && <Spinner label="Loading saved runs…" />}
      {runs && runs.length === 0 && (
        <Placeholder what="No runs saved yet. Generate a shortlist and it will appear here." />
      )}

      {runs && runs.length > 0 && (
        <Card className="overflow-hidden mb-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-surface-container-low border-b border-outline-variant">
                <tr className="font-label-bold text-label-bold text-on-surface-variant uppercase">
                  <th className="px-3 py-2">Run</th>
                  <th className="px-3 py-2">Target</th>
                  <th className="px-3 py-2">k</th>
                  <th className="px-3 py-2">θ</th>
                  <th className="px-3 py-2">Pool</th>
                  <th className="px-3 py-2">log det</th>
                  <th className="px-3 py-2">By</th>
                  <th className="px-3 py-2">When</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr
                    key={r.id}
                    className={`border-b border-outline-variant last:border-0 hover:bg-surface-container-low cursor-pointer ${
                      open?.id === r.id ? "bg-surface-container-low" : ""
                    }`}
                    onClick={() => openRun(r.id)}
                  >
                    <td className="px-3 py-2">
                      <div className="font-body-md text-body-md text-on-surface">
                        {r.label ?? `Run #${r.id}`}
                      </div>
                      <div className="font-body-sm text-body-sm text-on-surface-variant">
                        {r.n_items} selected
                        {r.n_excluded > 0 && ` · ${r.n_excluded} skipped`}
                      </div>
                    </td>
                    <td className="px-3 py-2 font-body-md text-body-md italic">{r.species}</td>
                    <td className="px-3 py-2 mono font-code-md text-code-md">{r.k}</td>
                    <td className="px-3 py-2 mono font-code-md text-code-md">{r.theta.toFixed(1)}</td>
                    <td className="px-3 py-2 mono font-code-md text-code-md">{r.pool_size}</td>
                    <td className="px-3 py-2 mono font-code-md text-code-md">{r.logdet.toFixed(3)}</td>
                    <td className="px-3 py-2 font-body-sm text-body-sm text-on-surface-variant">
                      {r.scientist_name ?? "—"}
                    </td>
                    <td className="px-3 py-2 font-body-sm text-body-sm text-on-surface-variant whitespace-nowrap">
                      {when(r.created_at)}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <button
                        title="Rename"
                        className="text-on-surface-variant hover:text-primary hover:bg-surface-container rounded p-1"
                        onClick={(e) => { e.stopPropagation(); void rename(r); }}
                      >
                        <Icon name="edit" size={18} />
                      </button>
                      <button
                        title="Delete"
                        className="text-on-surface-variant hover:text-error hover:bg-surface-container rounded p-1"
                        onClick={(e) => { e.stopPropagation(); void removeRun(r.id); }}
                      >
                        <Icon name="delete" size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {busy && <Spinner label="Opening run…" />}

      {open && (
        <Card className="p-md">
          <SectionTitle hint={`Saved ${when(open.created_at)} · k=${open.k} · θ=${open.theta.toFixed(1)} · pool ${open.pool_size} · log det ${open.logdet.toFixed(3)}`}>
            {open.label ?? `Run #${open.id}`} — {open.species}
          </SectionTitle>
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
                </tr>
              </thead>
              <tbody>
                {open.items.map((it) => (
                  <tr key={it.rank} className="border-b border-outline-variant last:border-0">
                    <td className="px-3 py-2 mono font-code-md text-code-md text-on-surface-variant">{it.rank}</td>
                    <td className="px-3 py-2 max-w-[18rem]">
                      <Seq className="text-on-surface">{it.sequence}</Seq>
                      {it.is_diversity_pick && (
                        <div className="font-label-bold text-label-bold text-secondary uppercase mt-0.5">
                          diversity pick
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-2 mono font-code-md text-code-md font-medium">{f3(it.q_i)}</td>
                    <td className="px-3 py-2 mono font-code-md text-code-md">{pct(it.p_active)}</td>
                    <td className="px-3 py-2 mono font-code-md text-code-md">{pct(it.p_toxic)}</td>
                    <td className="px-3 py-2 mono font-code-md text-code-md">
                      {it.rank === 1 ? <span className="text-outline">—</span> : f3(it.similarity_to_nearest)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="font-body-sm text-body-sm text-outline mt-md">
            These are the scores as recorded at selection time. They do not change when a
            model is retrained.
          </p>
        </Card>
      )}
    </>
  );
}
