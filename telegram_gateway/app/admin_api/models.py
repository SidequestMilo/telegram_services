from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
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

class FeedbackAnalyticsResponse(BaseModel):
    average_rating: float
    total_reviews: int
    sentiment_trends: Dict[str, int]
    rating_distribution: Dict[int, int]

class ActivityLogResponse(BaseModel):
    logs: List[dict]

class PlatformAnalyticsResponse(BaseModel):
    total_users: int
    active_users_24h: int
    new_users_today: int
    total_matches: int
    connections: int
    feedback_count: int
    growth: List[dict] = []
    activity: List[dict] = []

class UserSegmentItem(BaseModel):
    name: str
    value: int

class UserSegmentationResponse(BaseModel):
    segments: List[UserSegmentItem]

class SystemHealthResponse(BaseModel):
    mongodb: str
    redis: str
    telegram_api: str

class SystemResourcesResponse(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    uptime: float

class BroadcastHistoryItem(BaseModel):
    id: str
    message: str
    audience: str
    status: str
    sent_at: datetime
    success_rate: float

class BroadcastHistoryResponse(BaseModel):
    history: List[BroadcastHistoryItem]

class MatchTrendItem(BaseModel):
    date: str
    generated: int
    success: int
    skipped: int
    score: float

class MatchTrendsResponse(BaseModel):
    trends: List[MatchTrendItem]

class StatusUpdateResponse(BaseModel):
    status: str
    message: str
