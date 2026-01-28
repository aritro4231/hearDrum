import { Github, Mail } from "lucide-react";
import "./Contact.css";

function DiscordIcon({ size = 22 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M20.317 4.369a19.91 19.91 0 0 0-4.885-1.515.074.074 0 0 0-.078.037c-.211.375-.444.864-.608 1.249a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.249.077.077 0 0 0-.078-.037 19.86 19.86 0 0 0-4.885 1.515.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.056 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.105 13.08 13.08 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.009c.12.098.246.195.373.293a.077.077 0 0 1-.006.127 12.3 12.3 0 0 1-1.873.892.076.076 0 0 0-.04.106c.36.698.772 1.363 1.225 1.993a.076.076 0 0 0 .084.028 19.88 19.88 0 0 0 6.002-3.03.077.077 0 0 0 .032-.056c.5-5.177-.838-9.674-3.548-13.66a.061.061 0 0 0-.031-.028ZM8.02 15.331c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.418 2.157-2.418 1.211 0 2.175 1.094 2.157 2.418 0 1.334-.955 2.419-2.157 2.419Zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.418 2.157-2.418 1.211 0 2.175 1.094 2.157 2.418 0 1.334-.946 2.419-2.157 2.419Z" />
    </svg>
  );
}

const CONTACTS = [
  {
    label: "Email",
    value: "aritro@vt.edu",
    href: "mailto:aritro@vt.edu",
    Icon: Mail,
  },
  {
    label: "GitHub",
    value: "github.com/aritro4231",
    href: "https://github.com/aritro4231",
    Icon: Github,
  },
  {
    label: "Discord",
    value: "pogothecreator",
    href: "https://discord.com/users/505322546292457504",
    Icon: DiscordIcon,
  },
];

export default function Contact() {
  return (
    <section className="contact-section">
      <div className="contact-inner">
        <div className="contact-heading">
          <h2 className="contact-title">Contact</h2>
          <p className="contact-subtitle">
            Please feel free to reach out! I would love to connect.
          </p>
        </div>

        <div className="contact-grid">
          {CONTACTS.map(({ label, value, href, Icon }) => {
            const isExternal = href.startsWith("http");
            return (
              <a
                key={label}
                href={href}
                target={isExternal ? "_blank" : undefined}
                rel={isExternal ? "noopener noreferrer" : undefined}
                className="contact-card"
              >
                <span className="contact-icon" aria-hidden="true">
                  <Icon size={22} />
                </span>
                <span className="contact-meta">
                  <span className="contact-label">{label}</span>
                  <span className="contact-value">{value}</span>
                </span>
              </a>
            );
          })}
        </div>
      </div>
    </section>
  );
}