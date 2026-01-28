import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bluetooth, Plug } from "lucide-react";
import "./ListeningType.css";

const OPTIONS = [
  {
    type: "wired",
    Icon: Plug,
    title: "Wired Headphones / Earphones",
    subtext: "Phone or laptop via cable. Volume is usually more consistent.",
  },
  {
    type: "bluetooth",
    Icon: Bluetooth,
    title: "Bluetooth Headphones / Earbuds",
    subtext: "Wireless listening. Volume can vary by codec, device, and settings.",
  },
];

export default function ListeningType() {
  const navigate = useNavigate();
  const [selectedType, setSelectedType] = useState(null);

  const choose = (type) => {
    setSelectedType(type);
    localStorage.setItem("listeningType", type);
    navigate("/brand");
  };

  return (
    <div className="listening-page">
      <h1 className="listening-title">How are you listening?</h1>

      <div className="listening-choices">
        {OPTIONS.map(({ type, Icon, title, subtext }) => {
          const isSelected = selectedType === type;
          return (
            <button
              key={type}
              type="button"
              onClick={() => choose(type)}
              className={`choice-card${isSelected ? " is-selected" : ""}`}
              aria-pressed={isSelected}
            >
              <span className="choice-icon" aria-hidden="true">
                <Icon size={28} strokeWidth={2.25} />
              </span>

              <span className="choice-content">
                <span className="choice-title-row">
                  <span className="choice-title">{title}</span>
                </span>
                <span className="choice-subtext">{subtext}</span>
              </span>

              <span className="choice-check" aria-hidden="true">
                ?
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}