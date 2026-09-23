from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import meetings, tasks, calendar, users, auth
from app.services.live_transcriber import process_audio_stream, manager
import os

from app.database import engine, Base
import app.models

from sqlalchemy import text

# Ensure vector extension exists before creating tables
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MeetTrack API")

# Ensure upload directory exists on startup
os.makedirs(os.path.join(os.path.dirname(__file__), "uploads"), exist_ok=True)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_origin_regex=r"https://.*\.ngrok.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(meetings.router)
app.include_router(tasks.router)
app.include_router(calendar.router)
app.include_router(users.router)
app.include_router(auth.router)

@app.websocket("/api/bot/stream/{meeting_id}")
async def bot_audio_stream(websocket: WebSocket, meeting_id: str):
    await websocket.accept()
    await process_audio_stream(websocket, meeting_id)

@app.websocket("/api/meetings/stream/{meeting_id}")
async def frontend_transcript_stream(websocket: WebSocket, meeting_id: str):
    await manager.connect(websocket, meeting_id)
    try:
        while True:
            # Keep the connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, meeting_id)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "MeetTrack API is running."}
