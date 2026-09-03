import { useEffect, useState } from "react";
import { Target, CheckRecord } from "../types";
import {
  deleteTarget,
  checkNow,
  getHistory,
  getStats,
} from "../services/api";
import ResponseChart from "./ResponseChart";

export default function TargetCard({
  target,
  onDeleted,
  onUpdated,
}: {
  target: Target;
  onDeleted: (id: string) => void;
  onUpdated: (t: Target) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [checking, setChecking] = useState(false);
  const [history, setHistory] = useState<CheckRecord[] | null>(null);

  useEffect(() => {
    if (expanded) {
      loadHistory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expanded]);

  const loadHistory = async () => {
    try {
      const h = await getHistory(target.id);
      setHistory(Array.isArray(h) ? h : []);
    } catch (err) {
      console.error("Failed to load history:", err);
      setHistory([]);
    }
  };

  const doCheck = async () => {
    setChecking(true);

    try {
      const result = await checkNow(target.id);
      const stats = await getStats(target.id);

      onUpdated({
        ...target,
        online: result.online,
        last_status_code: result.status_code,
        average_response_time_ms:
          stats.average_response_time_ms ??
          result.response_time_ms ??
          null,
        uptime_24h: stats.uptime_24h ?? null,
        last_checked_at:
          stats.last_checked_at ??
          result.checked_at ??
          new Date().toISOString(),
      });

      await loadHistory();
    } catch (err) {
      console.error("Check failed:", err);
    } finally {
      setChecking(false);
    }
  };

  const doDelete = async () => {
    if (!confirm(`Delete monitor ${target.url}?`)) {
      return;
    }

    try {
      await deleteTarget(target.id);
      onDeleted(target.id);
    } catch (err) {
      console.error("Delete failed:", err);
      alert("Failed to delete target");
    }
  };

  const recentFails = (history ?? [])
    .filter(
      (check) =>
        check.error ||
        (check.status_code !== null &&
          check.status_code !== undefined &&
          check.status_code >= 400)
    )
    .slice(0, 5);

  return (
    <div className="card">
      <div className="row">
        <div>
          <div className="url">{target.url}</div>

          <div className="meta small">
            <span
              className={`status-dot ${
                target.online ? "status-online" : "status-offline"
              }`}
            />

            {target.online ? "Online" : "Offline"}

            <span style={{ marginLeft: 8 }}>
              · {target.uptime_24h ?? "—"}% uptime (24h)
            </span>
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <div className="small">
            Avg {target.average_response_time_ms ?? "—"} ms
          </div>

          <div className="small">
            {target.last_status_code ?? "-"}
          </div>
        </div>
      </div>

      <div
        style={{ marginTop: 12 }}
        className="row"
      >
        <button
          className="btn"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "Close" : "Details"}
        </button>

        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn ghost"
            onClick={doCheck}
            disabled={checking}
          >
            {checking ? "Checking..." : "Check Now"}
          </button>

          <button
            className="btn warn"
            onClick={doDelete}
          >
            Delete
          </button>
        </div>
      </div>

      {expanded && (
        <div>
          <div style={{ marginTop: 10 }}>
            <strong className="small">
              Response time history
            </strong>

            {history === null ? (
              <div className="small">
                Loading history...
              </div>
            ) : history.length === 0 ? (
              <div className="small">
                No history
              </div>
            ) : (
              <ResponseChart data={history} />
            )}
          </div>

          <div style={{ marginTop: 8 }}>
            <strong className="small">
              Recent failed checks
            </strong>

            <div className="fail-list">
              {recentFails.length === 0 && (
                <div className="small">
                  No recent failures
                </div>
              )}

              {recentFails.map((failure) => (
                <div
                  key={failure.id}
                  className="fail-item small"
                >
                  <div>
                    {new Date(
                      failure.checked_at
                    ).toLocaleString()}
                  </div>

                  <div>
                    {failure.error ??
                      `HTTP ${failure.status_code}`}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}