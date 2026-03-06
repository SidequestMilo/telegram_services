from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional

from .models import (
    UserListResponse, UserProfile, MatchListResponse, MatchAnalyticsResponse,
    ConnectionListResponse, UserPreferencesResponse, FeedbackResponse,
    ActivityLogResponse, PlatformAnalyticsResponse, UserSegmentationResponse,
    SystemHealthResponse
)
from .auth import verify_admin
from .service import AdminService

router = APIRouter(
    prefix="/api",
    tags=["admin"],
    dependencies=[Depends(verify_admin)]
)

def get_admin_service() -> AdminService:
    from app.main import database, session_manager, settings
    db_client = database.db if hasattr(database, "db") else None
    
    redis_client = None
    if hasattr(session_manager, "redis"):
        redis_client = session_manager.redis
    elif hasattr(session_manager, "_redis"):
        redis_client = session_manager._redis

    return AdminService(
        db=db_client, 
        redis_client=redis_client, 
        tg_bot_token=settings.TELEGRAM_BOT_TOKEN
    )

@router.get("/users", response_model=UserListResponse)
async def get_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_type: Optional[str] = None,
    location: Optional[str] = None,
    search: Optional[str] = None,
    service: AdminService = Depends(get_admin_service)
):
    return await service.get_users(page, limit, user_type, location, search)

@router.get("/users/{telegram_id}", response_model=UserProfile)
async def get_single_user(
    telegram_id: str,
    service: AdminService = Depends(get_admin_service)
):
    user = await service.get_user_by_id(telegram_id)
    if not user:
         raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/matches", response_model=MatchListResponse)
async def get_all_matches(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    date_range: Optional[str] = None,
    service: AdminService = Depends(get_admin_service)
):
    return await service.get_matches(page, limit, status, date_range)

@router.get("/matches/analytics", response_model=MatchAnalyticsResponse)
async def match_analytics(service: AdminService = Depends(get_admin_service)):
    return await service.get_match_analytics()

@router.get("/connections", response_model=ConnectionListResponse)
async def get_connections(service: AdminService = Depends(get_admin_service)):
    return await service.get_connections()

@router.get("/preferences/{telegram_id}", response_model=UserPreferencesResponse)
async def get_user_preferences(telegram_id: str, service: AdminService = Depends(get_admin_service)):
    return await service.get_user_preferences(telegram_id)

@router.get("/feedback", response_model=FeedbackResponse)
async def get_feedback(service: AdminService = Depends(get_admin_service)):
    return await service.get_feedback()

@router.get("/activity", response_model=ActivityLogResponse)
async def get_activity(
    user: Optional[str] = None,
    command: Optional[str] = None,
    date_range: Optional[str] = None,
    service: AdminService = Depends(get_admin_service)
):
    return await service.get_activity_logs(user, command, date_range)

@router.get("/analytics", response_model=PlatformAnalyticsResponse)
async def platform_analytics(service: AdminService = Depends(get_admin_service)):
    return await service.get_platform_analytics()

@router.get("/users/segments", response_model=UserSegmentationResponse)
async def user_segmentation(service: AdminService = Depends(get_admin_service)):
    return await service.get_user_segments()

@router.get("/system-health", response_model=SystemHealthResponse)
async def system_health(service: AdminService = Depends(get_admin_service)):
    return await service.get_system_health()
