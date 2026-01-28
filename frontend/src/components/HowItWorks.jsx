import { useNavigate } from "react-router-dom";
import "./HowItWorks.css";

export default function HowItWorks() {
  const navigate = useNavigate();
  const navigateStyle = {
    display: "flex",
    justifyContent: "center",
    gap: "7px",
    flexWrap: "wrap",
    marginTop: "11px",
  };

  const primaryButtonStyle = {
    backgroundColor: "var(--spotify-green)",
    color: "black",
    border: "none",
    padding: "14px 28px",
    borderRadius: "40px",
    fontSize: "18px",
    fontWeight: 700,
    cursor: "pointer",
    transition: "0.2s ease",
  };

  const ctaPanelStyle = {
    marginTop: "56px",
    padding: "28px 24px",
    borderRadius: "20px",
    background:
      "linear-gradient(135deg, rgba(29,185,84,0.18), rgba(29,185,84,0.05))",
    border: "1px solid rgba(29, 185, 84, 0.35)",
    boxShadow: "0 16px 40px rgba(29, 185, 84, 0.12)",
    maxWidth: "900px",
    marginInline: "auto",
  };

  const subtitleStyle = {};

  const rowStyle = {
    display: "flex",
    justifyContent: "center",
    gap: "16px",
    flexWrap: "nowrap",
    marginTop: "28px",
    overflowX: "auto",
    paddingBottom: "6px",
  };

  const cardStyle = {
    background: "rgba(255, 255, 255, 0.04)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    borderRadius: "16px",
    padding: "20px 22px",
    width: "240px",
    boxShadow: "0 10px 30px rgba(0, 0, 0, 0.35)",
    backdropFilter: "blur(6px)",
  };

  const numberStyle = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: "36px",
    height: "36px",
    borderRadius: "999px",
    background: "rgba(29, 185, 84, 0.15)",
    color: "var(--spotify-green)",
    fontWeight: 700,
    border: "1px solid rgba(29, 185, 84, 0.35)",
    marginBottom: "10px",
  };

  const titleStyle = {
    fontSize: "17px",
    fontWeight: 700,
    marginBottom: "2px",
  };

  const textStyle = {
    color: "var(--gray)",
    fontSize: "14px",
    lineHeight: 1.6,
  };

  const nioshPanelStyle = {
    marginTop: "26px",
    padding: "18px 20px",
    borderRadius: "16px",
    background: "rgba(29, 185, 84, 0.08)",
    border: "1px solid rgba(29, 185, 84, 0.35)",
    boxShadow: "0 12px 32px rgba(29, 185, 84, 0.12)",
    maxWidth: "900px",
    marginInline: "auto",
  };

  const nioshBadgeStyle = {
    display: "inline-block",
    padding: "6px 12px",
    borderRadius: "999px",
    border: "1px solid rgba(29, 185, 84, 0.45)",
    color: "var(--spotify-green)",
    fontSize: "12px",
    fontWeight: 800,
    letterSpacing: "0.6px",
    marginBottom: "8px",
  };

  return (
    <div className="how-page">
      <h1 className="how-title">How It Works</h1>
      <p className="how-subtitle">
        Four quick steps to estimate how long you can listen before hearing risk rises.
      </p>

      <div style={rowStyle}>
        <div style={cardStyle}>
          <div style={numberStyle}>1</div>
          <div style={titleStyle}>Pick Wired or Bluetooth</div>
          <div style={textStyle}>Start by choosing how your headphones connect.</div>
        </div>

        <div style={cardStyle}>
          <div style={numberStyle}>2</div>
          <div style={titleStyle}>Choose Your Device</div>
          <div style={textStyle}>Select your brand and model to tailor the estimate.</div>
        </div>

        <div style={cardStyle}>
          <div style={numberStyle}>3</div>
          <div style={titleStyle}>Pick Your Volume</div>
          <div style={textStyle}>Tell us your typical listening level.</div>
        </div>

        <div style={cardStyle}>
          <div style={numberStyle}>4</div>
          <div style={titleStyle}>Get Your Safe Listening Time</div>
          <div style={textStyle}>
            We estimate how long you can listen before hearing loss risk increases.
          </div>
        </div>
      </div>

      <section style={nioshPanelStyle}>
        <div style={nioshBadgeStyle}>SCIENCE-BASED</div>
        <div style={{ fontSize: "18px", fontWeight: 800, marginBottom: "4px" }}>
          We calculate time using the NIOSH Recommended Exposure Limit
        </div>
        <div className="how-subtitle" style={{ marginTop: "2px" }}>
          Your estimated safe listening time is grounded in NIOSH exposure guidance, not guesswork.
        </div>
      </section>

      <section style={ctaPanelStyle}>
        <h3 style={{ fontSize: "26px", marginBottom: "8px" }}>Listen Longer. Worry Less.</h3>
        <p className="how-subtitle" style={{ marginBottom: "6px" }}>
          We estimate how long you can listen before hearing loss risk increases.
        </p>
        <div style={navigateStyle}>
          <button
            onClick={() => navigate("/listening-type")}
            style={primaryButtonStyle}
            onMouseOver={(e) => (e.currentTarget.style.opacity = "0.88")}
            onMouseOut={(e) => (e.currentTarget.style.opacity = "1")}
          >
            Get My Recommendation
          </button>
        </div>
      </section>
    </div>
  );
}
