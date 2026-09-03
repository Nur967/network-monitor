import { useEffect, useState } from "react";
import "./index.css";
import AddTargetForm from "./components/AddTargetForm";
import TargetCard from "./components/TargetCard";
import { getTargets, getHealth } from "./services/api";
import { Target } from "./types";

function App() {
  const [backendStatus, setBackendStatus] = useState<"loading" | "connected" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const loadTargets = async () => {
    setLoading(true);
    try {
      const res = await getTargets();
      setTargets(res);
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to load targets");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        const h = await getHealth();
        if (h.status === "ok") setBackendStatus("connected");
        else {
          setBackendStatus("error");
          setErrorMessage("Backend unhealthy");
        }
      } catch (err: any) {
        setBackendStatus("error");
        setErrorMessage(err?.message || "Failed to reach backend");
      }

      await loadTargets();
    };

    init();

    const interval = setInterval(() => {
      // refresh lightweight list of targets
      loadTargets();
    }, 60_000);

    return () => clearInterval(interval);
  }, []);

  const onCreated = () => {
    loadTargets();
  };

  const onDeleted = (id: string) => {
    setTargets((t) => t.filter((x) => x.id !== id));
  };

  const onUpdated = (updated: Target) => {
    setTargets((t) => t.map((x) => (x.id === updated.id ? updated : x)));
  };

  return (
    <div className="app-root">
      <header className="app-header">
        <div>
          <h1>Network Monitor</h1>
          <p className="subtitle">Real-time uptime and response monitoring</p>
        </div>
        <div className="backend-status">
          {backendStatus === "loading" && <span className="status loading">Checking...</span>}
          {backendStatus === "connected" && <span className="status connected">⦿ Connected</span>}
          {backendStatus === "error" && <span className="status error">✖ {errorMessage || "Backend error"}</span>}
        </div>
      </header>

      <main className="main">
        <section className="controls">
          <AddTargetForm onCreated={onCreated} />
        </section>

        <section className="targets-section">
          {loading && <p className="info">Loading targets...</p>}
          {!loading && targets.length === 0 && <p className="info">No targets yet. Add a URL to start monitoring.</p>}

          <div className="grid">
            {targets.map((t) => (
              <TargetCard key={t.id} target={t} onDeleted={onDeleted} onUpdated={onUpdated} />
            ))}
          </div>
        </section>
      </main>

      <footer className="footer">© Network Monitor</footer>
    </div>
  );
}

export default App;
