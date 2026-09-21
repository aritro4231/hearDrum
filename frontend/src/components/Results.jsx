import { useEffect, useState } from "react";
import { saveListeningSession } from "../api";
import { useAuth } from "../auth/AuthContext";
import "./Results.css";

export default function Results() {
  const ALERT_KEY = "safeAlertedAt";
  const END_KEY = "safeEndAt";
  const volume = localStorage.getItem("listeningVolume");
  const estimatedDb = localStorage.getItem("estimatedDb");
  const listeningType = localStorage.getItem("listeningType");
  const modelData = JSON.parse(localStorage.getItem("selectedModel") || "null");
  const { isAuthenticated, token } = useAuth();

  const volumeNumber = Number(volume);
  const dbNumber = Number(estimatedDb);
  const safeMinutes = Math.round(480 * Math.pow(2, (85 - dbNumber) / 3));
  const initialSeconds = Math.max(0, safeMinutes * 60);
  const [remainingSeconds, setRemainingSeconds] = useState(initialSeconds);
  const [saveStatus, setSaveStatus] = useState("");

  useEffect(() => {
    if (!Number.isFinite(initialSeconds)) return;
    setRemainingSeconds(initialSeconds);
    const endAt = Date.now() + initialSeconds * 1000;
    localStorage.setItem(END_KEY, String(endAt));
    localStorage.removeItem(ALERT_KEY);
  }, [initialSeconds]);

  useEffect(() => {
    if (!Number.isFinite(remainingSeconds) || remainingSeconds <= 0) return;
    const timer = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          localStorage.setItem(ALERT_KEY, String(Date.now()));
          alert("Safe listening time reached. Please take a break.");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [remainingSeconds]);

  useEffect(() => {
    if (
      !isAuthenticated ||
      !token ||
      !modelData?.name ||
      !listeningType ||
      !Number.isFinite(volumeNumber) ||
      !Number.isFinite(dbNumber) ||
      !Number.isFinite(safeMinutes)
    ) {
      return;
    }

    const saveKey = [
      "savedSession",
      modelData.name,
      listeningType,
      volumeNumber,
      dbNumber,
      safeMinutes,
    ].join(":");

    if (sessionStorage.getItem(saveKey) === "1") return;

    let isMounted = true;

    (async () => {
      try {
        await saveListeningSession(token, {
          headphone_name: modelData.name,
          connection_type: listeningType,
          volume_percent: volumeNumber,
          estimated_db: dbNumber,
          duration_minutes: Math.max(1, safeMinutes),
        });
        sessionStorage.setItem(saveKey, "1");
        if (isMounted) setSaveStatus("Saved to your account.");
      } catch {
        if (isMounted) setSaveStatus("Could not save this session.");
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [
    dbNumber,
    isAuthenticated,
    listeningType,
    modelData?.name,
    safeMinutes,
    token,
    volumeNumber,
  ]);

  if (!Number.isFinite(volumeNumber) || !Number.isFinite(dbNumber)) {
    return (
      <p className="results-info">
        Missing volume data. Please go back and set your volume.
      </p>
    );
  }

  const safeHours = Math.floor(remainingSeconds / 3600);
  const safeMinsOnly = Math.floor((remainingSeconds % 3600) / 60);
  const safeSecsOnly = remainingSeconds % 60;

  return (
    <div className="results-container">
      <h1 className="results-title">Your Safe Listening Results</h1>

      <p className="results-info">
        Estimated Output: <b className="results-highlight">{dbNumber} dB SPL</b>
      </p>

      <p className="results-info">
        Listening Volume: <b className="results-highlight">{volumeNumber}%</b>
      </p>

      <div className="results-card">
        <p className="results-card-label">Safe Listening Time (NIOSH)</p>
        <p className="results-card-value">
          {safeHours > 0 ? `${safeHours}h ` : ""}
          {safeMinsOnly}m {safeSecsOnly}s
        </p>
      </div>

      <p className="results-footnote">
        Based on NIOSH Recommended Exposure Limit: 85 dB = 8 hours, every +3 dB halves time.
      </p>

      {saveStatus && <p className="results-save-status">{saveStatus}</p>}
    </div>
  );
}
