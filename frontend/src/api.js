const API =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

async function parseResponse(res) {
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const message =
      data?.detail ||
      data?.non_field_errors?.[0] ||
      data?.username?.[0] ||
      data?.password?.[0] ||
      "Request failed";
    throw new Error(message);
  }

  return data;
}

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

export async function registerUser(credentials) {
  const res = await fetch(`${API}/api/auth/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
  return parseResponse(res);
}

export async function loginUser(credentials) {
  const res = await fetch(`${API}/api/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
  return parseResponse(res);
}

export async function logoutUser(token) {
  const res = await fetch(`${API}/api/auth/logout/`, {
    method: "POST",
    headers: { Authorization: `Token ${token}` },
  });
  return parseResponse(res);
}

export async function getListeningSessions(token) {
  const res = await fetch(`${API}/api/sessions/`, {
    headers: { Authorization: `Token ${token}` },
  });
  return parseResponse(res);
}

export async function saveListeningSession(token, session) {
  const res = await fetch(`${API}/api/sessions/`, {
    method: "POST",
    headers: {
      Authorization: `Token ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(session),
  });
  return parseResponse(res);
}
