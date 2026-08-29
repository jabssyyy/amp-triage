import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Badge, Button, Card, ErrorNote, Icon, SectionTitle } from "../components/ui";
import { useStore } from "../store";

const SPECIES_OPTIONS = [
  "Escherichia coli",
  "Pseudomonas aeruginosa",
  "Staphylococcus aureus",
  "Klebsiella pneumoniae",
  "Acinetobacter baumannii",
];

export default function Projects() {
  const {
    user,
    activeProject,
    setActiveProject,
    projects,
    myProjects,
    refreshProjects,
  } = useStore();

  const [tab, setTab] = useState<"all" | "mine">("mine");
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [targetSpecies, setTargetSpecies] = useState("Escherichia coli");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user) {
    return (
      <div className="max-w-2xl mx-auto space-y-md py-md text-center">
        <Card className="p-xl space-y-md">
          <div className="w-12 h-12 mx-auto rounded-full bg-primary/10 text-primary flex items-center justify-center">
            <Icon name="lock" size={28} />
          </div>
          <h2 className="font-headline-sm text-headline-sm text-on-surface">Authentication Required</h2>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-md mx-auto">
            Campaign projects and institutional memory require a signed-in scientist profile.
          </p>
          <div className="pt-2">
            <Link to="/login">
              <Button variant="filled">
                <Icon name="login" size={18} />
                Sign In to View Projects
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreating(true);

    try {
      const proj = await api.projects.create({
        name: name.trim(),
        target_species: targetSpecies,
        status: "active",
      });
      await refreshProjects();
      setActiveProject(proj);
      setName("");
      setShowCreate(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (projId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this campaign project?")) return;
    try {
      await api.projects.delete(projId);
      if (activeProject?.id === projId) {
        setActiveProject(null);
      }
      await refreshProjects();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : String(err));
    }
  };

  const displayedList = tab === "mine" ? myProjects : projects;

  return (
    <div className="max-w-5xl mx-auto space-y-lg py-md">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-md">
        <div>
          <SectionTitle hint="Campaign workspaces isolating candidate batches by pathogen">
            Campaign Projects
          </SectionTitle>
        </div>
        <Button variant="filled" onClick={() => setShowCreate(!showCreate)}>
          <Icon name={showCreate ? "close" : "add"} size={18} />
          {showCreate ? "Cancel" : "New Campaign"}
        </Button>
      </div>

      {error && <ErrorNote>{error}</ErrorNote>}

      {/* Create Project Modal / Form */}
      {showCreate && (
        <Card className="p-lg bg-surface-container-low border-primary/30">
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-md">
            Start New Discovery Campaign
          </h3>
          <form onSubmit={handleCreate} className="space-y-md">
            <div>
              <label className="block font-label-bold text-label-bold text-on-surface-variant uppercase mb-1">
                Project Name
              </label>
              <input
                type="text"
                required
                placeholder="e.g. K. pneumoniae Beta-Lactam Synergist Search"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 rounded bg-surface-container-lowest border border-outline-variant font-body-md text-on-surface focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label className="block font-label-bold text-label-bold text-on-surface-variant uppercase mb-1">
                Target Pathogen (Exactly One)
              </label>
              <select
                value={targetSpecies}
                onChange={(e) => setTargetSpecies(e.target.value)}
                className="w-full px-3 py-2 rounded bg-surface-container-lowest border border-outline-variant font-body-md text-on-surface focus:outline-none focus:border-primary"
              >
                {SPECIES_OPTIONS.map((sp) => (
                  <option key={sp} value={sp}>
                    {sp}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-end gap-md pt-2">
              <Button variant="outlined" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
              <Button variant="filled" disabled={creating}>
                {creating ? "Creating…" : "Create Project"}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Tabs */}
      <div className="flex border-b border-outline-variant">
        <button
          type="button"
          onClick={() => setTab("mine")}
          className={`pb-2 px-4 font-label-bold text-label-bold flex items-center gap-2 transition-colors ${
            tab === "mine"
              ? "border-b-2 border-primary text-primary"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <Icon name="person" size={16} />
          My Campaigns ({myProjects.length})
        </button>
        <button
          type="button"
          onClick={() => setTab("all")}
          className={`pb-2 px-4 font-label-bold text-label-bold flex items-center gap-2 transition-colors ${
            tab === "all"
              ? "border-b-2 border-primary text-primary"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <Icon name="domain" size={16} />
          Lab Workspace ({projects.length})
        </button>
      </div>

      {/* Projects Grid */}
      {displayedList.length === 0 ? (
        <Card className="p-xl text-center text-on-surface-variant">
          <Icon name="folder_off" className="text-outline text-4xl mb-2" />
          <div className="font-headline-sm text-headline-sm text-on-surface">No Campaigns Found</div>
          <p className="font-body-sm text-body-sm text-outline mt-1">
            {tab === "mine"
              ? "You are not currently assigned to any campaigns. Create one above or check the Lab Workspace tab."
              : "No campaigns registered in this research unit yet."}
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-md">
          {displayedList.map((proj) => {
            const isActive = activeProject?.id === proj.id;
            const canDelete = user.role === "lead" || proj.created_by === user.id;

            return (
              <div
                key={proj.id}
                className={`bg-surface-container-lowest border border-outline-variant rounded-lg p-md flex flex-col justify-between cursor-pointer transition-all hover:border-primary ${
                  isActive
                    ? "border-2 border-primary bg-surface-container-high"
                    : "bg-surface-container-lowest"
                }`}
                onClick={() => setActiveProject(isActive ? null : proj)}
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="font-headline-sm text-headline-sm text-on-surface leading-tight">
                      {proj.name}
                    </span>
                    {proj.is_seeded && (
                      <Badge className="bg-primary-fixed text-on-primary-fixed-variant text-[10px]">
                        Seeded
                      </Badge>
                    )}
                  </div>

                  <div className="flex items-center gap-2 mb-3">
                    <Icon name="target" size={16} className="text-primary" />
                    <span className="font-label-bold text-label-bold text-primary">
                      {proj.target_species}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-on-surface-variant text-body-sm mb-3">
                    <div>
                      <span className="text-outline text-[11px] block uppercase">Runs</span>
                      <span className="font-headline-sm text-on-surface">{proj.n_runs}</span>
                    </div>
                    <div>
                      <span className="text-outline text-[11px] block uppercase">Members</span>
                      <span className="font-headline-sm text-on-surface">{proj.n_members}</span>
                    </div>
                  </div>
                </div>

                <div className="border-t border-outline-variant pt-3 flex items-center justify-between">
                  <span
                    className={`font-label-bold text-label-bold text-xs ${
                      isActive ? "text-primary font-bold" : "text-on-surface-variant"
                    }`}
                  >
                    {isActive ? "✓ Active Campaign" : "Click to Activate"}
                  </span>

                  {canDelete && (
                    <button
                      type="button"
                      onClick={(e) => handleDelete(proj.id, e)}
                      title="Delete Campaign"
                      className="text-outline hover:text-error p-1 rounded transition-colors"
                    >
                      <Icon name="delete" size={18} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
