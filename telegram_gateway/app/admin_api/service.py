from typing import Dict, Any, List
from datetime import datetime, timedelta
import httpx

class AdminService:
    def __init__(self, db, redis_client=None, tg_bot_token: str = ""):
        self.db = db
        self.redis = redis_client
        self.tg_bot_token = tg_bot_token

    async def get_users(self, page: int, limit: int, user_type: str = None, location: str = None, search: str = None) -> Dict[str, Any]:
        if self.db is None: return {"users": [], "total": 0}
        
        skip = (page - 1) * limit
        filter_query = {}
        if search:
            filter_query["$or"] = [
                {"profile.name": {"$regex": search, "$options": "i"}},
                {"profile.username": {"$regex": search, "$options": "i"}}
            ]
        if location:
            filter_query["profile.location"] = {"$regex": location, "$options": "i"}
        if user_type:
             filter_query["profile.occupation"] = {"$regex": user_type, "$options": "i"}

        cursor = self.db.users.find(filter_query).skip(skip).limit(limit)
        users = []
        async for doc in cursor:
            profile = doc.get("profile", {})
            users.append({
                "telegram_id": str(doc.get("telegram_user_id")),
                "username": profile.get("username", doc.get("username")),
                "name": profile.get("name"),
                "occupation": profile.get("occupation"),
                "location": profile.get("location"),
                "interests": profile.get("interests", []),
                "goals": profile.get("goals", []),
                "matches": doc.get("matches_count", 0),
                "connections": doc.get("connections_count", 0)
            })
            
        total = await self.db.users.count_documents(filter_query)
        return {"users": users, "total": total}

    async def get_user_by_id(self, telegram_id: str) -> Dict[str, Any]:
        if self.db is None: return None
        try:
             tel_id = int(telegram_id)
        except ValueError:
             tel_id = telegram_id
             
        doc = await self.db.users.find_one({"telegram_user_id": tel_id})
        if not doc: return None
            
        profile = doc.get("profile", {})
        return {
            "telegram_id": str(doc.get("telegram_user_id")),
            "username": profile.get("username", doc.get("username")),
            "name": profile.get("name"),
            "occupation": profile.get("occupation"),
            "location": profile.get("location"),
            "interests": profile.get("interests", []),
            "goals": profile.get("goals", []),
            "matches": doc.get("matches_count", 0), 
            "connections": doc.get("connections_count", 0)
        }

    async def get_matches(self, page: int, limit: int, status: str = None, date_range: str = None) -> Dict[str, Any]:
        if self.db is None: return {"matches": [], "total": 0}
        
        skip = (page - 1) * limit
        filter_query = {}
        if status:
            filter_query["status"] = status
            
        if date_range == "last_7_days":
             filter_query["timestamp"] = {"$gte": datetime.utcnow() - timedelta(days=7)}
        elif date_range == "last_30_days":
             filter_query["timestamp"] = {"$gte": datetime.utcnow() - timedelta(days=30)}
        
        cursor = self.db.matches.find(filter_query).skip(skip).limit(limit).sort("timestamp", -1)
        matches = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            matches.append(doc)
            
        total = await self.db.matches.count_documents(filter_query)
        return {"matches": matches, "total": total}

    async def get_match_analytics(self) -> Dict[str, Any]:
        if self.db is None:
            return {"total_matches": 0, "accepted": 0, "skipped": 0, "success_rate": 0.0}
            
        total_matches = await self.db.matches.count_documents({})
        accepted = await self.db.matches.count_documents({"status": "accepted"})
        skipped = await self.db.matches.count_documents({"status": "skipped"})
        
        success_rate = 0.0
        total_resolved = accepted + skipped
        if total_resolved > 0:
            success_rate = (accepted / total_resolved) * 100
            
        return {
            "total_matches": total_matches,
            "accepted": accepted,
            "skipped": skipped,
            "success_rate": round(success_rate, 2)
        }

    async def get_connections(self) -> Dict[str, Any]:
        if self.db is None: return {"connections": []}
        cursor = self.db.connections.find().sort("created_at", -1)
        connections = []
        async for doc in cursor:
             doc["_id"] = str(doc["_id"])
             connections.append(doc)
        return {"connections": connections}

    async def get_user_preferences(self, telegram_id: str) -> Dict[str, Any]:
        try:
             tel_id = int(telegram_id)
        except ValueError:
             tel_id = telegram_id
             
        if self.db is None: return {"skills": [], "goals": [], "interests": []}
        
        doc = await self.db.user_preferences.find_one({"telegram_user_id": tel_id})
        if not doc:
             user_doc = await self.db.users.find_one({"telegram_user_id": tel_id})
             if user_doc:
                 doc = user_doc.get("preferences")
                 
        if not doc:
             return {"skills": [], "goals": [], "interests": []}
             
        return {
             "skills": doc.get("skills", []),
             "goals": doc.get("goals", []),
             "interests": doc.get("interests", [])
        }

    async def get_feedback(self) -> Dict[str, Any]:
        if self.db is None: return {"feedback": []}
        cursor = self.db.feedback.find().sort("created_at", -1)
        feedback = []
        async for doc in cursor:
            feedback.append({
                "user": doc.get("username", str(doc.get("telegram_user_id", "Unknown"))),
                "rating": doc.get("rating", 0),
                "message": doc.get("message", ""),
                "created_at": doc.get("created_at", datetime.utcnow()).isoformat()
            })
        return {"feedback": feedback}

    async def get_activity_logs(self, user: str = None, command: str = None, date_range: str = None) -> Dict[str, Any]:
        if self.db is None: return {"logs": []}
        
        filter_query = {}
        if user:
             filter_query["user"] = user
        if command:
             # Match either command or raw message starting with command
             filter_query["command"] = {"$regex": command, "$options": "i"}
             
        if date_range == "today":
            filter_query["timestamp"] = {"$gte": datetime.utcnow() - timedelta(days=1)}
             
        cursor = self.db.activity_logs.find(filter_query).sort("timestamp", -1).limit(100)
        logs = []
        async for doc in cursor:
             logs.append({
                 "user": doc.get("user", "Unknown"),
                 "command": doc.get("command", ""),
                 "timestamp": doc.get("timestamp", datetime.utcnow()).isoformat(),
                 "status": doc.get("status", "success")
             })
             
        # Fallback to general API requests or messages if activity_logs is empty
        if not logs:
            msg_cursor = self.db.messages.find().limit(50)
            async for doc in msg_cursor:
                 logs.append({
                     "user": str(doc.get("telegram_user_id", "Unknown")),
                     "command": "message_action",
                     "timestamp": datetime.utcnow().isoformat(),
                     "status": "success"
                 })
                 
        return {"logs": logs}

    async def get_platform_analytics(self) -> Dict[str, Any]:
        if self.db is None:
            return {"total_users": 0, "active_users_24h": 0, "new_users_today": 0, "total_matches": 0, "connections": 0, "feedback_count": 0}
            
        total_users = await self.db.users.count_documents({})
        total_matches = await self.db.matches.count_documents({})
        connections = await self.db.connections.count_documents({})
        feedback_count = await self.db.feedback.count_documents({})
        
        # Estimate active users in 24h via messages table
        try:
            active_users_pipeline = [
               {"$match": {"timestamp": {"$gte": datetime.utcnow() - timedelta(days=1)}}},
               {"$group": {"_id": "$telegram_user_id"}}
            ]
            # Since message.timestamp might not be present, this might fail or return 0, fallback to general messages count
            active_users_cursor = self.db.messages.aggregate(active_users_pipeline)
            active_users_24h = len(await active_users_cursor.to_list(length=None))
        except:
            active_users_24h = len(await self.db.messages.distinct("telegram_user_id"))
            
        return {
            "total_users": total_users,
            "active_users_24h": active_users_24h,
            "new_users_today": 0, # Depending on users.created_at
            "total_matches": total_matches,
            "connections": connections,
            "feedback_count": feedback_count
        }

    async def get_user_segments(self) -> Dict[str, Any]:
        if self.db is None: return {"students": 0, "startup_founders": 0, "developers": 0, "investors": 0}
        
        cursor = self.db.users.aggregate([
            {
               "$group": {
                  "_id": "$profile.occupation",
                  "count": {"$sum": 1}
               }
            }
        ])
        
        segments = {
            "students": 0,
            "startup_founders": 0,
            "developers": 0,
            "investors": 0,
        }
        
        async for doc in cursor:
            occ = (doc.get("_id") or "").lower()
            count = doc.get("count", 0)
            if "student" in occ:
                segments["students"] += count
            elif "founder" in occ or "startup" in occ or "entrepreneur" in occ:
                segments["startup_founders"] += count
            elif "dev" in occ or "engineer" in occ or "programmer" in occ:
                segments["developers"] += count
            elif "investor" in occ or "vc" in occ or "capital" in occ:
                segments["investors"] += count
                
        return segments

    async def get_system_health(self) -> Dict[str, Any]:
        mongo_status = "disconnected"
        if self.db is not None:
             try:
                 await self.db.command('ping')
                 mongo_status = "connected"
             except:
                 pass
                 
        redis_status = "disconnected"
        if self.redis is not None:
             try:
                 await self.redis.ping()
                 redis_status = "connected"
             except:
                 pass
                 
        tg_status = "unreachable"
        if self.tg_bot_token:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"https://api.telegram.org/bot{self.tg_bot_token}/getMe", timeout=3.0)
                    if resp.status_code == 200:
                         tg_status = "reachable"
            except:
                pass
                
        return {
            "mongodb": mongo_status,
            "redis": redis_status,
            "telegram_api": tg_status
        }
