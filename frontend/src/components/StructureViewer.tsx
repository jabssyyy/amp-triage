/** 3D structure viewer.
 *
 *  Honesty rules baked in, straight from the project's research notes:
 *   - the tier badge is always visible, never buried;
 *   - predicted structures are coloured BY pLDDT confidence, so low-confidence
 *     regions are visibly washed out rather than rendered as if they were certain;
 *   - a disordered result is reported as a finding, not hidden. AlphaFold-class
 *     models are unreliable on short peptides and many AMPs are disordered in water
 *     until they contact a membrane.
 */
import { useEffect, useRef, useState } from "react";
import { api, type Structure } from "../api";
import { Icon, Spinner, TierBadge } from "./ui";

declare global {
  interface Window { $3Dmol?: any }
}

/** The ESM Atlas API returns pLDDT in the B-factor column on a 0-1 scale, while the
 *  conventional AlphaFold/ESMFold reporting scale is 0-100. Normalise to 0-100 so the
 *  confidence thresholds mean what everyone expects. Tolerates either input scale in
 *  case the upstream API changes. */
const to100 = (v: number) => (v <= 1.0 ? v * 100 : v);

export default function StructureViewer({ sequence, height = 320 }: {
  sequence: string; height?: number;
}) {
  const host = useRef<HTMLDivElement>(null);
  const [struct, setStruct] = useState<Structure | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);
    setStruct(null);
    api.structure(sequence)
      .then((s) => { if (!cancelled) setStruct(s); })
      .catch((e) => { if (!cancelled) setErr(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [sequence]);

  useEffect(() => {
    if (!struct?.pdb_text || !host.current || !window.$3Dmol) return;
    host.current.innerHTML = "";
    const viewer = window.$3Dmol.createViewer(host.current, { backgroundColor: "#ffffff" });
    viewer.addModel(struct.pdb_text, "pdb");

    if (struct.tier === "predicted") {
      // Colour by pLDDT so confidence is impossible to miss.
      viewer.setStyle({}, {
        cartoon: {
          colorfunc: (atom: any) => {
            const b = to100(atom.b ?? 0);
            if (b >= 90) return "#0053b3";  // very high
            if (b >= 70) return "#4bddb7";  // confident
            if (b >= 50) return "#e08700";  // low
            return "#ba1a1a";               // very low
          },
        },
      });
    } else {
      viewer.setStyle({}, { cartoon: { color: "#005ea5" } });
    }
    // Short peptides have few atoms, so the default framing leaves them tiny. Add
    // sticks for body and resize once the card has its final width.
    viewer.addStyle({}, { stick: { radius: 0.18 } });
    viewer.resize();
    viewer.zoomTo();
    viewer.render();
    viewer.zoom(1.6);
    viewer.render();

    const onResize = () => { viewer.resize(); viewer.render(); };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [struct]);

  if (loading) return <div className="p-md"><Spinner label="Resolving structure…" /></div>;
  if (err) return <div className="p-md font-body-sm text-body-sm text-on-surface-variant">Structure lookup failed: {err}</div>;
  if (!struct) return null;

  const plddt = struct.mean_plddt != null ? to100(struct.mean_plddt) : null;
  const lowConfidence = struct.tier === "predicted" && plddt != null && plddt < 70;

  return (
    <div>
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <TierBadge tier={struct.tier} />
        <div className="font-body-sm text-body-sm text-on-surface-variant">
          {struct.pdb_id && <span className="mono">PDB {struct.pdb_id}</span>}
          {plddt != null && <span className="mono">mean pLDDT {plddt.toFixed(0)}/100</span>}
        </div>
      </div>

      {struct.tier === "unavailable" ? (
        <div className="border border-dashed border-outline-variant rounded-lg p-lg text-center">
          <Icon name="help_center" className="text-outline" />
          <div className="font-body-md text-body-md text-on-surface-variant mt-1">
            No structure available for this peptide.
          </div>
        </div>
      ) : (
        <>
          <div ref={host} style={{ height, position: "relative" }}
               className="border border-outline-variant rounded-lg overflow-hidden bg-white" />
          <div className="font-body-sm text-body-sm text-on-surface-variant mt-2">
            {struct.tier === "experimental"
              ? "Experimentally determined structure retrieved from the PDB. This is measured data, not a prediction."
              : "Predicted by ESMFold and coloured by per-residue pLDDT — blue is very high, green confident, amber low, red very low."}
          </div>
          {lowConfidence && (
            <div className="mt-2 bg-error-container text-on-error-container rounded-lg p-3 font-body-sm text-body-sm">
              <strong>Low confidence overall (mean pLDDT {plddt?.toFixed(0)}/100).</strong> Treat this
              as an illustration, not a structure. Many antimicrobial peptides are genuinely
              disordered in water and only fold on membrane contact, so a low score here is
              often a real property of the peptide rather than a failure of the model.
            </div>
          )}
        </>
      )}
    </div>
  );
}
