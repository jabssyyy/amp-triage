/** Phase 8 — record a wet-lab result for a peptide, and show what the lab already knows.
 *
 *  This is where the loop closes. A shortlist is a prediction; this is the outcome
 *  coming back, and once it is here the selector stops offering the peptide to anyone
 *  else in the lab.
 *
 *  Results recorded here are always source='wet_lab' — the backend forces it. Seeded
 *  public records are shown with a distinct badge and can never be created from the UI.
 */
import { useCallback, useEffect, useState } from "react";
import { api, outcomeStyle, type ExperimentOut, type Outcome } from "../api";
import { useStore } from "../store";
import { Badge, Button, Card, Icon, SectionTitle, Spinner } from "./ui";

const OUTCOMES: { value: Outcome; label: string; hint: string }[] = [
  { value: "hit", label: "Hit", hint: "active at or below the breakpoint" },
  { value: "miss", label: "Miss", hint: "no useful activity" },
  { value: "toxic", label: "Toxic", hint: "unacceptable haemolysis" },
  { value: "inconclusive", label: "Inconclusive", hint: "assay did not resolve" },
];

function when(iso: string): string {
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function ExperimentPanel({ sequence }: { sequence: string }) {
  const { user, activeProject } = useStore();
  const [rows, setRows] = useState<ExperimentOut[] | null>(null);
  const [assay, setAssay] = useState<"MIC" | "hemolysis">("MIC");
  const [outcome, setOutcome] = useState<Outcome>("hit");
  const [value, setValue] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    api.experiments.list({ sequence })
      .then(setRows)
      .catch(() => setRows([]));
  }, [sequence]);

  useEffect(load, [load]);

  const submit = async () => {
    setSaving(true);
    setErr(null);
    try {
      await api.experiments.record({
        sequence,
        assay,
        outcome,
        measured_value: value.trim() === "" ? null : Number(value),
        unit: assay === "MIC" ? "ug/ml" : "%",
        project_id: activeProject?.id ?? null,
        notes: notes.trim() || null,
      });
      setValue("");
      setNotes("");
      load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="p-md">
      <SectionTitle hint="Recording an outcome here stops this peptide being offered to anyone else in the lab.">
        Wet-lab results
      </SectionTitle>

      {rows === null && <Spinner label="Loading results…" />}

      {rows !== null && rows.length === 0 && (
        <div className="font-body-md text-body-md text-on-surface-variant mb-md">
          No results recorded for this peptide yet.
        </div>
      )}

      {rows !== null && rows.length > 0 && (
        <ul className="space-y-2 mb-md">
          {rows.map((r) => (
            <li key={r.id} className="flex items-center justify-between gap-3 border-b border-outline-variant last:border-0 pb-2 last:pb-0">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge className={outcomeStyle[r.outcome]}>{r.outcome}</Badge>
                <span className="font-body-md text-body-md text-on-surface">{r.assay}</span>
                {r.measured_value != null && (
                  <span className="mono font-code-md text-code-md text-on-surface-variant">
                    {r.measured_value} {r.unit}
                  </span>
                )}
                {r.source === "seeded_public" && (
                  <Badge className="bg-surface-container-high text-on-surface-variant">
                    seeded from public data
                  </Badge>
                )}
              </div>
              <span className="font-body-sm text-body-sm text-outline whitespace-nowrap">
                {when(r.tested_at)}
              </span>
            </li>
          ))}
        </ul>
      )}

      {!user ? (
        <div className="border border-dashed border-outline-variant rounded-lg p-md text-center">
          <Icon name="lock" className="text-outline" />
          <div className="font-body-md text-body-md text-on-surface-variant mt-1">
            Sign in to record a result.
          </div>
        </div>
      ) : (
        <div className="border-t border-outline-variant pt-md">
          <div className="flex flex-wrap items-end gap-md">
            <label className="flex flex-col gap-1">
              <span className="font-label-bold text-label-bold text-on-surface-variant uppercase">Assay</span>
              <select value={assay} onChange={(e) => setAssay(e.target.value as "MIC" | "hemolysis")}
                className="border border-outline-variant rounded px-2 py-1 font-body-md text-body-md bg-surface-container-lowest">
                <option value="MIC">MIC</option>
                <option value="hemolysis">Haemolysis</option>
              </select>
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-label-bold text-label-bold text-on-surface-variant uppercase">Outcome</span>
              <select value={outcome} onChange={(e) => setOutcome(e.target.value as Outcome)}
                className="border border-outline-variant rounded px-2 py-1 font-body-md text-body-md bg-surface-container-lowest">
                {OUTCOMES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-label-bold text-label-bold text-on-surface-variant uppercase">
                Value ({assay === "MIC" ? "µg/ml" : "%"})
              </span>
              <input value={value} onChange={(e) => setValue(e.target.value)} inputMode="decimal"
                placeholder="optional"
                className="border border-outline-variant rounded px-2 py-1 mono font-code-md text-code-md bg-surface-container-lowest w-28" />
            </label>

            <label className="flex flex-col gap-1 flex-1 min-w-[12rem]">
              <span className="font-label-bold text-label-bold text-on-surface-variant uppercase">Notes</span>
              <input value={notes} onChange={(e) => setNotes(e.target.value)}
                placeholder="optional"
                className="border border-outline-variant rounded px-2 py-1 font-body-md text-body-md bg-surface-container-lowest w-full" />
            </label>

            <Button onClick={submit} disabled={saving}>
              <Icon name="science" size={18} /> {saving ? "Saving…" : "Record result"}
            </Button>
          </div>

          <div className="font-body-sm text-body-sm text-on-surface-variant mt-2">
            {OUTCOMES.find((o) => o.value === outcome)?.hint}
            {activeProject ? ` · logged against ${activeProject.name}` : " · no active campaign"}
          </div>
          {err && <div className="font-body-sm text-body-sm text-error mt-1">{err}</div>}
        </div>
      )}
    </Card>
  );
}
