from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import meetings, tasks, calendar

app = FastAPI(title="MeetTrack API")

# Setup CORS to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow any frontend (like Vercel) to connect
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(meetings.router)
app.include_router(tasks.router)
app.include_router(calendar.router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "MeetTrack API is running."}
