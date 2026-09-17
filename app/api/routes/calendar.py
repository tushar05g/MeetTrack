import os
import json
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from jose import jwt, JWTError

from app.database import SessionLocal
from app.models import Meeting, MeetingParticipant, MeetingStatus, User
from app.core.dependencies import get_current_user, get_db
from app.core.security import SECRET_KEY, ALGORITHM

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

router = APIRouter(prefix="/calendar", tags=["calendar"])

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
BOT_EMAIL = os.getenv("BOT_EMAIL", "meettrack-bot@gmail.com")

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

def get_calendar_service(user: User):
    """Returns an authenticated Google Calendar service for a specific user, or None if not connected."""
    if not user.google_calendar_token:
        return None
    try:
        creds = Credentials.from_authorized_user_info(user.google_calendar_token, SCOPES)
        return build('calendar', 'v3', credentials=creds)
    except Exception:
        return None

def invite_bot_to_event(service, event_id: str):
    """
    Patches a Google Calendar event to add the bot email as an attendee.
    """
    try:
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        attendees = event.get('attendees', [])
        
        bot_emails = [a['email'] for a in attendees]
        if BOT_EMAIL not in bot_emails:
            attendees.append({'email': BOT_EMAIL})
            service.events().patch(
                calendarId='primary',
                eventId=event_id,
                body={'attendees': attendees},
                sendUpdates='none'
            ).execute()
            print(f"[CALENDAR] Bot {BOT_EMAIL} added as guest to event {event_id}")
            return True
        return True
    except Exception as e:
        print(f"[CALENDAR] Failed to invite bot to event: {e}")
        return False

@router.get("/auth")
def auth_google_calendar(token: str = Query(...), redirect_to: str = Query("http://localhost:5173"), db: Session = Depends(get_db)):
    if not os.getenv("GOOGLE_CLIENT_ID"):
        return {"status": "missing_credentials", "message": "GOOGLE_CLIENT_ID not set"}

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    import urllib.parse
    import base64
    
    state_data = {"user_id": user.id, "redirect_to": redirect_to}
    state_str = base64.b64encode(json.dumps(state_data).encode()).decode()

    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "redirect_uri": "http://localhost:8000/calendar/callback",
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state_str,
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)

@router.get("/callback")
def calendar_callback(code: str, state: str, db: Session = Depends(get_db)):
    try:
        import base64
        state_data = json.loads(base64.b64decode(state.encode()).decode())
        user_id = int(state_data["user_id"])
        frontend_url = state_data.get("redirect_to", "http://localhost:5173")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "message": "User not found from OAuth state"}
            
        import requests
        data = {
            "code": code,
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": "http://localhost:8000/calendar/callback",
            "grant_type": "authorization_code"
        }
        resp = requests.post("https://oauth2.googleapis.com/token", data=data)
        if not resp.ok:
            return {"status": "error", "message": f"Token exchange failed: {resp.text}"}
            
        token_data = resp.json()
        
        creds_json = {
            "token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "scopes": SCOPES
        }
        
        user.google_calendar_token = creds_json
        db.commit()
            
        return RedirectResponse(url=f"{frontend_url}/upload?calendar=connected")
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/status")
def calendar_status(current_user: User = Depends(get_current_user)):
    """Check if Google Calendar is connected for the current user."""
    return {"connected": current_user.google_calendar_token is not None, "bot_email": BOT_EMAIL}

@router.get("/fetch_upcoming")
def fetch_upcoming_meeting(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = get_calendar_service(current_user)
    if not service:
        return {"status": "missing_credentials", "bot_email": BOT_EMAIL, "instructions": "Please click 'Connect Google Calendar' first to log in."}
        
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=10, singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return {"status": "error", "message": "No upcoming events found."}
            
        target_event = None
        for event in events:
            if 'hangoutLink' in event:
                target_event = event
                break
                
        if not target_event:
            return {"status": "error", "message": "None of your upcoming events have a Google Meet link attached."}
            
        meet_url = target_event['hangoutLink']
        event_id = target_event['id']
        attendees = target_event.get('attendees', [])
        
        start_time = None
        if 'start' in target_event and 'dateTime' in target_event['start']:
            start_time = target_event['start']['dateTime']
        
        bot_invited = invite_bot_to_event(service, event_id)
        
        meeting = Meeting(
            title=f"Calendar Sync: {target_event.get('summary', 'Untitled')}",
            audio_file_path="", 
            status=MeetingStatus.pending,
            owner_id=current_user.id
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        
        saved_attendees = []
        for attendee in attendees:
            email = attendee.get('email', '')
            name = attendee.get('displayName', email.split('@')[0])
            if email and email != BOT_EMAIL:
                mp = MeetingParticipant(meeting_id=meeting.id, name=name, email=email)
                db.add(mp)
                saved_attendees.append({"name": name, "email": email})
        db.commit()
        
        return {
            "status": "ok",
            "meet_url": meet_url,
            "meeting_id": meeting.id,
            "attendees": saved_attendees,
            "start_time": start_time,
            "bot_invited": bot_invited,
            "bot_email": BOT_EMAIL
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Error fetching from calendar: {str(e)}"}
