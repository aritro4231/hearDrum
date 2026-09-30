import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  editListeningSessionSettings,
  endListeningSession,
  getCurrentListeningSession,
  pauseListeningSession,
  resumeListeningSession,
  startListeningSession,
} from "../api";
import { useAuth } from "../auth/authStore";
import "./Results.css";

function readAmbientAnalysis() {
  try {
    return JSON.parse(localStorage.getItem("ambientAnalysis") || "null");
  } catch {
    return null;
  }
}

function formatDuration(totalSeconds) {
  const seconds = Math.max(0, Math.floor(totalSeconds || 0));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return [hours, minutes, secs]
    .map((part) => String(part).padStart(2, "0"))
    .join(":");
}

function formatMinutes(seconds) {
  const minutes = Math.round((seconds || 0) / 60);
  return `${minutes} min`;
}

function formatPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "0%";
  return `${number.toFixed(number >= 100 ? 0 : 1)}%`;
}

function formatConnection(value) {
  return value === "bluetooth" ? "Bluetooth" : "Wired";
}

function getLiveDurationSeconds(session, nowMs) {
  if (!session) return 0;
  const accumulated = Number(session.accumulated_duration_seconds || 0);
  if (session.status === "active" && session.last_resumed_at) {
    const resumedAt = Date.parse(session.last_resumed_at);
    if (Number.isFinite(resumedAt)) {
      return Math.max(0, accumulated + (nowMs - resumedAt) / 1000);
    }
  }
  return Number(session.actual_duration_seconds || accumulated || 0);
}

function getLiveExposurePercent(session, durationSeconds) {
  const allowable = Number(session?.allowable_duration_seconds || 0);
  if (allowable <= 0) return Number(session?.current_exposure_percent || 0);
  return (durationSeconds / allowable) * 100;
}

export default function Results() {
  const navigate = useNavigate();
  const { isAuthenticated, token } = useAuth();
  const volume = localStorage.getItem("listeningVolume");
  const estimatedDb = localStorage.getItem("estimatedDb");
  const listeningType = localStorage.getItem("listeningType");
  const modelData = JSON.parse(localStorage.getItem("selectedModel") || "null");
  const [ambientAnalysis] = useState(readAmbientAnalysis);
  const [session, setSession] = useState(null);
  const [completedSession, setCompletedSession] = useState(null);
  const [today, setToday] = useState(null);
  const [sessionBaselineExposure, setSessionBaselineExposure] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState("");
  const [nowMs, setNowMs] = useState(Date.now());

  const volumeNumber = Number(volume);
  const dbNumber = Number(estimatedDb);
  const ambientUsed = Boolean(
    ambientAnalysis?.analysis_used &&
      ambientAnalysis?.environment_class &&
      Number.isFinite(Number(ambientAnalysis?.confidence))
  );

  const applySessionResponse = (data) => {
    if (data?.session) {
      setSession(data.session);
      setSessionBaselineExposure(Number(data.session.current_exposure_percent || 0));
    }
    if (data?.today) setToday(data.today);
  };

  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setLoading(false);
      setError("Please log in before starting a listening session.");
      return;
    }

    if (
      !modelData?.name ||
      !listeningType ||
      !Number.isFinite(volumeNumber) ||
      !Number.isFinite(dbNumber)
    ) {
      setLoading(false);
      setError("Missing setup data. Please go back and choose your settings.");
      return;
    }

    let isMounted = true;

    (async () => {
      try {
        setLoading(true);
        const current = await getCurrentListeningSession(token);
        if (!isMounted) return;

        if (current.session) {
          applySessionResponse(current);
          setStatusMessage("Recovered your current listening session.");
          return;
        }

        const started = await startListeningSession(token, {
          headphone_name: modelData.name,
          connection_type: listeningType,
          volume_percent: volumeNumber,
          estimated_db: dbNumber,
          ambient_analysis_used: ambientUsed,
          ambient_environment_class: ambientUsed
            ? ambientAnalysis.environment_class
            : null,
          ambient_confidence: ambientUsed
            ? Number(ambientAnalysis.confidence)
            : null,
        });
        if (!isMounted) return;
        applySessionResponse(started);
        setStatusMessage(started.recovered ? "Recovered your current listening session." : "Session started.");
      } catch (err) {
        if (isMounted) {
          setError(err.message || "Could not start a listening session.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [
    ambientAnalysis,
    ambientUsed,
    dbNumber,
    isAuthenticated,
    listeningType,
    modelData?.name,
    token,
    volumeNumber,
  ]);

  const liveDurationSeconds = useMemo(
    () => getLiveDurationSeconds(session, nowMs),
    [nowMs, session]
  );
  const liveExposurePercent = useMemo(
    () => getLiveExposurePercent(session, liveDurationSeconds),
    [liveDurationSeconds, session]
  );
  const remainingSeconds = Math.max(
    0,
    Number(session?.allowable_duration_seconds || 0) - liveDurationSeconds
  );
  const todayExposure = Math.max(
    0,
    Number(today?.total_exposure_percent || 0) -
      sessionBaselineExposure +
      liveExposurePercent
  );
  const todayListeningSeconds = Math.max(
    0,
    Number(today?.total_listening_seconds || 0) -
      Number(session?.actual_duration_seconds || 0) +
      liveDurationSeconds
  );

  const runAction = async (action, successMessage) => {
    if (!session?.id || !token) return;
    setError("");
    try {
      const data = await action(token, session.id);
      applySessionResponse(data);
      setStatusMessage(successMessage);
      return data;
    } catch (err) {
      setError(err.message || "Session action failed.");
      return null;
    }
  };

  const pause = () => runAction(pauseListeningSession, "Paused.");
  const resume = () => runAction(resumeListeningSession, "Resumed.");

  const end = async () => {
    const data = await runAction(endListeningSession, "Session complete.");
    if (data?.session) {
      setCompletedSession(data.session);
      setSession(data.session);
    }
  };

  const editSettings = async () => {
    const data = await runAction(
      editListeningSessionSettings,
      "Current session finalized. Update your settings."
    );
    if (data?.next_settings) {
      localStorage.setItem("listeningVolume", String(data.next_settings.volume_percent));
      localStorage.setItem("estimatedDb", String(data.next_settings.estimated_db));
    }
    if (data?.session) {
      setCompletedSession(data.session);
      navigate("/volume");
    }
  };

  const startAnother = () => {
    localStorage.removeItem("ambientAnalysis");
    navigate("/ambient");
  };

  if (loading) {
    return <p className="results-info">Starting your listening session...</p>;
  }

  if (error && !session) {
    return <p className="results-info">{error}</p>;
  }

  if (!session) {
    return <p className="results-info">No listening session is active.</p>;
  }

  if (completedSession || session.status === "completed") {
    const finalSession = completedSession || session;
    return (
      <div className="results-container">
        <h1 className="results-title">Session Complete</h1>

        <div className="results-card">
          <p className="results-card-label">Listened</p>
          <p className="results-card-value">
            {formatMinutes(finalSession.actual_duration_seconds)}
          </p>
        </div>

        <div className="results-card results-grid-card">
          <div>
            <span>Session exposure</span>
            <strong>{formatPercent(finalSession.exposure_percent)}</strong>
          </div>
          <div>
            <span>Today's exposure</span>
            <strong>{formatPercent(today?.total_exposure_percent)}</strong>
          </div>
        </div>

        <div className="results-actions">
          <button type="button" className="results-primary" onClick={startAnother}>
            Start Another Session
          </button>
          <button
            type="button"
            className="results-secondary"
            onClick={() => navigate("/dashboard")}
          >
            View My Sessions
          </button>
        </div>
      </div>
    );
  }

  const isPaused = session.status === "paused";
  const environmentLabel = session.ambient_analysis_used
    ? (session.ambient_environment_class || "").replaceAll("_", " ")
    : "";

  return (
    <div className="results-container">
      <h1 className="results-title">Safe Listening Time</h1>

      <div className="results-countdown-card">
        <p className="results-session-state">{isPaused ? "Paused" : "Active"}</p>
        <p className="results-countdown">{formatDuration(remainingSeconds)}</p>
        <p className="results-card-label">remaining</p>
      </div>

      <div className="results-card results-session-summary">
        <p>
          <b>{session.headphone?.name || modelData?.name}</b> •{" "}
          {formatConnection(session.connection_type)}
        </p>
        <p>Volume: {session.volume_percent}%</p>
        <p>Estimated Output: {session.estimated_db} dB SPL</p>
        {session.ambient_analysis_used && (
          <p className="results-capitalize">Environment: {environmentLabel}</p>
        )}
      </div>

      <div className="results-card results-grid-card">
        <div>
          <span>Today's Exposure</span>
          <strong>{formatPercent(todayExposure)}</strong>
        </div>
        <div>
          <span>Session Exposure</span>
          <strong>{formatPercent(liveExposurePercent)}</strong>
        </div>
        <div>
          <span>Actual Listening</span>
          <strong>{formatDuration(liveDurationSeconds)}</strong>
        </div>
        <div>
          <span>Today Listened</span>
          <strong>{formatMinutes(todayListeningSeconds)}</strong>
        </div>
      </div>

      <p className="results-footnote">
        Exposure uses the existing NIOSH estimate: actual listening time divided by
        allowable time at the estimated sound level. Paused time is not counted.
      </p>

      {statusMessage && <p className="results-save-status">{statusMessage}</p>}
      {error && <p className="results-error">{error}</p>}

      <div className="results-actions">
        {isPaused ? (
          <button type="button" className="results-primary" onClick={resume}>
            Resume
          </button>
        ) : (
          <button type="button" className="results-primary" onClick={pause}>
            Pause
          </button>
        )}

        <button type="button" className="results-secondary" onClick={editSettings}>
          Edit Settings
        </button>

        <button type="button" className="results-secondary" onClick={end}>
          End Session
        </button>
      </div>
    </div>
  );
}
