/** Navigation drawer + top app bar + main canvas, matching the Stitch template shell. */
import { Link, NavLink, useLocation } from "react-router-dom";
import { useStore } from "../store";
import { Badge, Icon } from "./ui";

const NAV = [
  { to: "/", icon: "dashboard", label: "Overview" },
  { to: "/projects", icon: "folder", label: "Campaigns" },
  { to: "/shortlist", icon: "star", label: "Shortlist" },
  { to: "/history", icon: "history", label: "Run History" },
  { to: "/candidate", icon: "search_check", label: "Candidate" },
  { to: "/compare", icon: "compare_arrows", label: "Compare" },
  { to: "/whatif", icon: "biotech", label: "What-if Lab" },
  { to: "/evidence", icon: "menu_book", label: "Evidence" },
  { to: "/graph", icon: "hub", label: "Relationships" },
  { to: "/analytics", icon: "analytics", label: "Calibration & Trends" },
  { to: "/validation", icon: "verified", label: "Model & Validation" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const {
    species,
    setSpecies,
    speciesList,
    tray,
    user,
    activeProject,
    setActiveProject,
    projects,
  } = useStore();
  const { pathname } = useLocation();
  const title = NAV.find((n) => n.to === pathname)?.label ?? "PharmaMind";

  return (
    <div className="h-screen overflow-hidden flex bg-surface text-on-surface">
      <nav className="hidden md:flex fixed left-0 top-0 h-screen flex-col justify-between py-md w-64 border-r border-outline-variant bg-surface z-50">
        <div>
          <div className="px-md mb-lg">
            <span className="font-headline-md text-headline-md font-bold text-primary">PharmaMind</span>
            <div className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
              AMP triage for drug-resistant pathogens
            </div>
          </div>

          {/* User / Scientist Profile pill in Nav */}
          <div className="px-md mb-md">
            <Link
              to="/login"
              className="flex items-center justify-between p-2 rounded bg-surface-container hover:bg-surface-container-high transition-colors"
            >
              <div className="flex items-center gap-2 overflow-hidden">
                <div className="w-7 h-7 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs shrink-0">
                  {user ? user.full_name.charAt(0) : <Icon name="person" size={16} />}
                </div>
                <div className="overflow-hidden">
                  <div className="font-label-bold text-xs text-on-surface truncate">
                    {user ? user.full_name : "Sign In"}
                  </div>
                  <div className="font-body-sm text-[11px] text-on-surface-variant truncate">
                    {user ? `${user.role.toUpperCase()} • Lab #${user.lab_id}` : "Guest Mode"}
                  </div>
                </div>
              </div>
              <Icon name="chevron_right" size={16} className="text-outline" />
            </Link>
          </div>

          <ul className="flex flex-col space-y-1">
            {NAV.map((item) => (
              <li className="px-md" key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center space-x-3 px-3 py-2 rounded transition-colors ${
                      isActive
                        ? "text-primary border-l-4 border-primary bg-surface-container-high"
                        : "text-on-surface-variant hover:text-primary hover:bg-surface-container"
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon name={item.icon} fill={isActive} />
                      <span className="font-label-bold text-label-bold">{item.label}</span>
                      {item.to === "/compare" && tray.length > 0 && (
                        <span className="ml-auto bg-primary text-on-primary rounded-full px-1.5 font-label-bold text-label-bold">
                          {tray.length}
                        </span>
                      )}
                      {item.to === "/projects" && activeProject && (
                        <span className="ml-auto w-2 h-2 rounded-full bg-secondary" title="Active Project" />
                      )}
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
        </nav>

      <header className="fixed top-0 right-0 left-0 md:left-64 z-40 flex items-center justify-between px-lg h-14 border-b border-outline-variant bg-surface-container-lowest gap-4">
        <div className="flex items-center text-primary shrink-0">
          <span className="font-headline-sm text-headline-sm">{title}</span>
        </div>

        <div className="flex items-center gap-4 overflow-x-auto py-1">
          {/* Project Selector */}
          {user && (
            <label className="flex items-center gap-2 shrink-0">
              <span className="font-label-bold text-label-bold text-on-surface-variant uppercase text-xs">
                Campaign
              </span>
              <select
                className={`border rounded px-2 py-1 font-body-md text-body-md ${
                  activeProject
                    ? "border-primary bg-primary/5 text-primary font-medium"
                    : "border-outline-variant bg-surface-container-lowest text-on-surface"
                }`}
                value={activeProject ? activeProject.id : ""}
                onChange={(e) => {
                  const val = e.target.value;
                  if (!val) {
                    setActiveProject(null);
                  } else {
                    const found = projects.find((p) => p.id === Number(val));
                    if (found) setActiveProject(found);
                  }
                }}
              >
                <option value="">No Active Campaign</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.target_species.split(" ")[0][0]}. {p.target_species.split(" ")[1]})
                  </option>
                ))}
              </select>
            </label>
          )}

          {/* Species Selector */}
          <label className="flex items-center gap-2 shrink-0">
            <span className="font-label-bold text-label-bold text-on-surface-variant uppercase text-xs">
              Target
            </span>
            <select
              className={`border rounded px-2 py-1 font-body-md text-body-md ${
                activeProject
                  ? "border-secondary text-secondary bg-secondary/5"
                  : "border-outline-variant bg-surface-container-lowest text-on-surface"
              }`}
              value={species}
              disabled={!!activeProject}
              title={activeProject ? `Locked to active campaign '${activeProject.name}'` : undefined}
              onChange={(e) => setSpecies(e.target.value)}
            >
              {(speciesList.length ? speciesList.map((s) => s.name) : [species]).map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
            {activeProject && (
              <span title="Target follows active campaign">
                <Badge className="bg-secondary-container text-on-secondary-container text-[10px]">
                  Campaign Target
                </Badge>
              </span>
            )}
          </label>
        </div>
      </header>

      <main className="flex-1 mt-14 ml-0 md:ml-64 p-lg overflow-y-auto h-[calc(100vh-3.5rem)]">
        {children}
      </main>
    </div>
  );
}

