import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./BrandSelect.css";
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

  const hasSpec = (value) => value != null && String(value).trim() !== "";

  const matchesListeningType = (model) => {
    const hasWired = hasSpec(model.max_dB_SPL_wired);
    const hasBluetooth = hasSpec(model.max_dB_SPL_bluetooth);
    const connection = (model.connection || "").toLowerCase();
    const isBoth = connection === "both";
    const isWireless = connection === "wireless";
    const isBluetooth = connection === "bluetooth" || isWireless;

    if (listeningType === "wired") {
      if (connection && connection !== "wired" && !isBoth) return false;
      return hasWired;
    }

    if (listeningType === "bluetooth") {
      if (connection && !isBluetooth && !isBoth) return false;
      return hasBluetooth;
    }

    return true;
  };

  const filteredModels = models
    .filter(matchesListeningType)
    .filter((model) => model.name.toLowerCase().includes(search.toLowerCase()));

  const selectModel = (model) => {
    localStorage.setItem("selectedModel", JSON.stringify(model));
    setShowDropdown(false);
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

      <div className={`brand-combobox${showDropdown ? " is-open" : ""}`}>
        <input
          type="text"
          placeholder="Search model..."
          value={search}
          onFocus={() => setShowDropdown(true)}
          onChange={(event) => {
            setSearch(event.target.value);
            setShowDropdown(true);
          }}
          className="brand-input"
          aria-expanded={showDropdown}
          aria-controls="model-dropdown"
        />

        {showDropdown && (
          <>
            <div
              className="brand-select-overlay"
              onClick={() => setShowDropdown(false)}
            ></div>

            <div className="brand-dropdown" id="model-dropdown" role="listbox">
              {filteredModels.length === 0 && (
                <p className="no-results">No models found</p>
              )}

              {filteredModels.map((model) => (
                <div
                  key={model.name}
                  className="brand-item"
                  role="option"
                  aria-selected="false"
                  onClick={() => selectModel(model)}
                >
                  {model.name}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
