/** Relationship graph: compound / pathogen / mechanism / supporting paper.
 *
 *  Explainability surface, not the engine. Nodes and edges come from the API; only the
 *  layout is computed here.
 *
 *  Paper nodes link straight out to PubMed. A citation you cannot click is a citation
 *  nobody can check, and every claim on this screen has to be checkable in one hop.
 */
import { useEffect, useMemo, useState } from "react";
import { api, type GraphNode, type GraphResponse } from "../api";
import { useStore } from "../store";
import { Card, ErrorNote, Icon, Placeholder, SectionTitle, Seq, Spinner } from "../components/ui";

const STYLE: Record<string, { fill: string; stroke: string; text: string }> = {
  compound: { fill: "#005ea5", stroke: "#003d6b", text: "#ffffff" },
  pathogen: { fill: "#ba1a1a", stroke: "#93000a", text: "#ffffff" },
  mechanism: { fill: "#6dfad2", stroke: "#00725b", text: "#00332a" },
  paper: { fill: "#ffffff", stroke: "#8d94a3", text: "#161d1f" },
};

const NODE_W = 210;
const NODE_H = 44;
const W = 1000;
const H = 620;

/** Pull the PMID out of a node so the box can link to the real paper. */
function pmidOf(node: GraphNode): string | null {
  const fromProps = (node.properties as Record<string, unknown> | undefined)?.pmid;
  if (typeof fromProps === "string" && /^\d+$/.test(fromProps)) return fromProps;
  const m = /PMID[:\s]*(\d+)/i.exec(node.label);
  return m ? m[1] : null;
}

/** Strip the PMID prefix so the box shows the journal / title, not a duplicated id. */
function displayLabel(node: GraphNode): string {
  const cleaned = node.label.replace(/^PMID[:\s]*\d+\s*/i, "").replace(/^\((.*)\)$/, "$1");
  return cleaned.trim() || node.label;
}

function wrap(text: string, max = 26, lines = 2): string[] {
  const words = text.split(/\s+/);
  const out: string[] = [];
  let cur = "";
  for (const w of words) {
    if ((cur + " " + w).trim().length <= max) cur = (cur + " " + w).trim();
    else { if (cur) out.push(cur); cur = w; }
    if (out.length === lines) break;
  }
  if (cur && out.length < lines) out.push(cur);
  if (out.length === lines) {
    const joined = out.join(" ");
    if (joined.length < text.length) out[lines - 1] = out[lines - 1].replace(/.{1}$/, "…");
  }
  return out.length ? out : [text.slice(0, max)];
}

export default function Graph() {
  const { focus, species, shortlist } = useStore();
  const seq = focus ?? shortlist?.items[0]?.sequence ?? null;
  const [data, setData] = useState<GraphResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);

  useEffect(() => {
    if (!seq) return;
    let cancelled = false;
    setData(null); setErr(null);
    api.graph(seq, species)
      .then((g) => !cancelled && setData(g))
      .catch((e) => !cancelled && setErr(e instanceof Error ? e.message : String(e)));
    return () => { cancelled = true; };
  }, [seq, species]);

  /** Columned layout: pathogen and mechanisms above, compound centred, papers on a row
   *  below. Everything sits on a grid, so boxes cannot land on top of edge labels. */
  const layout = useMemo(() => {
    if (!data) return null;
    const pos: Record<string, { x: number; y: number }> = {};
    const compound = data.nodes.find((n) => n.type === "compound");
    const pathogen = data.nodes.find((n) => n.type === "pathogen");
    const mechanisms = data.nodes.filter((n) => n.type === "mechanism");
    const papers = data.nodes.filter((n) => !["compound", "pathogen", "mechanism"].includes(n.type));

    const midY = 300;
    if (compound) pos[compound.id] = { x: W / 2, y: midY };
    if (pathogen) pos[pathogen.id] = { x: W / 2, y: 70 };

    mechanisms.forEach((m, i) => {
      const spread = (mechanisms.length - 1) / 2;
      pos[m.id] = { x: W / 2 + (i - spread) * (NODE_W + 40), y: 175 };
    });

    papers.forEach((p, i) => {
      const perRow = Math.min(papers.length, 3);
      const row = Math.floor(i / perRow);
      const col = i % perRow;
      const spread = (perRow - 1) / 2;
      pos[p.id] = { x: W / 2 + (col - spread) * (NODE_W + 40), y: 450 + row * (NODE_H + 46) };
    });

    return pos;
  }, [data]);

  if (!seq) return <Placeholder what="No candidate selected. Open one from the Shortlist first." />;

  return (
    <>
      <h1 className="font-headline-lg text-headline-lg text-on-surface mb-1">Relationship Graph</h1>
      <p className="font-body-md text-body-md text-on-surface-variant mb-lg">
        <Seq>{seq}</Seq> against <span className="italic">{species}</span>
      </p>

      {err && <div className="mb-lg"><ErrorNote>{err}</ErrorNote></div>}
      {!data && !err && <Spinner label="Building relationship graph…" />}

      {data && layout && (
        <Card className="p-md">
          <SectionTitle hint="Derived from the retrieved literature. Click any paper to open it on PubMed.">
            Compound · pathogen · mechanism · source
          </SectionTitle>
          <div className="overflow-x-auto">
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 760 }}>
              {/* edges first so nodes always sit on top of them */}
              {data.edges.map((e, i) => {
                const a = layout[e.source], b = layout[e.target];
                if (!a || !b) return null;
                const midX = (a.x + b.x) / 2;
                const midY = (a.y + b.y) / 2;
                const label = e.label ?? e.relation;
                // offset the label along the edge so it clears both boxes
                const dx = b.x - a.x, dy = b.y - a.y;
                const len = Math.hypot(dx, dy) || 1;
                const off = Math.min(len / 2 - NODE_H, 46);
                const lx = midX - (dx / len) * 0 + (Math.abs(dy) > Math.abs(dx) ? 8 : 0);
                const ly = midY - (Math.abs(dy) > Math.abs(dx) ? 0 : off * 0) - 6;
                return (
                  <g key={i}>
                    <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#d3d9e2" strokeWidth={1.5} />
                    <text x={lx} y={ly} textAnchor="middle" fontSize={10} fill="#8d94a3"
                          fontFamily="Inter" style={{ paintOrder: "stroke" }}
                          stroke="#ffffff" strokeWidth={4} strokeLinejoin="round">
                      {label}
                    </text>
                    <text x={lx} y={ly} textAnchor="middle" fontSize={10} fill="#707784" fontFamily="Inter">
                      {label}
                    </text>
                  </g>
                );
              })}

              {data.nodes.map((n) => {
                const p = layout[n.id];
                if (!p) return null;
                const st = STYLE[n.type] ?? STYLE.paper;
                const pmid = pmidOf(n);
                const lines = wrap(displayLabel(n), n.type === "paper" || pmid ? 26 : 30, 2);
                const h = lines.length > 1 ? NODE_H + 12 : NODE_H;
                const isHover = hover === n.id;

                const box = (
                  <g
                    onMouseEnter={() => setHover(n.id)}
                    onMouseLeave={() => setHover(null)}
                    style={{ cursor: pmid ? "pointer" : "default" }}
                  >
                    <rect
                      x={p.x - NODE_W / 2} y={p.y - h / 2} width={NODE_W} height={h} rx={6}
                      fill={st.fill} stroke={isHover && pmid ? "#005ea5" : st.stroke}
                      strokeWidth={isHover && pmid ? 2 : 1.4}
                    />
                    {lines.map((ln, li) => (
                      <text
                        key={li}
                        x={p.x}
                        y={p.y - (lines.length - 1) * 7 + li * 14 + (pmid ? -4 : 4)}
                        textAnchor="middle" fontSize={11} fontWeight={600}
                        fill={st.text} fontFamily="Inter"
                      >
                        {ln}
                      </text>
                    ))}
                    {pmid && (
                      <text x={p.x} y={p.y + h / 2 - 8} textAnchor="middle" fontSize={9}
                            fill="#005ea5" fontFamily="Inter" style={{ textDecoration: "underline" }}>
                        PMID {pmid} ↗
                      </text>
                    )}
                  </g>
                );

                return pmid ? (
                  <a key={n.id} href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}/`}
                     target="_blank" rel="noreferrer">
                    {box}
                  </a>
                ) : (
                  <g key={n.id}>{box}</g>
                );
              })}
            </svg>
          </div>

          <div className="flex flex-wrap items-center gap-lg mt-md">
            {Object.entries(STYLE).map(([type, st]) => (
              <span key={type} className="flex items-center gap-1.5 font-body-sm text-body-sm text-on-surface-variant">
                <span className="w-3 h-3 rounded-sm border" style={{ background: st.fill, borderColor: st.stroke }} />
                {type}
              </span>
            ))}
            <span className="flex items-center gap-1 font-body-sm text-body-sm text-outline ml-auto">
              <Icon name="open_in_new" size={14} /> paper nodes open on PubMed
            </span>
          </div>
        </Card>
      )}
    </>
  );
}
