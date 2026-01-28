import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./VolumeSelect.css";

export default function VolumeSelect() {
  const navigate = useNavigate();
  const modelData = JSON.parse(localStorage.getItem("selectedModel") || "null");
  const listeningType = localStorage.getItem("listeningType");

  if (!modelData || !listeningType) {
    return (
      <p style={{ color: "white", marginTop: "40px" }}>
        Missing setup info. Please go back to Home and start again.
      </p>
    );
  }

  const connection = listeningType;
  const maxDb =
    connection === "wired"
      ? modelData.max_dB_SPL_wired
      : modelData.max_dB_SPL_bluetooth;

  const extractFirstNumber = (value) => {
    if (value == null) return NaN;
    const match = String(value).match(/-?\d+(\.\d+)?/);
    return match ? Number(match[0]) : NaN;
  };

  const [volume, setVolume] = useState(50);
  const [saved, setSaved] = useState(false);

  const numericMax = extractFirstNumber(maxDb);
  const safeNumericMax = Number.isFinite(numericMax) ? numericMax : 0;
  const estimatedDb = Math.round((volume / 100) * safeNumericMax);

  const saveVolume = () => {
    localStorage.setItem("listeningVolume", String(volume));
    localStorage.setItem("estimatedDb", String(estimatedDb));
    setSaved(true);
    navigate("/results");
  };

  return (
    <div className="volume-container">
      <h1 className="volume-title">Adjust Your Listening Volume</h1>

      <p className="volume-info">
        Model: <b>{modelData.name}</b>
      </p>

      

      <p className="volume-info">
        Max Output Level: <b className="volume-highlight">{maxDb}</b>
      </p>

      <div className="volume-slider-container">
        <p>
          Volume: <b>{volume}%</b>
        </p>

        <input
          type="range"
          min="0"
          max="100"
          value={volume}
          onChange={(e) => {
            setVolume(Number(e.target.value));
            setSaved(false);
          }}
          className="volume-slider"
        />
      </div>

      <p className="estimated-db">
        Estimated Output:{" "}
        <b className="volume-highlight">{estimatedDb} dB SPL</b>
      </p>

      <button type="button" className="next-button" onClick={saveVolume}>
        Next
      </button>

      {saved && (
        <p className="volume-info" style={{ marginTop: "12px" }}>
          Volume saved. Continue to the next step.
        </p>
      )}
    </div>
  );
}
