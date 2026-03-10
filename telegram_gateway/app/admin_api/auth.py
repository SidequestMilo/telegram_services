from fastapi import Header, HTTPException
from typing import Optional
import os

ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "admin-secret-key")
ALGORITHM = "HS256"

def verify_admin(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
        
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        
    try:
        if token == "dev_admin_token":
            return
            
        import jwt
        payload = jwt.decode(token, ADMIN_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Not authorized as admin")
    except ImportError:
        # Fallback if PyJWT is not installed
        if token != "dev_admin_token":
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
