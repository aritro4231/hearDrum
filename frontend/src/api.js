const API = import.meta.env.VITE_API_BASE_URL;

export async function getHeadphones() {
  const res = await fetch(`${API}/api/headphones/`);
  if (!res.ok) throw new Error("Failed to load headphones");
  return res.json();
}

export async function getHeadphoneBrands(listeningType) {
  const type = encodeURIComponent(listeningType ?? "");
  const res = await fetch(`${API}/api/headphones/brands/?type=${type}`);
  if (!res.ok) throw new Error("Failed to load headphone brands");
  return res.json();
}

export async function getHeadphoneModels(brand, listeningType) {
  const encodedBrand = encodeURIComponent(brand ?? "");
  const type = encodeURIComponent(listeningType ?? "");
  const res = await fetch(
    `${API}/api/headphones/?brand=${encodedBrand}&type=${type}`
  );
  if (!res.ok) throw new Error("Failed to load headphone models");
  return res.json();
}
