from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class UserProfile(BaseModel):
    telegram_id: str
    username: Optional[str] = None
    name: Optional[str] = None
    occupation: Optional[str] = None
    location: Optional[str] = None
    interests: List[str] = []
    goals: List[str] = []
    matches: int = 0
    connections: int = 0

class UserListResponse(BaseModel):
    users: List[dict]
    total: int

class MatchListResponse(BaseModel):
    matches: List[dict]
    total: int

class MatchAnalyticsResponse(BaseModel):
    total_matches: int
    accepted: int
    skipped: int
    success_rate: float

class ConnectionListResponse(BaseModel):
    connections: List[dict]

class UserPreferencesResponse(BaseModel):
    skills: List[str] = []
    goals: List[str] = []
    interests: List[str] = []

class FeedbackResponse(BaseModel):
    feedback: List[dict]

class ActivityLogResponse(BaseModel):
    logs: List[dict]

class PlatformAnalyticsResponse(BaseModel):
    total_users: int
    active_users_24h: int
    new_users_today: int
    total_matches: int
    connections: int
    feedback_count: int

class UserSegmentationResponse(BaseModel):
    students: int = 0
    startup_founders: int = 0
    developers: int = 0
    investors: int = 0

class SystemHealthResponse(BaseModel):
    mongodb: str
    redis: str
    telegram_api: str
