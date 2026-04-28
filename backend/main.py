import os
import tempfile

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from .auth import (
    authenticate_user,
    create_session,
    create_user,
    delete_session,
    get_session_user,
)
from .logger import append_prediction, clear_history, read_history
from .model_loader import predict_emotion
from .storage import STORAGE_DIR


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
TEAM_FILE = os.path.join(BACKEND_DIR, "team.json")
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".oga", ".m4a", ".mp4", ".webm", ".weba"}
CONTENT_TYPE_EXTENSIONS = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/flac": ".flac",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/mp4": ".mp4",
}
MAX_AUDIO_BYTES = 5 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024

app = FastAPI(title="Speech Emotion Recognition API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class AuthRequest(BaseModel):
    username: str
    password: str


def _clean_username(username: str) -> str:
    return username.strip()


def _get_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Login required.")
    return authorization.removeprefix("Bearer ").strip()


def require_user(authorization: str | None = Header(default=None)) -> str:
    token = _get_bearer_token(authorization)
    username = get_session_user(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return username


def require_token(authorization: str | None = Header(default=None)) -> str:
    return _get_bearer_token(authorization)


def _audio_suffix(filename: str, content_type: str | None) -> str:
    suffix = os.path.splitext(filename)[1].lower()
    if suffix:
        return suffix

    content_type = (content_type or "").split(";")[0].strip().lower()
    return CONTENT_TYPE_EXTENSIONS.get(content_type, ".webm")


def _save_upload_file_limited(file: UploadFile, suffix: str) -> str:
    total_size = 0

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=STORAGE_DIR) as temp_audio:
        temp_path = temp_audio.name
        while chunk := file.file.read(UPLOAD_CHUNK_SIZE):
            total_size += len(chunk)
            if total_size > MAX_AUDIO_BYTES:
                temp_audio.close()
                os.remove(temp_path)
                raise HTTPException(status_code=413, detail="Audio file must be 5MB or smaller.")
            temp_audio.write(chunk)

    return temp_path


@app.get("/")
async def serve_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.post("/signup")
async def signup(payload: AuthRequest):
    username = _clean_username(payload.username)
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    created = await run_in_threadpool(create_user, username, payload.password)
    if not created:
        raise HTTPException(status_code=409, detail="Username already exists.")

    token = await run_in_threadpool(create_session, username)
    return {"token": token, "username": username}


@app.post("/login")
async def login(payload: AuthRequest):
    username = _clean_username(payload.username)
    is_valid = await run_in_threadpool(authenticate_user, username, payload.password)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = await run_in_threadpool(create_session, username)
    return {"token": token, "username": username}


@app.post("/logout")
async def logout(token: str = Depends(require_token)):
    await run_in_threadpool(delete_session, token)
    return {"message": "Logged out"}


@app.post("/predict")
async def predict(file: UploadFile = File(...), username: str = Depends(require_user)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please upload an audio file.")

    suffix = _audio_suffix(file.filename, file.content_type)
    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload or record a WAV, MP3, FLAC, OGG, M4A, MP4, or WEBM file.",
        )

    temp_path = None
    try:
        temp_path = await run_in_threadpool(_save_upload_file_limited, file, suffix)
        result = await run_in_threadpool(predict_emotion, temp_path)
        await run_in_threadpool(
            append_prediction,
            username,
            file.filename,
            result["emotion"],
            result["confidence"],
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc
    finally:
        await file.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.get("/team")
async def get_team(username: str = Depends(require_user)):
    if not os.path.exists(TEAM_FILE):
        raise HTTPException(status_code=404, detail="Team data not found.")
    return FileResponse(TEAM_FILE, media_type="application/json")


@app.get("/history")
async def get_history(
    sort: str = Query(default="desc", pattern="^(asc|desc)$"),
    username: str = Depends(require_user),
):
    return await run_in_threadpool(read_history, username, sort)


@app.delete("/history")
async def delete_history(username: str = Depends(require_user)):
    await run_in_threadpool(clear_history, username)
    return {"message": "History cleared"}
