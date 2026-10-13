import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
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

type HistoryResponse = {
  count: number;
  measurements: Measurement[];
};

type StatsResponse = {
  sample_size: number;
  average_latency_ms: number | null;
  minimum_latency_ms: number | null;
  maximum_latency_ms: number | null;
  average_packet_loss: number | null;
  uptime_percent: number | null;
};

type ChartPoint = {
  time: string;
  latency: number | null;
  packetLoss: number | null;
};

type Device = {
  id: number;
  ip_address: string;
  mac_address: string;
  interface_alias: string | null;
  neighbor_state: string | null;
  first_seen: string;
  last_seen: string;
  last_online: string | null;
  responding: boolean;
};

type DevicesResponse = {
  count: number;
  devices: Device[];
};

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [status, setStatus] =
    useState<StatusResponse | null>(null);

  const [outages, setOutages] =
    useState<Outage[]>([]);

  const [history, setHistory] =
    useState<ChartPoint[]>([]);

  const [stats, setStats] =
    useState<StatsResponse | null>(null);

  const [error, setError] =
    useState<string | null>(null);

  const [devices, setDevices] =
    useState<Device[]>([]);  

  async function loadDashboard() {
    try {
      const [
        statusResponse,
        outagesResponse,
        historyResponse,
        statsResponse,
        devicesResponse,
      ] = await Promise.all([
        fetch(`${API_BASE}/status`),
        fetch(`${API_BASE}/outages?limit=5`),
        fetch(`${API_BASE}/history?limit=120`),
        fetch(`${API_BASE}/stats?limit=500`),
        fetch(`${API_BASE}/devices`),
      ]);

      if (
        !statusResponse.ok ||
        !outagesResponse.ok ||
        !historyResponse.ok ||
        !statsResponse.ok ||
        !devicesResponse.ok
      ) {
        throw new Error("API request failed");
      }

      const statusData: StatusResponse =
        await statusResponse.json();

      const outageData: OutagesResponse =
        await outagesResponse.json();

      const historyData: HistoryResponse =
        await historyResponse.json();

      const statsData: StatsResponse =
        await statsResponse.json();

      const devicesData: DevicesResponse =
        await devicesResponse.json();

      const chartData = historyData.measurements.map(
        (measurement) => ({
          time: new Date(
            measurement.recorded_at
          ).toLocaleTimeString([], {
            hour: "numeric",
            minute: "2-digit",
            second: "2-digit",
          }),
          latency: measurement.latency_ms,
          packetLoss: measurement.packet_loss,
        })
      );

      setStatus(statusData);
      setOutages(outageData.outages);
      setHistory(chartData);
      setStats(statsData);
      setError(null);
      setDevices(devicesData.devices);
    } catch {
      setError(
        "Unable to connect to the NetWatch API. Make sure FastAPI is running."
      );
    }
  }

  useEffect(() => {
    loadDashboard();

    const interval =
      setInterval(loadDashboard, 5000);

    return () => clearInterval(interval);
  }, []);

  function latency(
    measurement: Measurement | null
  ) {
    if (
      !measurement ||
      measurement.latency_ms === null
    ) {
      return "N/A";
    }

    return `${measurement.latency_ms} ms`;
  }

  function formatDuration(
    seconds: number | null
  ) {
    if (seconds === null) {
      return "Ongoing";
    }

    if (seconds < 60) {
      return `${Math.round(seconds)} sec`;
    }

    return `${(seconds / 60).toFixed(1)} min`;
  }

  function formatMetric(
    value: number | null | undefined,
    suffix: string,
    decimals = 1
  ) {
    if (
      value === null ||
      value === undefined
    ) {
      return "N/A";
    }

    return `${value.toFixed(decimals)}${suffix}`;
  }

  const internetHealthy =
    status?.internet?.is_healthy ?? false;

  const routerHealthy =
    status?.router?.is_healthy ?? false;

  const dnsHealthy =
    status?.dns?.is_healthy ?? false;

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

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <section className="status-grid">
        <div className="status-card">
          <span className="label">
            Internet
          </span>

          <h2
            className={
              internetHealthy
                ? "healthy"
                : "unhealthy"
            }
          >
            {internetHealthy
              ? "ONLINE"
              : "OFFLINE"}
          </h2>

          <p>
            {latency(
              status?.internet ?? null
            )}
          </p>
        </div>

        <div className="status-card">
          <span className="label">
            Router
          </span>

          <h2
            className={
              routerHealthy
                ? "healthy"
                : "unhealthy"
            }
          >
            {routerHealthy
              ? "ONLINE"
              : "OFFLINE"}
          </h2>

          <p>
            {latency(
              status?.router ?? null
            )}
          </p>
        </div>

        <div className="status-card">
          <span className="label">
            DNS
          </span>

          <h2
            className={
              dnsHealthy
                ? "healthy"
                : "unhealthy"
            }
          >
            {dnsHealthy
              ? "WORKING"
              : "FAILED"}
          </h2>

          <p>
            {status?.dns?.details ??
              "No DNS data"}
          </p>
        </div>
      </section>

      <section className="metrics-grid">
        <div className="metric-card">
          <span>Packet Loss</span>
          <strong>
            {status?.internet
              ?.packet_loss ?? 0}
            %
          </strong>
        </div>

        <div className="metric-card">
          <span>Measurements</span>
          <strong>
            {status?.measurement_count ??
              0}
          </strong>
        </div>

        <div className="metric-card">
          <span>Recent Outages</span>
          <strong>
            {outages.length}
          </strong>
        </div>
      </section>

      <section className="statistics-grid">
        <div className="stat-card">
          <span>Average Latency</span>

          <strong>
            {formatMetric(
              stats?.average_latency_ms,
              " ms"
            )}
          </strong>
        </div>

        <div className="stat-card">
          <span>Minimum Latency</span>

          <strong>
            {formatMetric(
              stats?.minimum_latency_ms,
              " ms",
              0
            )}
          </strong>
        </div>

        <div className="stat-card">
          <span>Maximum Latency</span>

          <strong>
            {formatMetric(
              stats?.maximum_latency_ms,
              " ms",
              0
            )}
          </strong>
        </div>

        <div className="stat-card">
          <span>Avg Packet Loss</span>

          <strong>
            {formatMetric(
              stats?.average_packet_loss,
              "%"
            )}
          </strong>
        </div>

        <div className="stat-card">
          <span>Uptime</span>

          <strong>
            {formatMetric(
              stats?.uptime_percent,
              "%",
              2
            )}
          </strong>
        </div>

        <div className="stat-card">
          <span>Stats Samples</span>

          <strong>
            {stats?.sample_size ?? 0}
          </strong>
        </div>
      </section>

      <section className="panel chart-panel">
        <div className="panel-heading">
          <h2>
            Internet Latency History
          </h2>

          <p>
            Recent latency measurements
            collected by NetWatch.
          </p>
        </div>

        <div className="chart-container">
          {history.length === 0 ? (
            <div className="empty-state">
              No historical measurements
              available yet.
            </div>
          ) : (
            <ResponsiveContainer
              width="100%"
              height="100%"
            >
              <LineChart data={history}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#29313d"
                />

                <XAxis
                  dataKey="time"
                  stroke="#8d99a8"
                  minTickGap={45}
                />

                <YAxis
                  stroke="#8d99a8"
                  unit=" ms"
                />

                <Tooltip
                  contentStyle={{
                    background: "#171c24",
                    border: "1px solid #29313d",
                    borderRadius: "10px",
                  }}
                />

                <Line
                  type="monotone"
                  dataKey="latency"
                  stroke="#51d88a"
                  strokeWidth={2}
                  dot={false}
                  connectNulls={false}
                  name="Latency"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Local Devices</h2>

          <p>
            Devices recently visible from this computer
            on the local network.
          </p>
        </div>

        {devices.length === 0 ? (
          <div className="empty-state">
            No local devices discovered yet.
          </div>
        ) : (
          <div className="device-list">
            {devices.map((device) => (
              <div
                className="device-row"
                key={device.id}
              >
                <div className="device-main">
                  <span
                    className={
                      device.responding
                        ? "device-dot online"
                        : "device-dot offline"
                    }
                  ></span>

                  <div>
                    <strong>
                      {device.ip_address}
                    </strong>

                    <span>
                      {device.mac_address}
                    </span>
                  </div>
                </div>

                <div className="device-details">
                  <span>
                    {device.interface_alias ??
                      "Unknown interface"}
                  </span>

                  <strong
                    className={
                      device.responding
                        ? "healthy"
                        : "muted"
                    }
                  >
                    {device.responding
                      ? "Responding"
                      : "Not Responding"}
                  </strong>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Recent Outages</h2>

          <p>
            Internet interruptions
            detected by NetWatch.
          </p>
        </div>

        {outages.length === 0 ? (
          <div className="empty-state">
            No outages recorded yet.
          </div>
        ) : (
          <div>
            {outages.map((outage) => (
              <div
                className="outage-row"
                key={outage.id}
              >
                <div>
                  <strong>
                    {outage.active
                      ? "Active Outage"
                      : "Resolved Outage"}
                  </strong>

                  <span>
                    {new Date(
                      outage.started_at
                    ).toLocaleString()}
                  </span>
                </div>

                <strong>
                  {formatDuration(
                    outage.duration_seconds
                  )}
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