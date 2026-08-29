import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setAuthToken } from "../api";
import { Badge, Button, Card, ErrorNote, Icon, SectionTitle } from "../components/ui";
import { useStore } from "../store";

const DEMO_USERS = [
  {
    name: "Dr. Elena Rostova",
    role: "lead",
    email: "elena.rostova@amr-unit.org",
    password: "ElenaDemo2026!",
    target: "E. coli Campaign",
  },
  {
    name: "Dr. Marcus Chen",
    role: "scientist",
    email: "marcus.chen@amr-unit.org",
    password: "MarcusDemo2026!",
    target: "Pseudomonas Project",
  },
  {
    name: "Dr. Priya Patel",
    role: "scientist",
    email: "priya.patel@amr-unit.org",
    password: "PriyaDemo2026!",
    target: "MRSA Project",
  },
];

export default function Login() {
  const { user, login, logout, setUser } = useStore();
  const navigate = useNavigate();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [labName, setLabName] = useState("Sample AMR Research Unit");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (mode === "login") {
        await login(email, password);
        navigate("/projects");
      } else {
        const res = await api.auth.register({
          email,
          full_name: fullName,
          password,
          lab_name: labName,
        });
        setAuthToken(res.access_token);
        setUser(res.scientist);
        navigate("/projects");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (demo: typeof DEMO_USERS[0]) => {
    setEmail(demo.email);
    setPassword(demo.password);
    setMode("login");
    setError(null);
  };

  if (user) {
    return (
      <div className="max-w-2xl mx-auto space-y-lg py-md">
        <SectionTitle hint="Authenticated session active">Scientist Profile</SectionTitle>

        <Card className="p-lg space-y-md">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-md">
              <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center font-headline-sm">
                <Icon name="person" size={28} />
              </div>
              <div>
                <h3 className="font-headline-sm text-headline-sm text-on-surface">{user.full_name}</h3>
                <div className="font-body-md text-body-md text-on-surface-variant">{user.email}</div>
              </div>
            </div>
            <Badge className="bg-secondary-container text-on-secondary-container">{user.role}</Badge>
          </div>

          <div className="border-t border-outline-variant pt-md grid grid-cols-2 gap-md">
            <div>
              <div className="font-label-bold text-label-bold text-on-surface-variant uppercase">Lab ID</div>
              <div className="font-body-md text-body-md text-on-surface mt-0.5">Lab #{user.lab_id}</div>
            </div>
            <div>
              <div className="font-label-bold text-label-bold text-on-surface-variant uppercase">Member Since</div>
              <div className="font-body-md text-body-md text-on-surface mt-0.5">
                {new Date(user.created_at).toLocaleDateString()}
              </div>
            </div>
          </div>

          <div className="flex gap-md pt-md">
            <Button variant="filled" onClick={() => navigate("/projects")}>
              <Icon name="folder" size={18} />
              View Projects
            </Button>
            <Button variant="outlined" onClick={logout}>
              <Icon name="logout" size={18} />
              Sign Out
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-lg py-md">
      <SectionTitle hint="Sign in to save candidate shortlists, campaigns, and lab memory">
        Scientist Authentication
      </SectionTitle>

      {/* Demo Credentials Quick Fill Bar */}
      <Card className="p-md bg-surface-container-low border-primary/20">
        <div className="flex items-center gap-2 mb-2 text-primary font-label-bold text-label-bold uppercase">
          <Icon name="bolt" size={16} />
          Seeded Demo Accounts (Click to Fill)
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {DEMO_USERS.map((demo) => (
            <button
              key={demo.email}
              type="button"
              onClick={() => handleQuickFill(demo)}
              className="text-left p-2 rounded bg-surface-container-lowest border border-outline-variant hover:border-primary transition-colors"
            >
              <div className="font-label-bold text-label-bold text-on-surface truncate">{demo.name}</div>
              <div className="font-body-sm text-body-sm text-primary capitalize">{demo.role}</div>
              <div className="font-body-sm text-body-sm text-outline truncate text-[11px]">{demo.target}</div>
            </button>
          ))}
        </div>
      </Card>

      <Card className="p-lg">
        {/* Toggle Mode */}
        <div className="flex border-b border-outline-variant mb-lg">
          <button
            type="button"
            className={`pb-2 px-4 font-label-bold text-label-bold transition-colors ${
              mode === "login"
                ? "border-b-2 border-primary text-primary"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
            onClick={() => {
              setMode("login");
              setError(null);
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`pb-2 px-4 font-label-bold text-label-bold transition-colors ${
              mode === "register"
                ? "border-b-2 border-primary text-primary"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
            onClick={() => {
              setMode("register");
              setError(null);
            }}
          >
            Register Account
          </button>
        </div>

        {error && (
          <div className="mb-md">
            <ErrorNote>{error}</ErrorNote>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-md">
          {mode === "register" && (
            <>
              <div>
                <label className="block font-label-bold text-label-bold text-on-surface-variant uppercase mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Dr. Alex Morgan"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-surface-container-lowest border border-outline-variant font-body-md text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="block font-label-bold text-label-bold text-on-surface-variant uppercase mb-1">
                  Research Unit / Lab Name
                </label>
                <input
                  type="text"
                  placeholder="Sample AMR Research Unit"
                  value={labName}
                  onChange={(e) => setLabName(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-surface-container-lowest border border-outline-variant font-body-md text-on-surface focus:outline-none focus:border-primary"
                />
              </div>
            </>
          )}

          <div>
            <label className="block font-label-bold text-label-bold text-on-surface-variant uppercase mb-1">
              Email Address
            </label>
            <input
              type="email"
              required
              placeholder="scientist@amr-unit.org"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 rounded bg-surface-container-lowest border border-outline-variant font-body-md text-on-surface focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label className="block font-label-bold text-label-bold text-on-surface-variant uppercase mb-1">
              Password
            </label>
            <input
              type="password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 rounded bg-surface-container-lowest border border-outline-variant font-body-md text-on-surface focus:outline-none focus:border-primary"
            />
          </div>

          <div className="pt-2">
            <Button variant="filled" disabled={loading} className="w-full justify-center">
              {loading ? (
                "Authenticating…"
              ) : mode === "login" ? (
                <>
                  <Icon name="login" size={18} />
                  Sign In to PharmaMind
                </>
              ) : (
                <>
                  <Icon name="person_add" size={18} />
                  Create Scientist Account
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
