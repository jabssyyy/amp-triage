/** Standalone evidence browser for the focused candidate. */
import { useEffect, useState } from "react";
import { api, type EvidenceResponse } from "../api";
import { useStore } from "../store";
import { Card, Placeholder, SectionTitle, Seq } from "../components/ui";
import EvidenceList from "../components/EvidenceList";

export default function Evidence() {
  const { focus, species, shortlist } = useStore();
  const seq = focus ?? shortlist?.items[0]?.sequence ?? null;
  const [evidence, setEvidence] = useState<EvidenceResponse | null>(null);

  useEffect(() => {
    if (!seq) return;
    let cancelled = false;
    setEvidence(null);
    api.evidence(seq, species)
      .then((e) => !cancelled && setEvidence(e))
      .catch(() => !cancelled && setEvidence({
        status: "unavailable", match_level: null, papers: [],
        reason: "Evidence service unreachable.",
      }));
    return () => { cancelled = true; };
  }, [seq, species]);

  if (!seq) return <Placeholder what="No candidate selected. Open one from the Shortlist first." />;

  return (
    <>
      <h1 className="font-headline-lg text-headline-lg text-on-surface mb-1">Scientific Evidence</h1>
      <p className="font-body-md text-body-md text-on-surface-variant mb-lg">
        Live PubMed retrieval for <Seq>{seq}</Seq> against <span className="italic">{species}</span>.
      </p>
      <Card className="p-md">
        <SectionTitle hint="A research-support surface. It grounds predictions in published work; it does not make decisions.">
          Retrieved literature
        </SectionTitle>
        <EvidenceList evidence={evidence} />
      </Card>
    </>
  );
}
