import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();

  const start = () => {
    navigate("/listening-type");
  };

  const heroTitleStyle = {
    color: "var(--spotify-green)",
    fontSize: "42px",
    marginBottom: "14px",
    position: "relative",
    zIndex: 1,
    whiteSpace: "nowrap",
  };

  const heroSubtitleStyle = {
    color: "var(--gray)",
    fontSize: "18px",
    marginBottom: "28px",
    position: "relative",
    zIndex: 1,
    maxWidth: "720px",
    marginInline: "auto",
    lineHeight: 1.6,
  };

  const sectionStyle = {
    marginTop: "56px",
    position: "relative",
    zIndex: 1,
  };

  const cardRowStyle = {
    display: "flex",
    justifyContent: "center",
    gap: "16px",
    flexWrap: "wrap",
    marginTop: "18px",
  };

  const cardStyle = {
    background: "rgba(255, 255, 255, 0.04)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    borderRadius: "16px",
    padding: "18px 20px",
    width: "240px",
    textAlign: "center",
    boxShadow: "0 10px 30px rgba(0, 0, 0, 0.35)",
    backdropFilter: "blur(6px)",
  };

  const cardTitleStyle = {
    color: "var(--white)",
    fontSize: "16px",
    fontWeight: 600,
    marginBottom: "6px",
  };

  const cardTextStyle = {
    color: "var(--gray)",
    fontSize: "14px",
    lineHeight: 1.6,
  };

  const secondaryButtonStyle = {
    backgroundColor: "transparent",
    color: "var(--white)",
    border: "1px solid rgba(255, 255, 255, 0.18)",
    padding: "14px 22px",
    borderRadius: "40px",
    fontSize: "16px",
    fontWeight: 600,
    cursor: "pointer",
    transition: "0.2s ease",
    position: "relative",
    zIndex: 1,
  };

  const primaryButtonStyle = {
    backgroundColor: "var(--spotify-green)",
    color: "black",
    border: "none",
    padding: "16px 32px",
    borderRadius: "40px",
    fontSize: "20px",
    fontWeight: 700,
    cursor: "pointer",
    transition: "0.2s ease",
    position: "relative",
    zIndex: 1,
  };

  const ctaPanelStyle = {
    marginTop: "64px",
    padding: "28px 24px",
    borderRadius: "20px",
    background:
      "linear-gradient(135deg, rgba(29,185,84,0.18), rgba(29,185,84,0.05))",
    border: "1px solid rgba(29, 185, 84, 0.35)",
    boxShadow: "0 16px 40px rgba(29, 185, 84, 0.12)",
    maxWidth: "780px",
    marginInline: "auto",
  };

  const demoPanelStyle = {
    ...ctaPanelStyle,
    marginTop: "52px",
    maxWidth: "860px",
  };

  const demoSliderWrapStyle = {
    marginTop: "18px",
    background: "rgba(255, 255, 255, 0.04)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    borderRadius: "16px",
    padding: "18px 18px 16px 18px",
  };

  const demoRangeStyle = {
    width: "100%",
    accentColor: "var(--spotify-green)",
    cursor: "pointer",
  };

  const demoResultStyle = {
    marginTop: "14px",
    fontSize: "18px",
    fontWeight: 700,
    color: "var(--white)",
  };

  const demoHintStyle = {
    ...cardTextStyle,
    marginTop: "6px",
  };

  const volumeToSafeMinutes = (vol) => {
    const maxMinutes = 480;
    const minMinutes = 15;
    const normalized = (vol - 10) / 90;
    const eased = Math.min(1, Math.max(0, normalized ** 1.6));
    const minutes = Math.round(maxMinutes - (maxMinutes - minMinutes) * eased);
    return minutes;
  };

  const [demoVolume, setDemoVolume] = useState(60);
  const demoSafeMinutes = volumeToSafeMinutes(demoVolume);
  return (
    <div
      style={{
        textAlign: "center",
        marginTop: "40px",
        position: "relative",
        minHeight: "100vh",
        paddingBottom: "80px",
      }}
    >
      <section>
        <h1 style={heroTitleStyle}>Keep Your Music Loud and Your Hearing Safe!</h1>

        <p style={heroSubtitleStyle}>
          HearDrum gives you tailored listening insight based on how you listen and what you use -
          so your safe time estimate actually fits you.
        </p>

        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: "12px",
            flexWrap: "wrap",
            marginBottom: "22px",
          }}
        >
          <button
            onClick={start}
            style={primaryButtonStyle}
            className="motion-btn motion-btn-primary"
            onMouseOver={(e) => (e.currentTarget.style.opacity = "0.88")}
            onMouseOut={(e) => (e.currentTarget.style.opacity = "1")}
          >
            Get Started
          </button>

          <button
            onClick={() => navigate("/how-it-works")}
            style={secondaryButtonStyle}
            className="motion-btn"
            onMouseOver={(e) => {
              e.currentTarget.style.borderColor = "rgba(29, 185, 84, 0.5)";
              e.currentTarget.style.color = "var(--spotify-green)";
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.18)";
              e.currentTarget.style.color = "var(--white)";
            }}
          >
            How It Works
          </button>
        </div>

      </section>

      <section style={sectionStyle}>
        <div style={demoPanelStyle} className="motion-card motion-delay-1">
          <h2 style={{ fontSize: "26px", marginBottom: "6px" }}>Take a quick glimpse at what’s safe</h2>
          <p style={{ ...cardTextStyle, maxWidth: "760px", margin: "0 auto" }}>
            Drag the slider for a quick estimate. Click on Get Started above to get tailored insights!
          </p>

          <div style={demoSliderWrapStyle}>
            <div style={{ ...cardTextStyle, marginBottom: "8px" }}>
              Volume: <strong style={{ color: "var(--white)" }}>{demoVolume}%</strong>
            </div>
            <input
              type="range"
              min="10"
              max="100"
              step="1"
              value={demoVolume}
              onChange={(e) => setDemoVolume(Number(e.target.value))}
              style={demoRangeStyle}
            />

            <div style={demoResultStyle}>Estimated safe time: {demoSafeMinutes} minutes</div>
            <div style={demoHintStyle}>
              Tailored insight comes from wired vs Bluetooth, your device model, and your volume.
            </div>
          </div>
        </div>
      </section>

    </div>
  );
}
