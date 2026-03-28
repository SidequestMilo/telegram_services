
import asyncio
import logging
from datetime import datetime
from .database import Database
from .config import Settings

logger = logging.getLogger(__name__)

async def re_engage_inactive_users(db: Database, settings: Settings, send_message_func):
    """
    Cron job task to re-engage users who haven't been active for 36 hours.
    """
    logger.info("Starting re-engagement cron job...")
    try:
        # User specified 36 hours
        hours = getattr(settings, "RE_ENGAGE_HOURS", 36)
        inactive_users = await db.get_inactive_users(hours)
        
        logger.info(f"Found {len(inactive_users)} inactive users to re-engage.")
        
        for user in inactive_users:
            telegram_user_id = user["telegram_user_id"]
            name = user.get("profile", {}).get("name", "there")
            
            message = {
                "chat_id": telegram_user_id,
                "text": f"Hey {name}! 👋 It's been a while. Ready to find some more matches today? 🚀\n\nType /connect to see who's new!",
                "parse_mode": "Markdown"
            }
            
            # Send the message
            success = await send_message_func(message, "cron-re-engage")
            
            if success:
                logger.info(f"Successfully re-engaged user {telegram_user_id}")
                # Update last_active so we don't spam them every cron run
                await db.update_last_active(telegram_user_id)
            else:
                logger.warning(f"Failed to re-engage user {telegram_user_id}")
                
    except Exception as e:
        logger.error(f"Error in re-engagement cron job: {e}")

async def start_cron_scheduler(db: Database, settings: Settings, send_message_func):
    """
    Run the cron scheduler every hour.
    """
    while True:
        await re_engage_inactive_users(db, settings, send_message_func)
        # Sleep for 1 hour before checking again
        await asyncio.sleep(3600)
