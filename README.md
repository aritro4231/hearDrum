# 🥁 hearDrum

**hearDrum** helps headphone users understand how loud they're actually listening, and how long that volume is safe to sustain using the National Institute for Occupational Safety and Health's (NIOSH) noise exposure guidelines.

Pick your headphones, set your volume, and hearDrum estimates your real-world output in dB SPL and counts down your safe listening window before it recommends a break.

🔗 **Live demo:** [heardrum.vercel.app](https://heardrum.vercel.app)

---

## How it works

1. **Choose your connection type** — wired or Bluetooth.
2. **Select your headphone brand and model** from a database of real headphone specs.
3. **Adjust the volume slider** — hearDrum estimates your output in dB SPL based on that headphone's published maximum output level.
4. **Get your safe listening time**, calculated with the NIOSH Recommended Exposure Limit (85 dB = 8 hours, with exposure time halving every +3 dB). A live countdown alerts you when it's time to take a break.

## Features

- 📋 Headphone database lookup by brand, model, and connection type (wired vs. Bluetooth)
- 🎚️ Real-time dB SPL estimation as you adjust volume
- ⏱️ NIOSH-based safe listening timer with break alerts
- 🌐 Clean multi-step React flow: listening type → brand → model → volume → results

## Tech Stack

**Frontend**
- React 19 + Vite
- React Router
- Lucide React (icons)

**Backend**
- Django 5 + Django REST Framework
- django-cors-headers
- SQLite (default Django dev DB)
- Gunicorn (production server)

## Project Structure

```
hearDrum/
├── backend/            # Django REST API
│   ├── backend/        # Project settings, URLs, WSGI/ASGI
│   └── core/           # App logic
│       ├── data/       # Headphone spec database (JSON)
│       ├── views.py    # API endpoints
│       └── utils.py    # Data loading helpers
├── frontend/           # React + Vite app
│   └── src/
│       └── components/ # Step-by-step UI flow
└── requirements.txt
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/devices/` | List available connection types (wired, Bluetooth) |
| `GET` | `/api/headphones/brands/?type=` | List headphone brands, optionally filtered by connection type |
| `GET` | `/api/headphones/?brand=&type=` | List headphone models for a given brand |

## Getting Started

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The API will be available at `http://localhost:8000/`.

### Frontend

```bash
cd frontend
npm install
```

Create a `.env` file in `frontend/` with:

```
VITE_API_BASE_URL=http://localhost:8000
```

Then start the dev server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173/`.


## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
