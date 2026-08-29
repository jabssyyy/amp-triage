/** Shared app state.
 *
 *  This is the reason the app is a SPA rather than eight wired-up static pages:
 *  species, pool, shortlist and the compare tray all flow between screens. A judge
 *  clicking Shortlist -> Candidate -> Compare -> What-if must not lose context.
 */
import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
  type ReactNode,
} from "react";
import {
  api, setAuthToken, getAuthToken,
  type Project, type Scientist, type ShortlistResponse, type SpeciesMetric,
} from "./api";

interface Store {
  species: string;
  setSpecies: (s: string) => void;
  speciesList: SpeciesMetric[];
  speciesMeta: SpeciesMetric | undefined;

  pool: string[];
  setPool: (p: string[]) => void;
  poolName: string;
  setPoolName: (n: string) => void;

  k: number;
  setK: (k: number) => void;
  theta: number;
  setTheta: (t: number) => void;

  shortlist: ShortlistResponse | null;
  runShortlist: () => Promise<void>;
  loading: boolean;
  error: string | null;

  /** Sequences staged for side-by-side comparison (max 2). */
  tray: string[];
  toggleTray: (seq: string) => void;
  clearTray: () => void;

  focus: string | null;
  setFocus: (s: string | null) => void;

  // --- Lab memory (phase 8) -------------------------------------------------
  excludeTested: boolean;
  setExcludeTested: (v: boolean) => void;
  penaliseTested: boolean;
  setPenaliseTested: (v: boolean) => void;

  // --- Auth Slice (Phase 7) -------------------------------------------------
  user: Scientist | null;
  token: string | null;
  activeProject: Project | null;
  projects: Project[];
  myProjects: Project[];
  refreshProjects: () => Promise<void>;
  setActiveProject: (p: Project | null) => void;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  setUser: (u: Scientist | null) => void;
}

const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [species, setSpecies] = useState("Escherichia coli");
  const [speciesList, setSpeciesList] = useState<SpeciesMetric[]>([]);
  const [pool, setPool] = useState<string[]>([]);
  const [poolName, setPoolName] = useState("built-in demo pool");
  const [k, setK] = useState(20);
  const [theta, setTheta] = useState(1.0);
  const [shortlist, setShortlist] = useState<ShortlistResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tray, setTray] = useState<string[]>([]);
  // Persisted so a page refresh on Candidate / Graph / Evidence does not lose the
  // selected peptide. Losing it mid-demo looks like a crash.
  const [focus, setFocusState] = useState<string | null>(
    typeof window !== "undefined" ? localStorage.getItem("pharmamind_focus") : null,
  );
  const setFocus = useCallback((s: string | null) => {
    setFocusState(s);
    if (typeof window !== "undefined") {
      if (s) localStorage.setItem("pharmamind_focus", s);
      else localStorage.removeItem("pharmamind_focus");
    }
  }, []);
  const [excludeTested, setExcludeTested] = useState(false);
  const [penaliseTested, setPenaliseTested] = useState(false);

  // Auth & Project State
  const [token, setTokenState] = useState<string | null>(getAuthToken());
  const [user, setUser] = useState<Scientist | null>(null);
  const [activeProject, setActiveProjectState] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [myProjects, setMyProjects] = useState<Project[]>([]);

  useEffect(() => {
    api.species().then(setSpeciesList).catch((e) => setError(String(e.message ?? e)));
  }, []);

  // Restore authenticated session
  useEffect(() => {
    if (token) {
      api.auth
        .me()
        .then((u) => {
          setUser(u);
        })
        .catch(() => {
          setAuthToken(null);
          setTokenState(null);
          setUser(null);
        });
    }
  }, [token]);

  const refreshProjects = useCallback(async () => {
    if (!token) {
      setProjects([]);
      setMyProjects([]);
      return;
    }
    try {
      const [allP, myP] = await Promise.all([
        api.projects.list().catch(() => []),
        api.projects.mine().catch(() => []),
      ]);
      setProjects(allP);
      setMyProjects(myP);
    } catch {
      // Graceful fallback
    }
  }, [token]);

  useEffect(() => {
    if (user) {
      refreshProjects();
    }
  }, [user, refreshProjects]);

  const setActiveProject = useCallback((p: Project | null) => {
    setActiveProjectState(p);
    if (p && p.target_species) {
      setSpecies(p.target_species);
    }
  }, []);

  const login = useCallback(async (email: string, pass: string) => {
    setError(null);
    try {
      const res = await api.auth.login({ email, password: pass });
      setAuthToken(res.access_token);
      setTokenState(res.access_token);
      setUser(res.scientist);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      throw e;
    }
  }, []);

  const logout = useCallback(() => {
    setAuthToken(null);
    setTokenState(null);
    setUser(null);
    setActiveProjectState(null);
    setProjects([]);
    setMyProjects([]);
  }, []);

  // Load the demo pool once so the app is usable without an upload.
  useEffect(() => {
    fetch("/demo_pool.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("no demo pool"))))
      .then((seqs: string[]) => setPool(seqs))
      .catch(() => void 0);
  }, []);

  const runShortlist = useCallback(async () => {
    if (!pool.length) {
      setError("No candidate pool loaded.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setShortlist(await api.shortlist(pool, species, k, theta, {
        project_id: activeProject?.id ?? null,
        exclude_tested: excludeTested,
        penalise_tested: penaliseTested,
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setShortlist(null);
    } finally {
      setLoading(false);
    }
  }, [pool, species, k, theta, excludeTested, penaliseTested, activeProject]);

  const toggleTray = useCallback((seq: string) => {
    setTray((cur) =>
      cur.includes(seq) ? cur.filter((s) => s !== seq) : [...cur, seq].slice(-2),
    );
  }, []);

  const value = useMemo<Store>(
    () => ({
      species, setSpecies, speciesList,
      speciesMeta: speciesList.find((s) => s.name === species),
      pool, setPool, poolName, setPoolName,
      k, setK, theta, setTheta,
      shortlist, runShortlist, loading, error,
      tray, toggleTray, clearTray: () => setTray([]),
      focus, setFocus,
      excludeTested, setExcludeTested, penaliseTested, setPenaliseTested,
      user, token, activeProject, projects, myProjects,
      refreshProjects, setActiveProject, login, logout, setUser,
    }),
    [species, speciesList, pool, poolName, k, theta, shortlist, runShortlist,
     loading, error, tray, toggleTray, focus, excludeTested, penaliseTested,
     user, token, activeProject,
     projects, myProjects, refreshProjects, setActiveProject, login, logout],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore(): Store {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useStore must be used inside StoreProvider");
  return ctx;
}

