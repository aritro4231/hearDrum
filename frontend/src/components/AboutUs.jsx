import "./AboutUs.css";
import pic1 from "../assets/personal_pic.jpeg";
import pic2 from "../assets/_MG_7648.JPG";

export default function AboutUs() {
  return (
    <div className="about-page">
      <h1 className="about-title">About Us</h1>

      <section className="about-card">
        <div className="about-left">
          <div className="about-photo-stack">
            <img className="about-photo" src={pic1} alt="Aritro Sengupta portrait" />
            <img className="about-photo" src={pic2} alt="Aritro Sengupta portrait" />
          </div>

          <div className="about-badges">
            <span className="about-badge">Virginia Tech</span>
            <span className="about-badge">CS Junior</span>
            <span className="about-badge">DJ / Producer</span>
          </div>
        </div>

        <div className="about-right">
          <div className="about-name">Aritro Sengupta</div>
          <div className="about-subtitle">Computer Science Junior at Virginia Tech</div>

          <p className="about-lead">
            I built HearDrum to solve a gap: most headphone brands, especially beyond Apple phones do not warn you when you exceed safe listening levels.
          </p>

          <ul className="about-bullets">
            <li>I wanted equal hearing care across brands, devices, and even on PC.</li>
            <li>As a DJ and producer, protecting my ears is personal and non-negotiable.</li>
            <li>This app turns safe listening science into something people can actually use.</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
