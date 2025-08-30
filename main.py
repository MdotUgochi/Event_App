from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
import cloudinary
import cloudinary.uploader
from datetime import datetime
import os
from dotenv import load_dotenv

from database import get_db, engine, Settings
from models import Base, Event, RSVP
from schemas import EventCreate, EventResponse, RSVPCreate, RSVPResponse

# Load environment variables
load_dotenv()


Base.metadata.create_all(bind=engine)


app = FastAPI(title="Event_App API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Cloudinary
cloudinary.config(
    cloud_name=Settings.CLOUDINARY_CLOUD_NAME,
    api_key=Settings.CLOUDINARY_API_KEY,
    api_secret=Settings.CLOUDINARY_API_SECRET
)

@app.get("/")
def read_root():
    return {"message": "Event Platform API", "version": "1.0.0"}


@app.post("/events/", response_model=EventResponse)
async def create_event(
    title: str = Form(...),
    description: str = Form(...),
    date: str = Form(...),  # YYYY-MM-DD HH:MM
    location: str = Form(...),
    flyer: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Create a new event with optional flyer upload."""
    
    
    try:
        event_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Use YYYY-MM-DD HH:MM"
        )
    
    
    flyer_url = None
    if flyer and flyer.filename:
        try:
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                flyer.file,
                folder="event-flyers",
                resource_type="image"
            )
            flyer_url = result["secure_url"]
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to upload flyer: {str(e)}"
            )
    
    # Create event in database
    db_event = Event(
        title=title,
        description=description,
        date=event_date,
        location=location,
        flyer_url=flyer_url
    )
    
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    return db_event

@app.get("/events/", response_model=List[EventResponse])
def get_events(db: Session = Depends(get_db)):
    """Get all events with RSVP counts."""
    events = db.query(Event).order_by(Event.date.desc()).all()
    return events

@app.get("/events/{event_id}", response_model=EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get specific event by ID."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


# RSVP ENDPOINTS

@app.post("/events/{event_id}/rsvp", response_model=RSVPResponse)
def create_rsvp(
    event_id: int,
    name: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """RSVP to an event."""
    
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if user already RSVPed (prevent duplicates)
    existing_rsvp = db.query(RSVP).filter(
        RSVP.event_id == event_id,
        RSVP.email == email
    ).first()
    
    if existing_rsvp:
        raise HTTPException(
            status_code=400, 
            detail="You have already RSVPed to this event"
        )
        
 # Create RSVP
    db_rsvp = RSVP(
        event_id=event_id,
        name=name,
        email=email
    )
    
    db.add(db_rsvp)
    db.commit()
    db.refresh(db_rsvp)
    
    return db_rsvp

@app.get("/events/{event_id}/rsvps", response_model=List[RSVPResponse])
def get_event_rsvps(event_id: int, db: Session = Depends(get_db)):
    """Get all RSVPs for a specific event."""
    
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    rsvps = db.query(RSVP).filter(RSVP.event_id == event_id).all()
    return rsvps


# RSVP Deadline
@app.post("/events/{event_id}/rsvp/deadline", response_model=RSVPResponse)
def set_rsvp_deadline(
    event_id: int,
    deadline: datetime = Body(...),
    db: Session = Depends(get_db)
):
    """Set RSVP deadline for an event."""
    
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.rsvp_deadline = deadline
    db.commit()
    db.refresh(event)
    
    return event

#RSVP Status
@app.get("/events/{event_id}/rsvp/status", response_model=RSVPResponse)
def get_rsvp_status(
    event_id: int,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """Get RSVP status for an event."""
    
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if RSVP exists
    rsvp = db.query(RSVP).filter(
        RSVP.event_id == event_id,
        RSVP.email == email
    ).first()
    
    if not rsvp:
        raise HTTPException(
            status_code=404,
            detail="RSVP not found"
        )
    
    return rsvp

# Cancel RSVP
@app.delete("/events/{event_id}/rsvp", response_model=RSVPResponse)
def cancel_rsvp(
    event_id: int,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """Cancel RSVP for an event."""
    
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if RSVP exists
    rsvp = db.query(RSVP).filter(
        RSVP.event_id == event_id,
        RSVP.email == email
    ).first()
    
    if not rsvp:
        raise HTTPException(
            status_code=404,
            detail="RSVP not found"
        )
    
    db.delete(rsvp)
    db.commit()
    
    return rsvp
