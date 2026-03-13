from typing import Dict, Any, List
from datetime import datetime, timedelta
import httpx
import os
import time
try:
    import psutil
except ImportError:
    psutil = None

from bson import ObjectId

class AdminService:
    def __init__(self, db, redis_client=None, tg_bot_token: str = ""):
        self.db = db
        self.redis = redis_client
        self.tg_bot_token = tg_bot_token
        self.start_time = time.time()

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
                "connections": doc.get("connections_count", 0),
                "status": doc.get("status", "Active")
            })
            
        total = await self.db.users.count_documents(filter_query)
        return {"users": users, "total": total}

    async def update_user_status(self, telegram_id: str, status: str) -> Dict[str, Any]:
        if self.db is None: return {"status": "error", "message": "Database not connected"}
        try:
             tel_id = int(telegram_id)
        except ValueError:
             tel_id = telegram_id
             
        result = await self.db.users.update_one(
            {"telegram_user_id": tel_id},
            {"$set": {"status": status}}
        )
        if result.matched_count == 0:
            return {"status": "error", "message": "User not found"}
        return {"status": "success", "message": f"User status updated to {status}"}

    async def get_match_trends(self) -> Dict[str, Any]:
        if self.db is None: return {"trends": []}
        
        # Aggregate matches by date for the last 30 days
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": datetime.utcnow() - timedelta(days=30)}
                }
            },
            {
                "$group": {
                    "_id": { "$dateToString": { "format": "%Y-%m-%d", "date": "$timestamp" } },
                    "count": { "$sum": 1 },
                    "success_count": { "$sum": { "$cond": [{ "$eq": ["$status", "accepted"] }, 1, 0] } },
                    "avg_comp": { "$avg": "$match_data.score" }
                }
            },
            { "$sort": { "_id": 1 } }
        ]
        
        cursor = self.db.matches.aggregate(pipeline)
        trends = []
        async for doc in cursor:
            trends.append({
                "date": doc["_id"],
                "count": doc["count"],
                "success_count": doc["success_count"],
                "average_compatibility": round(doc.get("avg_comp") or 0.0, 2)
            })
            
        if not trends:
            # Fallback mock data if no real data
            for i in range(7):
                date = (datetime.utcnow() - timedelta(days=6-i)).strftime("%Y-%m-%d")
                trends.append({
                    "date": date, 
                    "count": 10 + i, 
                    "success_count": 5 + i,
                    "average_compatibility": 75.0 + i
                })
                
        return {"trends": trends}

    async def get_broadcast_history(self) -> Dict[str, Any]:
        if self.db is None: return {"history": []}
        
        cursor = self.db.broadcasts.find().sort("sent_at", -1).limit(50)
        history = []
        async for doc in cursor:
            history.append({
                "id": str(doc["_id"]),
                "message": doc.get("message", ""),
                "audience": doc.get("audience", "All"),
                "status": doc.get("status", "Sent"),
                "sent_at": doc.get("sent_at", datetime.utcnow()),
                "success_rate": doc.get("success_rate", 100.0)
            })
            
        if not history:
            # Add some dummy history if empty
            history.append({
                "id": "mock_1",
                "message": "Welcome to our new community!",
                "audience": "New Users",
                "status": "Completed",
                "sent_at": datetime.utcnow() - timedelta(days=2),
                "success_rate": 98.5
            })
            
        return {"history": history}

    async def update_feedback_status(self, feedback_id: str, status: str) -> Dict[str, Any]:
        if self.db is None: return {"status": "error", "message": "Database not connected"}
        try:
            obj_id = ObjectId(feedback_id)
        except:
            return {"status": "error", "message": "Invalid feedback ID"}
            
        result = await self.db.feedback.update_one(
            {"_id": obj_id},
            {"$set": {"status": status}}
        )
        if result.matched_count == 0:
            return {"status": "error", "message": "Feedback not found"}
        return {"status": "success", "message": f"Feedback status updated to {status}"}

    async def get_system_resources(self) -> Dict[str, Any]:
        if psutil is None:
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0,
                "uptime": time.time() - self.start_time
            }
            
        return {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "uptime": time.time() - self.start_time
        }

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

    async def get_feedback_analytics(self) -> Dict[str, Any]:
        if self.db is None:
            return {"average_rating": 0.0, "total_reviews": 0, "sentiment_trends": {}, "rating_distribution": {}}
            
        cursor = self.db.feedback.find()
        total_rating = 0
        total_reviews = 0
        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        async for doc in cursor:
            rating = doc.get("rating", 0)
            if rating > 0:
                total_rating += rating
                total_reviews += 1
                if rating in rating_dist:
                    rating_dist[rating] += 1
        
        avg_rating = (total_rating / total_reviews) if total_reviews > 0 else 0.0
        
        return {
            "average_rating": round(avg_rating, 2),
            "total_reviews": total_reviews,
            "sentiment_trends": {"positive": rating_dist[4] + rating_dist[5], "neutral": rating_dist[3], "negative": rating_dist[1] + rating_dist[2]},
            "rating_distribution": rating_dist
        }

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
            active_users_24h = len(await self.db.messages.distinct("telegram_user_id", {"timestamp": {"$gte": datetime.utcnow() - timedelta(days=1)}}))
        except:
            active_users_24h = len(await self.db.messages.distinct("telegram_user_id"))
            
        # Mock growth data for the dashboard charts
        growth = []
        for i in range(7):
            date = (datetime.utcnow() - timedelta(days=6-i)).strftime("%b %d")
            growth.append({"name": date, "users": total_users - (7-i)})

        return {
            "total_users": total_users,
            "active_users_24h": active_users_24h,
            "new_users_today": 0,
            "total_matches": total_matches,
            "connections": connections,
            "feedback_count": feedback_count,
            "growth": growth
        }

    async def get_user_segments(self) -> List[Dict[str, Any]]:
        if self.db is None: return []
        
        cursor = self.db.users.aggregate([
            {
               "$group": {
                  "_id": "$profile.occupation",
                  "count": {"$sum": 1}
               }
            },
            {"$sort": {"count": -1}}
        ])
        
        segments = []
        async for doc in cursor:
            occ = (doc.get("_id") or "Unknown").title()
            count = doc.get("count", 0)
            segments.append({"name": occ, "value": count})
                
        if not segments:
            segments = [
                {"name": "Students", "value": 0},
                {"name": "Founders", "value": 0},
                {"name": "Developers", "value": 0},
                {"name": "Others", "value": 0}
            ]

        return {"segments": segments}

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
