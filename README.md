# Speech Emotion Recognition Web App

A deploy-ready Speech Emotion Recognition (SER) dashboard built with FastAPI, Hugging Face Transformers, SQLite authentication, per-user prediction logs, and a dark HTML/Tailwind/JavaScript frontend.

The app uses the pretrained model `superb/wav2vec2-base-superb-er`, so no training step is required.

## Features

- Login and signup with hashed passwords
- Audio upload and browser recording
- Emotion prediction with confidence score
- User-specific prediction history
- Metrics and About pages for demo presentation
- FastAPI serves both the API and frontend

## Project Structure

```text
ser-app/
|-- backend/
|   |-- __init__.py
|   |-- auth.py
|   |-- main.py
|   |-- model_loader.py
|   |-- logger.py
|   |-- storage.py
|   |-- team.json
|   `-- requirements.txt
|-- frontend/
|   |-- index.html
|   |-- script.js
|   `-- style.css
|-- start.sh
|-- .gitignore
|-- local_data/
`-- README.md
```

On Render, user data is stored on the mounted disk at `/data`. During local development, the app falls back to `local_data/`.

Persistent files are created automatically:

```text
/data/database.db
/data/logs.csv
```

Local fallback:

```text
local_data/database.db
local_data/logs.csv
```

## Run Locally

```bash
cd ser-app
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

The first startup may take longer because the Hugging Face model downloads and caches locally. After that, the model is loaded once in memory when FastAPI starts.

## Render Deployment

1. Push the project to GitHub.
2. Go to the Render dashboard.
3. Create a new Web Service.
4. Connect your GitHub repository.
5. Set the root directory to `ser-app` if your repository contains other folders.
6. Add a Render Disk and mount it at:

```text
/data
```

7. Use these commands:

```text
Build Command: pip install -r backend/requirements.txt
Start Command: bash start.sh
```

Render automatically provides the `PORT` environment variable used by `start.sh`. The app stores SQLite users and prediction logs on `/data`, so they survive redeploys and restarts.

## API Summary

- `POST /signup` creates a user account.
- `POST /login` returns a bearer token.
- `POST /logout` removes the current session.
- `POST /predict` accepts uploaded or recorded audio and returns emotion plus confidence.
- `GET /team` returns batch and team member names.
- `GET /history?sort=desc` returns the logged-in user's prediction history.
- `DELETE /history` clears only the logged-in user's history.

## Notes

- WAV files are preferred, but the backend also accepts MP3, FLAC, OGG, M4A, MP4, WEBM, and WEBA when the runtime audio libraries can decode them.
- Browser recordings are usually sent as WebM, OGG, or MP4 blobs.
- No hardcoded port is used in production; Render supplies `$PORT`.
