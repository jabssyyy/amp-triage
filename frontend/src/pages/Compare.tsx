/** Side-by-side comparison of two candidates.
 *
 *  The embedding distance shown here is the exact number the selector used to decide
 *  these two peptides were different — it is the answer to "why both, and not two
 *  copies of the better one". RMSD appears only when BOTH structures are experimental;
 *  comparing predicted short-peptide structures is noise and the API refuses it.
 */
import { useEffect, useState } from "react";
import { api, f2, f3, pct, type CompareResponse } from "../api";
import { useStore } from "../store";
import { Button, Card, ErrorNote, Icon, Placeholder, SectionTitle, Seq, Spinner, Stat } from "../components/ui";
import StructureViewer from "../components/StructureViewer";

export default function Compare() {
  const { tray, clearTray, species } = useStore();
  const [data, setData] = useState<CompareResponse | null>(null);
  const [rmsd, setRmsd] = useState<{ rmsd: number | null; reason?: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (tray.length !== 2) { setData(null); return; }
    let cancelled = false;
    setErr(null); setData(null); setRmsd(null);
    api.compare(tray, species)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setErr(e instanceof Error ? e.message : String(e)));
    api.structureCompare(tray)
      .then((r) => !cancelled && setRmsd(r))
      .catch(() => !cancelled && setRmsd({ rmsd: null, reason: "Structure comparison unavailable." }));
    return () => { cancelled = true; };
  }, [tray, species]);

  if (tray.length !== 2) {
    return (
      <Placeholder what={`Select two candidates to compare — ${tray.length} of 2 staged. Use the compare icon on the Shortlist.`} />
    );
  }

  const rows: Array<[string, (p: CompareResponse["properties"][number]) => string]> = [
    ["Length", (p) => `${p.length} aa`],
    ["Net charge (pH 7)", (p) => (p.net_charge_pH7 > 0 ? `+${f2(p.net_charge_pH7)}` : f2(p.net_charge_pH7))],
    ["Isoelectric point", (p) => f2(p.isoelectric_point)],
    ["Hydrophobic moment μH", (p) => f3(p.hydrophobic_moment_uH)],
    ["Mean hydrophobicity", (p) => f3(p.mean_hydrophobicity)],
    ["Hydrophobic fraction", (p) => pct(p.hydrophobic_fraction)],
    ["Cationic fraction", (p) => pct(p.cationic_fraction)],
  ];

  return (
    <>
      <div className="flex justify-between items-start mb-lg gap-4 flex-wrap">
        <div>
          <h1 className="font-headline-lg text-headline-lg text-on-surface mb-1">Compare candidates</h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Against <span className="italic">{species}</span>
          </p>
        </div>
        <Button variant="outlined" onClick={clearTray}>
          <Icon name="close" size={18} /> Clear tray
        </Button>
      </div>

      {err && <div className="mb-lg"><ErrorNote>{err}</ErrorNote></div>}
      {!data && !err && <Spinner label="Comparing…" />}

      {data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-md mb-lg">
            <Stat label="Embedding distance" value={f3(data.embedding_distance)}
                  sub="the number the selector used" tone="good" />
            <Stat label="Cosine similarity" value={f3(data.cosine_similarity)}
                  sub="1.0 would be identical" />
            <Stat label="Structural RMSD"
                  value={rmsd?.rmsd != null ? `${f2(rmsd.rmsd)} Å` : "—"}
                  sub={rmsd?.rmsd != null ? "both structures experimental" : "requires two experimental structures"} />
          </div>

          {rmsd && rmsd.rmsd == null && rmsd.reason && (
            <Card className="p-md mb-lg bg-surface-container-low">
              <div className="font-body-md text-body-md text-on-surface-variant">
                <strong>RMSD withheld.</strong> {rmsd.reason} Comparing predicted structures of
                short peptides produces numbers that look precise and mean nothing, so the
                comparison falls back to the defensible axes below: hydrophobic moment, charge,
                the wheels, and the embedding distance.
              </div>
            </Card>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-lg mb-lg">
            {data.sequences.map((seq, i) => (
              <Card key={seq} className="p-md">
                <div className="font-label-bold text-label-bold text-on-surface-variant uppercase mb-1">
                  Candidate {i + 1}
                </div>
                <Seq className="text-on-surface">{seq}</Seq>
                <div className="mt-md flex justify-center"
                     dangerouslySetInnerHTML={{ __html: data.wheel_svgs[i] }} />
                <div className="mt-md">
                  <StructureViewer sequence={seq} height={240} />
                </div>
              </Card>
            ))}
          </div>

          <SectionTitle>Property comparison</SectionTitle>
          <Card className="overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-surface-container-low border-b border-outline-variant">
                <tr className="font-label-bold text-label-bold text-on-surface-variant uppercase">
                  <th className="px-3 py-2">Property</th>
                  <th className="px-3 py-2">Candidate 1</th>
                  <th className="px-3 py-2">Candidate 2</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(([label, get]) => {
                  const a = get(data.properties[0]);
                  const b = get(data.properties[1]);
                  return (
                    <tr key={label} className="border-b border-outline-variant last:border-0">
                      <td className="px-3 py-2 font-body-md text-body-md text-on-surface-variant">{label}</td>
                      <td className={`px-3 py-2 mono font-code-md text-code-md ${a !== b ? "font-medium text-primary" : ""}`}>{a}</td>
                      <td className={`px-3 py-2 mono font-code-md text-code-md ${a !== b ? "font-medium text-primary" : ""}`}>{b}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </>
  );
}
