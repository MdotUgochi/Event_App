from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

class RSVPBase(BaseModel):
    name: str
    email: str

class RSVPCreate(RSVPBase):
    pass

class RSVPResponse(RSVPBase):
    id: int
    event_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class EventBase(BaseModel):
    title: str
    description: str
    date: datetime
    location: str
    flyer_url: Optional[str] = None

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    id: int
    created_at: datetime
    rsvps: List[RSVPResponse] = []
    
    class Config:
        from_attributes = True