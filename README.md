# 🎧 hearDrum

hearDrum is a headphone listening tracker with a NIOSH-based exposure estimate and an optional ambient sound classifier. Choose a headphone model and volume setting, then track listening time and estimated exposure across sessions.

The app estimates output from a volume slider and bundled profiles. It does not measure sound pressure at the ear or establish a calibrated A-weighted level. The countdown represents time to reach the modeled exposure allowance, rather than a guarantee of safe listening.

**Demo:** [heardrum.vercel.app](https://heardrum.vercel.app)

## Features

- Headphone lookup by brand, model, and wired or Bluetooth connection.
- Registration, login, and authenticated listening history.
- Persistent active, paused, and completed sessions; recovery of an unfinished session.
- Session exposure and daily totals, including totals above 100%.
- Optional classification of short ambient recordings into ten urban sound classes.

## Exposure calculation

The shared calculation lives in [backend/core/exposure.py](backend/core/exposure.py). It uses an 85 dB reference level, an eight-hour reference duration, and a 3 dB exchange rate:

```text
T(L) = 480 × 2^((85 − L) / 3) minutes
Session dose (%) = 100 × listening_seconds / (60 × T(L))
Daily dose (%) = sum of session doses
```

For an input interpreted as dBA, 85 gives eight hours, 88 gives four hours, and 91 gives two hours. Paused time is excluded. The constants and equation follow the [NIOSH occupational noise criterion](https://www.cdc.gov/niosh/noise/prevent/understand.html).

## Headphone data

Profiles are bundled as JSON and imported into the `Headphone` table using `python manage.py import_headphones`.

| Seed file | Entries | Unique names |
| --- | ---: | ---: |
| [headphones_database.json](backend/core/data/headphones_database.json) | 100 | 32 |
| [headphones_databasev2.json](backend/core/data/headphones_databasev2.json) | 217 | 146 |

The importer uses V2 and upserts by name. **146 unique headphone names** is the supported seed count, rather than 217 distinct models. AirPods Max appears 69 times; three other names have conflicting duplicate entries. Later entries overwrite earlier ones.

Of the 146 unique V2 profiles, **126 contain at least one value marked `(est.)`**. The seed provides no source URLs, per-value provenance, or documented estimation method. Treat it as a largely estimated catalog rather than verified published maximum output measurements. The seed count does not verify the deployed database count.

## Ambient model and evaluation

The PyTorch CNN uses log-mel spectrograms. The bundled checkpoint uses mono audio at 22,050 Hz, fitted to four seconds, with 64 mel bands. Preprocessing includes peak normalization and per-clip feature standardization. Classification identifies an acoustic scene; it does not measure ambient SPL.

Training uses [UrbanSound8K](https://urbansounddataset.weebly.com/urbansound8k.html): 8,732 excerpts across ten classes. The downloader points to [Zenodo record 1203745](https://zenodo.org/records/1203745) and checks the archive MD5.

| Split | Metadata folds | Clips |
| --- | --- | ---: |
| Training | 1–8 | 7,079 |
| Validation | 9 | 816 |
| Test | 10 | 837 |

[ml/train.py](ml/train.py) preserves these fold assignments and selects the checkpoint by validation accuracy. [ml/evaluate.py](ml/evaluate.py) evaluates fold 10. The local report records **655/837 correct: 78.2557%, rounded to 78.3%**. An audit reproduced this score using the current checkpoint and cached test features. Best validation accuracy is 77.8186%.

| Clip | Split | Source interval, seconds |
| --- | --- | --- |
| `180937-7-3-10.wav` | Training, fold 1 | 309.585–313.585 |
| `180937-4-1-12.wav` | Validation, fold 9 | 309.481–313.481 |

### Training and evaluation commands

Run from the repository root with the Python dependencies installed. Downloaded audio, feature caches, and reports are excluded from Git. Observe the dataset's license and attribution requirements.

```text
python -m ml.download_urbansound8k
python -m ml.cache_features --cache-dir data/urbansound8k_features_64
python -m ml.train --epochs 30 --batch-size 128 --feature-cache-dir data/urbansound8k_features_64
python -m ml.evaluate --feature-cache-dir data/urbansound8k_features_64
```

These training settings match the bundled checkpoint's recorded hyperparameters. Training replaces the default checkpoint when validation improves. Without `--feature-cache-dir`, training extracts audio features and applies waveform augmentation; the cached path does not apply that augmentation.

## Inference benchmark

[ml/benchmark_ambient_inference.py](ml/benchmark_ambient_inference.py) defaults to ten warmups and 100 measured iterations per path. P95 uses linear interpolation at rank `(n − 1) × 0.95` in sorted samples. Loading and warmup are excluded; model timing synchronizes CUDA when applicable.

```text
python -m ml.benchmark_ambient_inference --warmup 10 --runs 100
```

The local report recorded on September 30, 2026 used a Ryzen 9 7940HS CPU, eight PyTorch threads, and a repeated four-second, 48 kHz mono PCM16 synthetic sine-wave WAV:

| Path | Median | P95 |
| --- | ---: | ---: |
| Model forward pass and confidence extraction on precomputed features | 2.71 ms | 3.70 ms |
| Ambient service, including decoding and preprocessing | 6.83 ms | 8.00 ms |
| Direct DRF view benchmark | 8.94 ms | **14.29 ms** |

**14.3 ms is the direct view benchmark's P95.** It includes synthetic multipart request construction/parsing, permission handling, WAV decoding, preprocessing, inference, response mapping, and JSON rendering. Forced authentication excludes real token lookup and database authentication.

It excludes browser recording, network/upload latency, routing, middleware, server overhead, and checkpoint loading. Sequential runs do not establish production latency under concurrent load. Raw timing samples are not saved. The report's decode description says upload-wrapper construction is excluded, but the timed function includes it.

Evaluation, training, and benchmark reports are written under `ml/artifacts/`, which is ignored by Git. The reported artifacts exist locally but are not included in a fresh checkout.

## Authentication and session tracking

The backend uses Django users and DRF `TokenAuthentication`. Registration validates passwords and stores them through Django's password hashing. Login returns an existing token or creates one. Requests send `Authorization: Token <token>`; logout deletes the token.

History, lifecycle actions, and ambient analysis require authentication. Session queries and mutations are scoped to the authenticated user. A database constraint permits one active or paused session per user. Server timestamps track elapsed listening time and exclude paused intervals. Editing settings completes the session before starting another.

Current security and integrity limitations:

- The frontend stores tokens in `localStorage`, exposing them to successful same-origin script injection.
- Tokens have no expiry and are reused on login. Failed server logout can leave a token valid after local storage is cleared.
- No application rate limits are configured for login, registration, or inference.
- DRF token API views do not enforce CSRF; they use explicit authorization headers rather than cookie authentication. Django's CSRF middleware remains installed. Adding cookie authentication would require CSRF protection.
- There is no global authenticated permission default. Existing private endpoints have explicit checks; new undecorated API endpoints would be public.
- The backend has a predictable development secret fallback and does not configure HTTPS redirect, HSTS, or secure cookies. Production deployment must supply its secret and transport protections.
- Clients supply estimated dB and may submit historical durations. Lifecycle writes lack transaction/row locking, so concurrent actions can race. Session time tracks the app's active state, not independently detected playback.

## Stack and layout

- Frontend: React 19, Vite, React Router, and Lucide React.
- Backend: Django 5, Django REST Framework, PostgreSQL, django-cors-headers, and Gunicorn.
- Audio/ML: PyTorch, torchaudio, SciPy, soundfile, pandas, and scikit-learn.

```text
backend/
  backend/             Django settings and root URLs
  core/
    data/              Headphone JSON seeds
    exposure.py        Exposure and session lifecycle calculations
    ambient.py         Upload validation and ambient service
    ml/                Features, CNN, inference, and bundled checkpoint
    management/        Headphone import command
frontend/src/          React UI, API client, and authentication state
ml/                    Dataset, training, evaluation, and benchmark scripts
```

## Local setup

The backend defaults to PostgreSQL, not the bundled SQLite file. It accepts `DATABASE_URL` or the `DB_*`/`PG*` variables in [settings.py](backend/backend/settings.py). Create a local PostgreSQL database named `heardrum` before running migrations.

These commands use PowerShell. Supply your local database credentials. `DB_PORT` below overrides the code's default of 6767 with PostgreSQL's usual port of 5432. If `DATABASE_URL` is set, it takes precedence.

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DB_NAME = "heardrum"
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:DB_USER = "postgres"
$env:DB_PASSWORD = "your-local-database-password"
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(50))"
python manage.py migrate
python manage.py import_headphones
python manage.py runserver
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The development API defaults to `http://127.0.0.1:8000`. To override it, add `VITE_API_BASE_URL=http://localhost:8000` to `frontend/.env`. Vite normally serves the app at `http://localhost:5173`.

## API

| Method | Endpoint | Authentication | Purpose |
| --- | --- | --- | --- |
| GET | `/` | Public | Health response |
| POST | `/api/auth/register/` | Public | Create user and token |
| POST | `/api/auth/login/` | Public | Authenticate and return token |
| POST | `/api/auth/logout/` | Required | Delete token |
| GET | `/api/devices/` | Public | Connection types |
| GET | `/api/headphones/brands/?type=` | Public | Brands filtered by connection |
| GET | `/api/headphones/?brand=&type=` | Public | Models for a required brand |
| GET, POST | `/api/sessions/` | Required | List owned sessions or submit a historical session |
| GET | `/api/sessions/current/` | Required | Recover active or paused session |
| GET | `/api/sessions/today/` | Required | UTC daily summary |
| POST | `/api/sessions/start/` | Required | Start or recover unfinished session |
| POST | `/api/sessions/<id>/pause/` | Required | Pause owned session |
| POST | `/api/sessions/<id>/resume/` | Required | Resume owned session |
| POST | `/api/sessions/<id>/end/` | Required | Complete owned session |
| POST | `/api/sessions/<id>/edit/` | Required | Complete session and return settings |
| POST | `/api/ambient/analyze/` | Required | Classify WAV upload in the `audio` field |

## Development checks

```text
cd backend
python manage.py test core
```

Backend tests require a configured database and permission to create a test database.

```text
cd frontend
npm run lint
npm run build
```
