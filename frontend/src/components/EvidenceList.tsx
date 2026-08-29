/** Renders retrieved PubMed evidence.
 *
 *  Every row carries its PMID and a live link, so any claim on screen can be checked
 *  in one click. Empty and unavailable states are rendered honestly — an empty
 *  evidence pane is acceptable, an invented citation is not.
 */
import type { EvidenceResponse } from "../api";
import { Badge, Icon, Spinner } from "./ui";

export default function EvidenceList({ evidence }: { evidence: EvidenceResponse | null }) {
  if (!evidence) return <Spinner label="Searching PubMed…" />;

  if (evidence.status !== "success" || evidence.papers.length === 0) {
    return (
      <div className="border border-dashed border-outline-variant rounded-lg p-lg text-center">
        <Icon name="search_off" className="text-outline" />
        <div className="font-body-md text-body-md text-on-surface-variant mt-1">
          {evidence.status === "unavailable"
            ? "PubMed could not be reached."
            : "No published records matched this peptide or pathogen."}
        </div>
        {evidence.reason && (
          <div className="font-body-sm text-body-sm text-outline mt-1">{evidence.reason}</div>
        )}
      </div>
    );
  }

  return (
    <>
      <div className="mb-md">
        <Badge className={evidence.match_level === "peptide"
          ? "bg-secondary-container text-on-secondary-container"
          : "bg-primary-fixed text-on-primary-fixed-variant"}>
          {evidence.match_level === "peptide" ? "peptide-level match" : "pathogen-level match"}
        </Badge>
      </div>
      <ul className="space-y-md">
        {evidence.papers.map((p) => (
          <li key={p.pmid} className="border-l-2 border-outline-variant pl-md">
            <a href={p.url} target="_blank" rel="noreferrer"
               className="font-body-lg text-body-lg text-primary hover:underline inline-flex items-start gap-1">
              {p.title}
              <Icon name="open_in_new" size={14} className="mt-1 shrink-0" />
            </a>
            <div className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
              {p.journal && <span>{p.journal} · </span>}
              <span className="mono">PMID {p.pmid}</span>
            </div>
            {p.abstract_excerpt && (
              <p className="font-body-md text-body-md text-on-surface-variant mt-1 italic">
                “{p.abstract_excerpt}”
              </p>
            )}
          </li>
        ))}
      </ul>
      <p className="font-body-sm text-body-sm text-outline mt-md">
        Excerpts are quoted verbatim from the retrieved abstracts. Nothing on this pane is
        generated — if PubMed returns nothing, this pane stays empty.
      </p>
    </>
  );
}
