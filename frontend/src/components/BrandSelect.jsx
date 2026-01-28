import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./BrandSelect.css";
import { getHeadphoneBrands } from "../api";

export default function BrandSelect() {
  const [brands, setBrands] = useState([]);
  const [search, setSearch] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const listeningType = localStorage.getItem("listeningType");

  useEffect(() => {
    if (!listeningType) {
      navigate("/listening-type");
      return;
    }

    let isMounted = true;

    (async () => {
      try {
        const data = await getHeadphoneBrands(listeningType);
        if (!isMounted) return;
        setBrands(data.brands);
        setLoading(false);
      } catch (err) {
        console.error(err);
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [listeningType, navigate]);

  const filteredBrands = brands.filter((b) =>
    b.toLowerCase().includes(search.toLowerCase())
  );

  const selectBrand = (brand) => {
    localStorage.setItem("selectedBrand", brand);
    setShowDropdown(false);
    navigate("/model");
  };

  if (loading) return <p style={{ color: "white" }}>Loading brands...</p>;

  return (
    <div className="brand-select-container brand-page-wrapper">
      <h1 className="brand-select-title">Select Your Headphone Brand</h1>

      <input
        type="text"
        placeholder="Search brand..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setShowDropdown(true);
        }}
        onFocus={() => setShowDropdown(true)}
        className="brand-input"
      />

      {/* DROPDOWN */}
      {showDropdown && (
        <div className="brand-dropdown">
          {filteredBrands.length === 0 && (
            <p className="no-results">No brands found</p>
          )}

          {filteredBrands.map((brand) => (
            <div
              key={brand}
              className="brand-item"
              onClick={() => selectBrand(brand)}
            >
              {brand}
            </div>
          ))}
        </div>
      )}

      {/* CLICK-OUTSIDE OVERLAY — NOW SCOPED TO BRAND PAGE ONLY */}
      {showDropdown && (
        <div
          className="brand-select-overlay"
          onClick={() => setShowDropdown(false)}
        ></div>
      )}
    </div>
  );
}
