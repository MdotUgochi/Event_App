from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
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

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(title="Event_App API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Cloudinary
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
    date: str = Form(...),  # Expected format: YYYY-MM-DD HH:MM
    location: str = Form(...),
    flyer: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Create a new event with optional flyer upload."""
    
    # Parse date string
    try:
        event_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Use YYYY-MM-DD HH:MM"
        )
    
    # flyer upload
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

