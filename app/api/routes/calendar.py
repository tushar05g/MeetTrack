import os
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Meeting, MeetingParticipant, MeetingStatus

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

router = APIRouter(prefix="/calendar", tags=["calendar"])

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
TOKEN_FILE = 'token.json'

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_client_config():
    return {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8000/calendar/callback"]
        }
    }

# Global variable to store the OAuth flow state between the /auth and /callback requests
auth_flow = None

@router.get("/auth")
def auth_google_calendar():
    global auth_flow
    if not os.getenv("GOOGLE_CLIENT_ID"):
        return {"status": "missing_credentials", "message": "GOOGLE_CLIENT_ID not set"}

    # Fix: Allow http for oauthlib during local development
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    auth_flow = Flow.from_client_config(get_client_config(), scopes=SCOPES)
    auth_flow.redirect_uri = "http://localhost:8000/calendar/callback"
    
    auth_url, _ = auth_flow.authorization_url(prompt='consent')
    return RedirectResponse(url=auth_url)

@router.get("/callback")
def calendar_callback(code: str):
    global auth_flow
    if not auth_flow:
        return {"status": "error", "message": "Auth flow session expired. Please click Connect Google Calendar again."}
        
    try:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        auth_flow.fetch_token(code=code)
        
        creds = auth_flow.credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
        return RedirectResponse(url="http://localhost:5173/upload?calendar=connected")
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/fetch_upcoming")
def fetch_upcoming_meeting(db: Session = Depends(get_db)):
    if not os.path.exists(TOKEN_FILE):
        return {"status": "missing_credentials", "instructions": "Please click 'Connect Google Calendar' first to log in."}
        
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=10, singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return {"status": "error", "message": "No upcoming events found."}
            
        # Find first event with a Google Meet link
        target_event = None
        for event in events:
            if 'hangoutLink' in event:
                target_event = event
                break
                
        if not target_event:
            return {"status": "error", "message": "None of your upcoming events have a Google Meet link attached."}
            
        meet_url = target_event['hangoutLink']
        attendees = target_event.get('attendees', [])
        
        # Get start time if available
        start_time = None
        if 'start' in target_event and 'dateTime' in target_event['start']:
            start_time = target_event['start']['dateTime']
        
        # Save to DB
        meeting = Meeting(
            title=f"Calendar Sync: {target_event.get('summary', 'Untitled')}",
            audio_file_path="", 
            status=MeetingStatus.pending
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        
        saved_attendees = []
        for attendee in attendees:
            email = attendee.get('email', '')
            name = attendee.get('displayName', email.split('@')[0])
            if email:
                mp = MeetingParticipant(meeting_id=meeting.id, name=name, email=email)
                db.add(mp)
                saved_attendees.append({"name": name, "email": email})
        db.commit()
        
        return {
            "status": "ok",
            "meet_url": meet_url,
            "meeting_id": meeting.id,
            "attendees": saved_attendees,
            "start_time": start_time
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Error fetching from calendar: {str(e)}"}
