import { useEffect } from "react";
import { Link } from "react-router-dom";
import logo from "../assets/heardrum.png";

export default function Layout({ children }) {
  useEffect(() => {
    const ALERT_KEY = "safeAlertedAt";
    const END_KEY = "safeEndAt";
    const TAB_FLAG = "safeAlertShownThisTab";

    let audioCtx = null;
    const ensureAudioCtx = () => {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return null;
      if (!audioCtx) audioCtx = new AudioCtx();
      if (audioCtx.state === "suspended") {
        audioCtx.resume().catch(() => {});
      }
      return audioCtx;
    };

    const unlockAudio = () => {
      ensureAudioCtx();
      window.removeEventListener("pointerdown", unlockAudio);
      window.removeEventListener("keydown", unlockAudio);
    };

    window.addEventListener("pointerdown", unlockAudio, { once: true });
    window.addEventListener("keydown", unlockAudio, { once: true });

    const playAlertBeep = () => {
      try {
        const ctx = ensureAudioCtx();
        if (!ctx) return;

        const beep = (startTime, freq) => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = "sine";
          osc.frequency.value = freq;
          gain.gain.value = 0.28;
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(startTime);
          osc.stop(startTime + 0.28);
        };

        const t0 = ctx.currentTime + 0.02;
        beep(t0, 880);
        beep(t0 + 0.34, 988);
        beep(t0 + 0.68, 784);

        if (navigator.vibrate) {
          navigator.vibrate([200, 120, 200, 120, 260]);
        }

      } catch {
        // Ignore audio errors (autoplay policies, etc.)
      }
    };

    const maybeAlert = () => {
      if (sessionStorage.getItem(TAB_FLAG) === "1") return;
      const endAt = Number(localStorage.getItem(END_KEY));
      const alertedAt = Number(localStorage.getItem(ALERT_KEY));
      if (!Number.isFinite(endAt) || endAt <= 0) return;
      if (Number.isFinite(alertedAt) && alertedAt >= endAt) {
        sessionStorage.setItem(TAB_FLAG, "1");
        playAlertBeep();
        alert("Safe listening time reached. Please take a break.");
      }
    };

    const onStorage = (e) => {
      if (e.key === ALERT_KEY || e.key === END_KEY) maybeAlert();
    };

    const interval = setInterval(maybeAlert, 5000);
    window.addEventListener("storage", onStorage);
    maybeAlert();
    return () => {
      clearInterval(interval);
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("pointerdown", unlockAudio);
      window.removeEventListener("keydown", unlockAudio);
    };
  }, []);

  return (
    <>
      <header className="header">
        <Link to="/">
          <img src={logo} alt="HearDrum Logo" className="logo" />
        </Link>

        <nav className="navbar">
          <Link to="/how-it-works">How it works</Link>
          <Link to="/about-us">About us</Link>
          <Link to="/contact">Contact</Link>
        </nav>
      </header>

      <main className="page-container">{children}</main>
    </>
  );
}
