import { useEffect, useState } from "react";
import "./App.css";

type Measurement = {
  recorded_at: string;
  check_type: string;
  target: string;
  is_healthy: boolean;
  latency_ms: number | null;
  packet_loss: number | null;
  details: string | null;
};

type StatusResponse = {
  router: Measurement | null;
  internet: Measurement | null;
  dns: Measurement | null;
  measurement_count: number;
};

type Outage = {
  id: number;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  active: boolean;
};

type OutagesResponse = {
  count: number;
  outages: Outage[];
};

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [outages, setOutages] = useState<Outage[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard() {
    try {
      const [statusResponse, outagesResponse] = await Promise.all([
        fetch(`${API_BASE}/status`),
        fetch(`${API_BASE}/outages?limit=5`),
      ]);

      if (!statusResponse.ok || !outagesResponse.ok) {
        throw new Error("API request failed");
      }

      const statusData: StatusResponse = await statusResponse.json();
      const outageData: OutagesResponse = await outagesResponse.json();

      setStatus(statusData);
      setOutages(outageData.outages);
      setError(null);
    } catch {
      setError(
        "Unable to connect to the NetWatch API. Make sure FastAPI is running."
      );
    }
  }

  useEffect(() => {
    loadDashboard();

    const interval = setInterval(loadDashboard, 5000);

    return () => clearInterval(interval);
  }, []);

  function latency(measurement: Measurement | null) {
    if (!measurement || measurement.latency_ms === null) {
      return "N/A";
    }

    return `${measurement.latency_ms} ms`;
  }

  function formatDuration(seconds: number | null) {
    if (seconds === null) {
      return "Ongoing";
    }

    if (seconds < 60) {
      return `${Math.round(seconds)} sec`;
    }

    return `${(seconds / 60).toFixed(1)} min`;
  }

  const internetHealthy = status?.internet?.is_healthy ?? false;
  const routerHealthy = status?.router?.is_healthy ?? false;
  const dnsHealthy = status?.dns?.is_healthy ?? false;

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>NetWatch</h1>
          <p>Network Health Dashboard</p>
        </div>

        <div className="live-indicator">
          <span className="live-dot"></span>
          Live
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <section className="status-grid">
        <div className="status-card">
          <span className="label">Internet</span>

          <h2 className={internetHealthy ? "healthy" : "unhealthy"}>
            {internetHealthy ? "ONLINE" : "OFFLINE"}
          </h2>

          <p>{latency(status?.internet ?? null)}</p>
        </div>

        <div className="status-card">
          <span className="label">Router</span>

          <h2 className={routerHealthy ? "healthy" : "unhealthy"}>
            {routerHealthy ? "ONLINE" : "OFFLINE"}
          </h2>

          <p>{latency(status?.router ?? null)}</p>
        </div>

        <div className="status-card">
          <span className="label">DNS</span>

          <h2 className={dnsHealthy ? "healthy" : "unhealthy"}>
            {dnsHealthy ? "WORKING" : "FAILED"}
          </h2>

          <p>{status?.dns?.details ?? "No DNS data"}</p>
        </div>
      </section>

      <section className="metrics-grid">
        <div className="metric-card">
          <span>Packet Loss</span>
          <strong>{status?.internet?.packet_loss ?? 0}%</strong>
        </div>

        <div className="metric-card">
          <span>Measurements</span>
          <strong>{status?.measurement_count ?? 0}</strong>
        </div>

        <div className="metric-card">
          <span>Recent Outages</span>
          <strong>{outages.length}</strong>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Recent Outages</h2>
          <p>Internet interruptions detected by NetWatch.</p>
        </div>

        {outages.length === 0 ? (
          <div className="empty-state">No outages recorded yet.</div>
        ) : (
          <div>
            {outages.map((outage) => (
              <div className="outage-row" key={outage.id}>
                <div>
                  <strong>
                    {outage.active ? "Active Outage" : "Resolved Outage"}
                  </strong>

                  <span>
                    {new Date(outage.started_at).toLocaleString()}
                  </span>
                </div>

                <strong>
                  {formatDuration(outage.duration_seconds)}
                </strong>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default App;