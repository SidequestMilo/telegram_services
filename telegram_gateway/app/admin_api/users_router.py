from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional

from .models import (
    UserListResponse, UserProfile, UserSegmentationResponse, StatusUpdateResponse, ConversationResponse
)
from .service import AdminService

router = APIRouter(
    prefix="/users",
    tags=["Users"]
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

@router.get("", response_model=UserListResponse)
async def get_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_type: Optional[str] = None,
    location: Optional[str] = None,
    search: Optional[str] = None,
    service: AdminService = Depends(get_admin_service)
):
    return await service.get_users(page, limit, user_type, location, search)

@router.get("/segments", response_model=UserSegmentationResponse)
async def user_segmentation(service: AdminService = Depends(get_admin_service)):
    return await service.get_user_segments()

@router.patch("/{telegram_id}/status", response_model=StatusUpdateResponse)
async def update_user_status(
    telegram_id: str,
    status: str = Query(..., regex="^(Active|Suspended|Inactive)$"),
    service: AdminService = Depends(get_admin_service)
):
    return await service.update_user_status(telegram_id, status)

@router.get("/{telegram_id}", response_model=UserProfile)
async def get_single_user(
    telegram_id: str,
    service: AdminService = Depends(get_admin_service)
):
    user = await service.get_user_by_id(telegram_id)
    if not user:
         raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/{telegram_id}/conversations", response_model=ConversationResponse)
async def get_user_conversations(
    telegram_id: str,
    limit: int = 100,
    service: AdminService = Depends(get_admin_service)
):
    return await service.get_user_conversations(telegram_id, limit)
