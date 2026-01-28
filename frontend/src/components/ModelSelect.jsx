import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./BrandSelect.css"; // reusing styles
import { getHeadphoneModels } from "../api";

export default function ModelSelect() {
  const [models, setModels] = useState([]);
  const [search, setSearch] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(true);

  const navigate = useNavigate();
  const brand = localStorage.getItem("selectedBrand");
  const listeningType = localStorage.getItem("listeningType");

  useEffect(() => {
    if (!listeningType) {
      navigate("/listening-type");
      return;
    }

    if (!brand) {
      // if no brand, send back to brand page
      navigate("/brand");
      return;
    }

    let isMounted = true;

    (async () => {
      try {
        const data = await getHeadphoneModels(brand, listeningType);
        if (!isMounted) return;
        setModels(data.models || []);
        setLoading(false);
      } catch (err) {
        console.error(err);
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [brand, listeningType, navigate]);

  const matchesListeningType = (m) => {
    const hasWired = m.max_dB_SPL_wired != null;
    const hasBluetooth = m.max_dB_SPL_bluetooth != null;
    const connection = (m.connection || "").toLowerCase();
    const isWireless = connection === "wireless";
    const isBluetooth = connection === "bluetooth" || isWireless;

    if (listeningType === "wired") {
      if (connection && connection !== "wired") return false;
      return hasWired;
    }

    if (listeningType === "bluetooth") {
      if (connection && !isBluetooth) return false;
      return hasBluetooth;
    }

    return true;
  };

  const modelsForType = models.filter(matchesListeningType);

  const filteredModels = modelsForType.filter((m) =>
    m.name.toLowerCase().includes(search.toLowerCase())
  );

  const selectModel = (model) => {
    // just store the model and go to volume
    localStorage.setItem("selectedModel", JSON.stringify(model));
    navigate("/volume");
  };

  if (loading) {
    return <p style={{ color: "white" }}>Loading models...</p>;
  }

  return (
    <div className="brand-select-container">
      <h1 className="brand-select-title">Select Your Model</h1>

      <p style={{ color: "var(--spotify-green)", marginBottom: "20px" }}>
        Brand: <b>{brand}</b>
      </p>

      <input
        type="text"
        placeholder="Search model..."
        value={search}
        onFocus={() => setShowDropdown(true)}
        onChange={(e) => {
          setSearch(e.target.value);
          setShowDropdown(true);
        }}
        className="brand-input"
      />

      {showDropdown && (
        <div className="brand-dropdown">
          {filteredModels.length === 0 && (
            <p className="no-results">No models found</p>
          )}

          {filteredModels.map((model) => (
            <div
              key={model.name}
              className="brand-item"
              onClick={() => selectModel(model)}
            >
              {model.name}
            </div>
          ))}
        </div>
      )}

      {showDropdown && (
        <div
          className="brand-select-overlay"
          onClick={() => setShowDropdown(false)}
        ></div>
      )}
    </div>
  );
}
