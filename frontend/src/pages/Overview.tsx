/** Landing screen. Every figure here is derived from a live endpoint or shown empty. */
import { Link } from "react-router-dom";
import { confidenceStyle } from "../api";
import { useStore } from "../store";
import { Badge, Button, Card, Icon, SectionTitle, Stat } from "../components/ui";

export default function Overview() {
  const { speciesList, pool, shortlist, species } = useStore();

  return (
    <>
      <div className="mb-lg">
        <h1 className="font-headline-lg text-headline-lg text-on-surface mb-2">
          An AI research assistant for antimicrobial drug discovery
        </h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant max-w-4xl">
          It ranks candidate compounds against drug-resistant pathogens, grounds every
          prediction in published evidence, surfaces similar known compounds, and lets
          researchers explore what-if hypotheses.
        </p>
      </div>

      <Card className="p-md mb-lg bg-surface-container-low">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-md font-body-md text-body-md">
          {([
            ["Disease", "Drug-resistant bacterial infection (AMR)"],
            ["Biological target", "WHO-priority pathogen"],
            ["Compound", "Antimicrobial peptide"],
          ] as const).map(([k, v]) => (
            <div key={k}>
              <div className="font-label-bold text-label-bold text-on-surface-variant uppercase">{k}</div>
              <div className="text-on-surface mt-0.5">{v}</div>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-md mb-lg">
        <Stat label="Candidate pool" value={pool.length.toLocaleString()} sub="peptides loaded" />
        <Stat label="Trained targets" value={speciesList.length} sub="WHO-priority pathogens" />
        <Stat label="Current shortlist" value={shortlist?.items.length ?? "—"} sub={shortlist ? `for ${species}` : "not generated yet"} />
        <Stat label="Objective" value={shortlist ? shortlist.logdet.toFixed(2) : "—"} sub="log det(L + I)" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-lg mb-lg">
        <Card className="p-md">
          <SectionTitle hint="Quality times diversity, maximised greedily under a fixed testing budget.">
            How the ranking works
          </SectionTitle>
          <div className="bg-surface-container rounded p-md mono font-code-md text-code-md text-on-surface overflow-x-auto">
            log det(L<sub>A</sub>) = 2 · Σ log(q<sub>i</sub>) + log det(S<sub>A</sub>)
          </div>
          <p className="font-body-md text-body-md text-on-surface-variant mt-md">
            q<sub>i</sub> = P(active) × (1 − P(toxic)) — a peptide scores well only if it is
            both likely to work and unlikely to harm human cells. The second term collapses
            toward −∞ for redundant sets, so near-duplicates stop earning budget. Greedy
            selection is near-optimal (1 − 1/e) with respect to this log-determinant
            objective — not with respect to raw diversity.
          </p>
          <div className="mt-md">
            <Link to="/shortlist"><Button>Build a shortlist <Icon name="arrow_forward" size={18} /></Button></Link>
          </div>
        </Card>

        <Card className="p-md">
          <SectionTitle hint="Cross-validated on sequence-level splits. Weak models are labelled.">
            Trained targets
          </SectionTitle>
          <ul className="space-y-2">
            {speciesList.map((s) => (
              <li key={s.name} className="flex items-center justify-between gap-2 border-b border-outline-variant last:border-0 pb-2 last:pb-0">
                <span className="font-body-md text-body-md italic">{s.name}</span>
                <span className="flex items-center gap-2 shrink-0">
                  <span className="mono font-code-md text-code-md text-on-surface-variant">
                    {s.cv_roc_auc.toFixed(3)}
                  </span>
                  <Badge className={confidenceStyle[s.confidence]}>{s.confidence}</Badge>
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-md">
            <Link to="/validation"><Button variant="outlined">See validation <Icon name="arrow_forward" size={18} /></Button></Link>
          </div>
        </Card>
      </div>

    </>
  );
}
