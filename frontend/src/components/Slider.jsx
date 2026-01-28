// src/components/Slider.jsx
import { useEffect, useState } from "react";
import "./slider.css";

const images = [
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/1e5becf441ad8ea50f63e8-hQCeK7sV7L0jJ2sQA8wyVJdC9XPIxC.webp",
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/124a48bb02faec1bdc5850-rZQuTo0Pm81U3S8DfEgJmxjy8qurYT.webp",
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/7a81053c9caf25aa886765-ff4mBM3L8GNul6kHGBbOMqOyqohvyc.webp",
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/2e87cbe71c67fc4b4b2e28-T95FkRFFYAoYYnpIY6iR8Vnfw8aY54.webp",
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/93d79acaf2deb9578fb9a3-RsD1WVrrRrAW41DgnIqBbmWqGfXAcK.webp",
  "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/Screenshot%202025-08-07%20at%2022.22.44-uV7XHPnKbgGjQPkGAPBKty1L5uHxeC.png",
];

export default function Slider() {
  const [cards, setCards] = useState([]);

  useEffect(() => {
    const newCards = images.map((img, index) => ({
      id: index + 1,
      imgSrc: img,
    }));
    setCards(newCards);

    const handleScroll = () => {
      const scrollPos = window.scrollY;
      const slider = document.querySelector(".slider");
      if (!slider) return;

      const initialTransform =
        "translate3d(-50%, -50%, 0) rotateX(0deg) rotateY(-25deg) rotateZ(-120deg)";
      const zOffset = scrollPos * 0.5;
      slider.style.transform = `${initialTransform} translateY(${zOffset}px)`;
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  const handleMouseOver = (e) => {
    e.currentTarget.style.left = "15%";
  };

  const handleMouseOut = (e) => {
    e.currentTarget.style.left = "0%";
  };

  return (
    <div className="slider" aria-label="3D image slider">
      {cards.map((card) => (
        <div
          key={card.id}
          className="card"
          onMouseOver={handleMouseOver}
          onMouseOut={handleMouseOut}
        >
          <img src={card.imgSrc} alt={`Image ${card.id}`} />
        </div>
      ))}
    </div>
  );
}
