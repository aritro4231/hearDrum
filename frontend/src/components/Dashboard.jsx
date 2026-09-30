import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getListeningSessions } from "../api";
import { useAuth } from "../auth/authStore";
import "./Dashboard.css";

function formatAmbientClass(value) {
  if (!value) return "";
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatConfidence(value) {
  const confidence = Number(value);
  if (!Number.isFinite(confidence)) return "";
  return `${Math.round(confidence * 100)}%`;
}

function formatPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "0%";
  return `${number.toFixed(number >= 100 ? 0 : 1)}%`;
}

function formatMinutes(seconds) {
  return `${Math.round(Number(seconds || 0) / 60)} min`;
}

function sessionDate(session) {
  return new Date(session.started_at || session.created_at);
}

function groupSessionsByDate(sessions) {
  const groups = new Map();
  for (const session of sessions) {
    const date = sessionDate(session);
    const key = date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
    if (!groups.has(key)) {
      groups.set(key, {
        label: key,
        sessions: [],
        exposure: 0,
        seconds: 0,
      });
    }
    const group = groups.get(key);
    group.sessions.push(session);
    group.exposure += Number(
      session.status === "completed"
        ? session.exposure_percent
        : session.current_exposure_percent
    ) || 0;
    group.seconds += Number(session.actual_duration_seconds || 0);
  }
  return [...groups.values()];
}

export default function Dashboard() {
  const { isAuthenticated, logout, token, user } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/auth", { replace: true });
      return;
    }

    let isMounted = true;

    (async () => {
      try {
        const data = await getListeningSessions(token);
        if (!isMounted) return;
        setSessions(data.sessions || []);
      } catch (err) {
        if (!isMounted) return;
        setError(err.message || "Could not load listening history.");
      } finally {
        if (isMounted) setLoading(false);
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, navigate, token]);

  const groupedSessions = useMemo(() => groupSessionsByDate(sessions), [sessions]);

  const signOut = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">{user?.username || "Account"}</h1>
          <p className="dashboard-copy">Your saved listening sessions.</p>
        </div>

        <button type="button" className="dashboard-logout motion-btn" onClick={signOut}>
          Log Out
        </button>
      </div>

      {loading && <p className="dashboard-muted">Loading history...</p>}
      {error && <p className="dashboard-error">{error}</p>}

      {!loading && !error && sessions.length === 0 && (
        <div className="dashboard-empty">
          <p>No listening sessions yet.</p>
        </div>
      )}

      {!loading && !error && groupedSessions.length > 0 && (
        <div className="session-day-list">
          {groupedSessions.map((group) => (
            <section className="session-day" key={group.label}>
              <div className="session-day-header">
                <h2>{group.label}</h2>
                <p>
                  {group.sessions.length} session{group.sessions.length === 1 ? "" : "s"} •{" "}
                  {formatMinutes(group.seconds)} listened • {formatPercent(group.exposure)} exposure
                </p>
              </div>

              <div className="session-list">
                {group.sessions.map((session) => (
                  <article className="session-card" key={session.id}>
                    <div>
                      <h2>{session.headphone?.name || "Unknown headphone"}</h2>
                      <p>
                        {sessionDate(session).toLocaleTimeString([], {
                          hour: "numeric",
                          minute: "2-digit",
                        })}
                        {session.ended_at
                          ? ` - ${new Date(session.ended_at).toLocaleTimeString([], {
                              hour: "numeric",
                              minute: "2-digit",
                            })}`
                          : ` - ${session.status}`}
                      </p>
                    </div>

                    <dl>
                      <div>
                        <dt>Connection</dt>
                        <dd>{session.connection_type}</dd>
                      </div>
                      <div>
                        <dt>Volume</dt>
                        <dd>{session.volume_percent}%</dd>
                      </div>
                      <div>
                        <dt>Estimated dB</dt>
                        <dd>{session.estimated_db} dB SPL</dd>
                      </div>
                      <div>
                        <dt>Listened</dt>
                        <dd>{formatMinutes(session.actual_duration_seconds)}</dd>
                      </div>
                      <div>
                        <dt>Exposure</dt>
                        <dd>
                          {formatPercent(
                            session.status === "completed"
                              ? session.exposure_percent
                              : session.current_exposure_percent
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>Status</dt>
                        <dd>{session.status}</dd>
                      </div>
                    </dl>

                    {session.ambient_analysis_used && (
                      <div className="session-ambient">
                        <span>Environmental context</span>
                        <strong>
                          {formatAmbientClass(session.ambient_environment_class)}
                          {session.ambient_confidence != null
                            ? ` (${formatConfidence(session.ambient_confidence)})`
                            : ""}
                        </strong>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
