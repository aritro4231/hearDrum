import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { analyzeAmbientAudio } from "../api";
import {
  convertRecordingToWav,
  getPreferredRecordingMimeType,
} from "../audio/ambientAudio";
import { useAuth } from "../auth/authStore";
import "./AmbientAnalysis.css";

const AMBIENT_KEY = "ambientAnalysis";
const RECORDING_MS = 4000;
const RECORDING_FAILSAFE_MS = 7000;
const ANALYSIS_FAILSAFE_MS = 30000;

function formatConfidence(value) {
  const confidence = Number(value);
  if (!Number.isFinite(confidence)) return "";
  return `${Math.round(confidence * 100)}%`;
}

export default function AmbientAnalysis() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [result, setResult] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(AMBIENT_KEY) || "null");
    } catch {
      return null;
    }
  });
  const streamRef = useRef(null);
  const recorderRef = useRef(null);
  const mountedRef = useRef(true);

  const stopStreamTracks = useCallback(() => {
    if (!streamRef.current) return;
    streamRef.current.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    const volume = localStorage.getItem("listeningVolume");
    const estimatedDb = localStorage.getItem("estimatedDb");
    if (!volume || !estimatedDb) {
      navigate("/volume", { replace: true });
    }
  }, [navigate]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      stopRecorder(recorderRef.current);
      stopStreamTracks();
    };
  }, [stopStreamTracks]);

  const skip = () => {
    localStorage.setItem(
      AMBIENT_KEY,
      JSON.stringify({ analysis_used: false, skipped: true })
    );
    navigate("/results");
  };

  const continueToResults = () => {
    navigate("/results");
  };

  const analyze = async () => {
    if (!token) {
      setError("Please log in before analyzing your environment.");
      setStatus("error");
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError("Microphone recording is not supported in this browser.");
      setStatus("error");
      return;
    }

    setError("");
    setResult(null);
    localStorage.removeItem(AMBIENT_KEY);
    setStatus("listening");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = getPreferredRecordingMimeType();
      const recorder = new MediaRecorder(
        stream,
        mimeType ? { mimeType } : undefined
      );
      recorderRef.current = recorder;

      const { browserBlob } = await recordForDuration(
        recorder,
        mimeType,
        RECORDING_MS,
        RECORDING_FAILSAFE_MS
      );
      stopStreamTracks();

      if (!mountedRef.current) return;

      setStatus("analyzing");

      const wavBlob = await withTimeout(
        convertRecordingToWav(browserBlob),
        ANALYSIS_FAILSAFE_MS,
        "Audio conversion timed out. Please try again."
      );
      const analysis = await withTimeout(
        analyzeAmbientAudio(token, wavBlob),
        ANALYSIS_FAILSAFE_MS,
        "Ambient analysis timed out. Please try again."
      );
      const nextResult = {
        ...analysis,
        browser_mime_type: browserBlob.type || "browser-default",
        uploaded_mime_type: "audio/wav",
        recorded_seconds: RECORDING_MS / 1000,
      };

      localStorage.setItem(AMBIENT_KEY, JSON.stringify(nextResult));
      if (!mountedRef.current) return;
      setResult(nextResult);
      setStatus("detected");
    } catch (err) {
      stopRecorder(recorderRef.current);
      stopStreamTracks();
      if (!mountedRef.current) return;
      setError(messageForError(err));
      setStatus("error");
    } finally {
      recorderRef.current = null;
    }
  };

  const isBusy = status === "listening" || status === "analyzing";
  const detected = status === "detected" && result?.analysis_used;

  return (
    <div className="ambient-container">
      <h1 className="ambient-title">Environmental Context</h1>

      <div className="ambient-card">
        <p className="ambient-copy">
          HearDrum can listen for about 4 seconds to identify your acoustic
          environment. The short sample is analyzed temporarily and is not saved.
        </p>

        <div className={`ambient-status ambient-status-${status}`}>
          {status === "idle" && "Ready to analyze"}
          {status === "listening" && "Listening..."}
          {status === "analyzing" && "Analyzing..."}
          {status === "detected" && "Environment detected"}
          {status === "error" && "Analysis unavailable"}
        </div>

        {detected && (
          <div className="ambient-result">
            <div>
              <span>Detected environment</span>
              <strong>{result.environment_label}</strong>
            </div>
            <div>
              <span>Model confidence</span>
              <strong>{formatConfidence(result.confidence)}</strong>
            </div>
            <p>{result.context?.message}</p>
          </div>
        )}

        {error && <p className="ambient-error">{error}</p>}

        <div className="ambient-actions">
          {!detected && (
            <button
              type="button"
              className="ambient-primary motion-btn"
              onClick={analyze}
              disabled={isBusy}
            >
              {isBusy ? "Please wait..." : "Analyze with Microphone"}
            </button>
          )}

          {detected && (
            <button
              type="button"
              className="ambient-primary motion-btn"
              onClick={continueToResults}
            >
              Continue
            </button>
          )}

          {status === "error" && (
            <button
              type="button"
              className="ambient-secondary motion-btn"
              onClick={analyze}
            >
              Retry
            </button>
          )}

          <button
            type="button"
            className="ambient-secondary motion-btn"
            onClick={skip}
            disabled={isBusy}
          >
            Skip
          </button>
        </div>
      </div>
    </div>
  );
}

function recordForDuration(recorder, mimeType, durationMs, failsafeMs) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let settled = false;
    let stopTimer = null;
    let failsafeTimer = null;

    const cleanup = () => {
      window.clearTimeout(stopTimer);
      window.clearTimeout(failsafeTimer);
      recorder.removeEventListener("dataavailable", handleData);
      recorder.removeEventListener("stop", handleStop);
      recorder.removeEventListener("error", handleError);
    };

    const finish = () => {
      if (settled) return;
      settled = true;
      cleanup();
      if (chunks.length === 0) {
        reject(new Error("No microphone audio was captured."));
        return;
      }
      resolve({
        browserBlob: new Blob(chunks, {
          type: recorder.mimeType || mimeType || "audio/webm",
        }),
      });
    };

    const fail = (err) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(err instanceof Error ? err : new Error("Recording failed."));
    };

    function handleData(event) {
      if (event.data?.size > 0) chunks.push(event.data);
    }

    function handleStop() {
      finish();
    }

    function handleError(event) {
      fail(event.error || new Error("Recording failed."));
    }

    recorder.addEventListener("dataavailable", handleData);
    recorder.addEventListener("stop", handleStop);
    recorder.addEventListener("error", handleError);

    try {
      recorder.start(250);
    } catch (err) {
      fail(err);
      return;
    }

    stopTimer = window.setTimeout(() => {
      if (recorder.state === "inactive") {
        finish();
        return;
      }
      try {
        recorder.requestData?.();
        recorder.stop();
      } catch (err) {
        fail(err);
      }
    }, durationMs);

    failsafeTimer = window.setTimeout(() => {
      stopRecorder(recorder);
      fail(new Error("Microphone recording timed out. Please try again."));
    }, failsafeMs);
  });
}

function stopRecorder(recorder) {
  if (!recorder || recorder.state === "inactive") return;
  try {
    recorder.requestData?.();
    recorder.stop();
  } catch {
    // The recorder may already be stopping; cleanup still stops stream tracks.
  }
}

function withTimeout(promise, timeoutMs, message) {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error(message)), timeoutMs);
    promise.then(
      (value) => {
        window.clearTimeout(timer);
        resolve(value);
      },
      (err) => {
        window.clearTimeout(timer);
        reject(err);
      }
    );
  });
}

function messageForError(err) {
  if (err?.name === "NotAllowedError" || err?.name === "SecurityError") {
    return "Microphone permission was denied. You can retry or skip this step.";
  }
  if (err?.name === "NotFoundError") {
    return "No microphone was found. You can still continue without ambient analysis.";
  }
  if (err?.message) return err.message;
  return "Ambient analysis failed. You can retry or skip this step.";
}
