/** Candidate detail: score, properties, helical wheel, 3D structure, evidence. */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, f2, f3, pct, type EvidenceResponse, type Properties, type ScoreResponse } from "../api";
import { useStore } from "../store";
import { Button, Card, ErrorNote, Icon, Placeholder, SectionTitle, Seq, Spinner, Stat } from "../components/ui";
import StructureViewer from "../components/StructureViewer";
import EvidenceList from "../components/EvidenceList";
import ExperimentPanel from "../components/ExperimentPanel";

export default function Candidate() {
  const { focus, species, tray, toggleTray, shortlist, setFocus } = useStore();
  const navigate = useNavigate();
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [props, setProps] = useState<Properties | null>(null);
  const [wheel, setWheel] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<EvidenceResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const seq = focus ?? shortlist?.items[0]?.sequence ?? null;

  useEffect(() => {
    if (!seq) return;
    let cancelled = false;
    setBusy(true); setErr(null);
    setScore(null); setProps(null); setWheel(null); setEvidence(null);
    Promise.all([
      api.score(seq, species),
      api.properties(seq),
      api.wheel(seq),
    ]).then(([s, p, w]) => {
      if (cancelled) return;
      setScore(s); setProps(p); setWheel(w);
    }).catch((e) => !cancelled && setErr(e instanceof Error ? e.message : String(e)))
      .finally(() => !cancelled && setBusy(false));

    api.evidence(seq, species)
      .then((e) => !cancelled && setEvidence(e))
      .catch(() => !cancelled && setEvidence({ status: "unavailable", match_level: null, papers: [], reason: "Evidence service unreachable." }));

    return () => { cancelled = true; };
  }, [seq, species]);

  if (!seq) {
    return <Placeholder what="No candidate selected. Open one from the Shortlist." />;
  }

  return (
    <>
      <div className="mb-lg flex flex-wrap justify-between items-start gap-4">
        <div className="min-w-0">
          <h1 className="font-headline-lg text-headline-lg text-on-surface mb-1">Candidate</h1>
          <Seq className="text-on-surface-variant">{seq}</Seq>
          <div className="font-body-sm text-body-sm text-on-surface-variant mt-1">
            scored against <span className="italic">{species}</span>
            {score && (score.cached
              ? " · embedding from cache"
              : " · embedded live (novel sequence)")}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outlined" onClick={() => toggleTray(seq)}>
            <Icon name="compare_arrows" size={18} fill={tray.includes(seq)} />
            {tray.includes(seq) ? "In compare tray" : "Add to compare"}
          </Button>
          <Button variant="outlined" onClick={() => { setFocus(seq); navigate("/whatif"); }}>
            <Icon name="biotech" size={18} /> Edit in What-if Lab
          </Button>
        </div>
      </div>

      {err && <div className="mb-lg"><ErrorNote>{err}</ErrorNote></div>}
      {busy && <div className="mb-lg"><Spinner label="Scoring candidate…" /></div>}

      {score && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-md mb-lg">
          <Stat label="P(active)" value={pct(score.p_active)} tone="good" sub="predicted activity" />
          <Stat label="P(toxic)" value={pct(score.p_toxic)} tone={score.p_toxic > 0.5 ? "bad" : "default"} sub="human erythrocyte lysis" />
          <Stat label="q_i" value={f3(score.q)} sub="P(active) × (1 − P(toxic))" />
          {props && <Stat label="Net charge (pH 7)" value={props.net_charge_pH7 > 0 ? `+${f2(props.net_charge_pH7)}` : f2(props.net_charge_pH7)} sub={`pI ≈ ${f2(props.isoelectric_point)}`} />}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-lg mb-lg">
        <Card className="p-md">
          <SectionTitle hint="Deterministic geometry from the sequence — no prediction, no uncertainty. The arrow is the hydrophobic moment.">
            Helical wheel
          </SectionTitle>
          {wheel
            ? <div className="flex justify-center" dangerouslySetInnerHTML={{ __html: wheel }} />
            : <Spinner label="Drawing wheel…" />}
        </Card>

        <Card className="p-md">
          <SectionTitle hint="Experimental structures come from the PDB. Predictions are shown with their confidence.">
            3D structure
          </SectionTitle>
          <StructureViewer sequence={seq} />
        </Card>
      </div>

      {props && (
        <Card className="p-md mb-lg">
          <SectionTitle>Physicochemical properties</SectionTitle>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-md">
            {([
              ["Length", `${props.length} aa`],
              ["Hydrophobic moment μH", f3(props.hydrophobic_moment_uH)],
              ["Mean hydrophobicity", f3(props.mean_hydrophobicity)],
              ["Hydrophobic fraction", pct(props.hydrophobic_fraction)],
              ["Cationic fraction", pct(props.cationic_fraction)],
              ["Anionic fraction", pct(props.anionic_fraction)],
              ["Polar fraction", pct(props.polar_fraction)],
              ["Isoelectric point", f2(props.isoelectric_point)],
            ] as const).map(([label, value]) => (
              <div key={label}>
                <div className="font-label-bold text-label-bold text-on-surface-variant uppercase">{label}</div>
                <div className="mono font-code-md text-code-md text-on-surface mt-0.5">{value}</div>
              </div>
            ))}
          </div>
          <div className="mt-md">
            <div className="font-label-bold text-label-bold text-on-surface-variant uppercase mb-1">Composition</div>
            <div className="flex flex-wrap gap-1">
              {Object.entries(props.composition).sort((a, b) => b[1] - a[1]).map(([aa, n]) => (
                <span key={aa} className="mono font-code-md text-code-md bg-surface-container px-2 py-0.5 rounded border border-outline-variant">
                  {aa}<span className="text-on-surface-variant"> ×{n}</span>
                </span>
              ))}
            </div>
          </div>
        </Card>
      )}

      <div className="mb-lg">
        <ExperimentPanel sequence={seq} />
      </div>

      <Card className="p-md">
        <SectionTitle hint="Retrieved live from PubMed. Research-support only — this tool does not make clinical decisions.">
          Published evidence
        </SectionTitle>
        <EvidenceList evidence={evidence} />
      </Card>
    </>
  );
}
