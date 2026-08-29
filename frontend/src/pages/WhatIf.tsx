/** What-if lab: edit a residue, re-score live, see where it would land on the shortlist.
 *
 *  PharmaMind requirement #4. A sequence that is not in the embedding cache is embedded
 *  on the fly by the backend (~37 ms once ESM2 is warm), so hypothetical peptides score
 *  by exactly the same path as known ones.
 */
import { useEffect, useMemo, useState } from "react";
import { api, f3, pct, type Properties, type ScoreResponse } from "../api";
import { useStore } from "../store";
import { Button, Card, ErrorNote, Icon, SectionTitle, Seq, Spinner, Stat } from "../components/ui";

const AA = "ACDEFGHIKLMNPQRSTVWY".split("");

export default function WhatIf() {
  const { focus, species, shortlist } = useStore();
  const original = focus ?? shortlist?.items[0]?.sequence ?? "KWKLFKKIGAVLKVL";

  const [seq, setSeq] = useState(original);
  const [baseline, setBaseline] = useState<ScoreResponse | null>(null);
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [props, setProps] = useState<Properties | null>(null);
  const [wheel, setWheel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { setSeq(original); }, [original]);

  useEffect(() => {
    api.score(original, species).then(setBaseline).catch(() => setBaseline(null));
  }, [original, species]);

  const valid = /^[ACDEFGHIKLMNPQRSTVWY]{5,}$/.test(seq);

  useEffect(() => {
    if (!valid) { setScore(null); setProps(null); setWheel(null); return; }
    let cancelled = false;
    setBusy(true); setErr(null);
    const t = setTimeout(() => {
      Promise.all([api.score(seq, species), api.properties(seq), api.wheel(seq)])
        .then(([s, p, w]) => { if (!cancelled) { setScore(s); setProps(p); setWheel(w); } })
        .catch((e) => !cancelled && setErr(e instanceof Error ? e.message : String(e)))
        .finally(() => !cancelled && setBusy(false));
    }, 250); // debounce so every keystroke does not hit the API
    return () => { cancelled = true; clearTimeout(t); };
  }, [seq, species, valid]);

  const rank = useMemo(() => {
    if (!score || !shortlist) return null;
    const better = shortlist.items.filter((i) => i.q_i > score.q).length;
    return { position: better + 1, of: shortlist.items.length };
  }, [score, shortlist]);

  const delta = score && baseline ? score.q - baseline.q : null;

  return (
    <>
      <h1 className="font-headline-lg text-headline-lg text-on-surface mb-1">What-if Lab</h1>
      <p className="font-body-md text-body-md text-on-surface-variant mb-lg max-w-3xl">
        Edit any residue and the peptide is re-embedded and re-scored live against{" "}
        <span className="italic">{species}</span>. Hypothetical sequences go through exactly
        the same model path as known ones.
      </p>

      <Card className="p-md mb-lg">
        <SectionTitle hint="Click a residue to cycle it, or type directly. Minimum 5 standard amino acids.">
          Sequence editor
        </SectionTitle>

        <div className="flex flex-wrap gap-1 mb-md">
          {seq.split("").map((residue, i) => (
            <select
              key={i}
              value={residue}
              onChange={(e) => setSeq(seq.slice(0, i) + e.target.value + seq.slice(i + 1))}
              className="mono font-code-md text-code-md w-9 h-9 text-center border border-outline-variant rounded bg-surface-container-lowest hover:border-primary cursor-pointer appearance-none"
              title={`Position ${i + 1}`}
            >
              {AA.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          ))}
        </div>

        <input
          value={seq}
          onChange={(e) => setSeq(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""))}
          className={`w-full mono font-code-md text-code-md px-3 py-2 border rounded bg-surface-container-lowest ${valid ? "border-outline-variant" : "border-error"}`}
          placeholder="Type or paste a peptide sequence"
          spellCheck={false}
        />
        <div className="flex items-center justify-between mt-2 gap-4 flex-wrap">
          <span className="font-body-sm text-body-sm text-on-surface-variant">
            {valid ? `${seq.length} residues` : "Needs at least 5 standard amino acids (ACDEFGHIKLMNPQRSTVWY)."}
          </span>
          {seq !== original && (
            <Button variant="text" onClick={() => setSeq(original)}>
              <Icon name="undo" size={16} /> Reset to original
            </Button>
          )}
        </div>
      </Card>

      {err && <div className="mb-lg"><ErrorNote>{err}</ErrorNote></div>}
      {busy && <div className="mb-lg"><Spinner label="Re-embedding and scoring…" /></div>}

      {score && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-md mb-lg">
            <Stat label="P(active)" value={pct(score.p_active)} tone="good" />
            <Stat label="P(toxic)" value={pct(score.p_toxic)} tone={score.p_toxic > 0.5 ? "bad" : "default"} />
            <Stat
              label="q_i"
              value={f3(score.q)}
              tone={delta == null ? "default" : delta > 0.001 ? "good" : delta < -0.001 ? "bad" : "default"}
              sub={delta == null ? undefined
                : `${delta >= 0 ? "+" : ""}${delta.toFixed(3)} vs original`}
            />
            <Stat
              label="Would rank"
              value={rank ? `#${rank.position}` : "—"}
              sub={rank ? `of ${rank.of} on the current shortlist` : "no shortlist loaded"}
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-lg">
            <Card className="p-md">
              <SectionTitle>Helical wheel</SectionTitle>
              {wheel && <div className="flex justify-center" dangerouslySetInnerHTML={{ __html: wheel }} />}
            </Card>
            {props && (
              <Card className="p-md">
                <SectionTitle>Properties</SectionTitle>
                <div className="grid grid-cols-2 gap-md">
                  {([
                    ["Net charge (pH 7)", props.net_charge_pH7.toFixed(2)],
                    ["Hydrophobic moment μH", f3(props.hydrophobic_moment_uH)],
                    ["Hydrophobic fraction", pct(props.hydrophobic_fraction)],
                    ["Cationic fraction", pct(props.cationic_fraction)],
                  ] as const).map(([l, v]) => (
                    <div key={l}>
                      <div className="font-label-bold text-label-bold text-on-surface-variant uppercase">{l}</div>
                      <div className="mono font-code-md text-code-md mt-0.5">{v}</div>
                    </div>
                  ))}
                </div>
                <div className="mt-md font-body-sm text-body-sm text-on-surface-variant">
                  Original: <Seq>{original}</Seq>
                  {score && !score.cached && (
                    <div className="mt-1 text-secondary">This sequence is not in the database — embedded live.</div>
                  )}
                </div>
              </Card>
            )}
          </div>
        </>
      )}
    </>
  );
}
