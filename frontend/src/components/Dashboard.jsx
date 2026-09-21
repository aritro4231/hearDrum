import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getListeningSessions } from "../api";
import { useAuth } from "../auth/AuthContext";
import "./Dashboard.css";

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

      {!loading && !error && sessions.length > 0 && (
        <div className="session-list">
          {sessions.map((session) => (
            <article className="session-card" key={session.id}>
              <div>
                <h2>{session.headphone?.name || "Unknown headphone"}</h2>
                <p>{new Date(session.created_at).toLocaleString()}</p>
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
                  <dt>Duration</dt>
                  <dd>{session.duration_minutes} min</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
